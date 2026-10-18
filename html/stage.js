/* PRTS 工作区渲染引擎。
 *
 * 单一数据流：Qt 持有文档模型，任何编辑 → stageApi.loadProject(json)
 * 全量同步；JS 只报交互事件（window.bridge：stageReady/log/clipSelected/
 * clipMoved/timeUpdate/exportFrame）。
 *
 * 渲染：#gl WebGL 画布（spine 多骨架，y 向上世界 → 相机 position=(w/2,h/2)
 * 映射为舞台像素 y 向下）；#overlay DOM 层（PNG <img> / SVG 内联，SMIL/CSS
 * 动画因此可动）。z 序：layer 行号小的在上；spine 组整体在覆盖层之下，
 * 组内按 layer 排序绘制。
 *
 * 时钟：setTime(t) 全确定性（拖播放头逐帧重渲染，spine 直接写 trackTime）；
 * play() 走 rAF 真实时钟，导出模式逐帧 captureFrame()。
 */
(function () {
'use strict';

// ---------------- 桥 ----------------
function bcall(name, a, b) {
  var br = window.bridge;
  if (br) { try { br[name](a, b); } catch (e) { console.warn('[stage] bridge.' + name, e); } }
}
function log(m) { console.log('[stage]', m); bcall('log', String(m)); }

// ---------------- 工具 ----------------
function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
function lerp(a, b, k) { return a + (b - a) * k; }
function pickEntry(list, t) {
  for (var i = 0; i < list.length; i++) {
    var e = list[i];
    if (t >= e.start && t < e.end) return e;
  }
  return null;
}

// ---------------- DOM ----------------
var stageBox = document.getElementById('stage');
var glCanvas = document.getElementById('gl');
var overlay = document.getElementById('overlay');

// ---------------- GL ----------------
var context = null, sceneRenderer = null, assetManager = null;
function initGL() {
  if (context) return true;
  try {
    context = new spine.webgl.ManagedWebGLRenderingContext(glCanvas, {
      alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true,
    });
    sceneRenderer = new spine.webgl.SceneRenderer(glCanvas, context, true);
    assetManager = new spine.webgl.AssetManager(context);
    return true;
  } catch (e) { log('WebGL 初始化失败: ' + e); return false; }
}

// ---------------- 模型状态 ----------------
var model = null;              // {canvas:{w,h,bg}, duration, layers, clips, spine:{模型:{skel,atlas}}, assets}
var actors = {};               // clipId -> actor
var duration = 5;
var glState = { w: 1280, h: 720, bg: '#ffffff' };

// 骨架数据缓存：asset -> {status:'loading'|'ok'|'err', data, anchor, boundsW, boundsH}
var skelLib = {};

// ---------------- 骨架数据加载 ----------------
function ensureSkeletonData(asset, info) {
  var e = skelLib[asset];
  if (e) return e;
  e = { status: 'loading', data: null, anchor: null, boundsW: 100, boundsH: 100 };
  skelLib[asset] = e;
  try {
    assetManager.loadBinary(info.skel);
    assetManager.loadTextureAtlas(info.atlas);
  } catch (err) { e.status = 'err'; log('骨架加载发起失败 ' + asset + ': ' + err); }
  return e;
}

function finalizeSkeletonData(asset, e) {
  try {
    var atlas = assetManager.get(model.spine[asset].atlas);
    var binary = assetManager.get(model.spine[asset].skel);
    var data = new spine.SkeletonBinary(new spine.AtlasAttachmentLoader(atlas))
      .readSkeletonData(binary);
    // 锚定：setup pose 包围盒 → 脚底中心（skeleton 局部坐标）
    var tmp = new spine.Skeleton(data);
    if (data.skins.length) { tmp.setSkinByName(data.skins[0].name); tmp.setSlotsToSetupPose(); }
    tmp.setToSetupPose();
    tmp.updateWorldTransform();
    var off = new spine.Vector2(), size = new spine.Vector2();
    tmp.getBounds(off, size, []);
    e.anchor = { x: off.x + size.x / 2, y: off.y };
    e.boundsW = Math.max(1, size.x);
    e.boundsH = Math.max(1, size.y);
    e.data = data;
    e.status = 'ok';
  } catch (err) {
    e.status = 'err';
    log('骨架解析失败 ' + asset + ': ' + err);
  }
}

// 150ms 轮询：加载完成的骨架数据落地 → 实例化等待中的 actor
var readySent = false;
setInterval(function () {
  if (!assetManager || !model) return;
  var loading = false;
  for (var asset in skelLib) {
    var e = skelLib[asset];
    if (e.status === 'loading') {
      loading = true;
      if (assetManager.hasErrors()) {
        e.status = 'err';
        log('骨架资源加载出错 ' + asset + ': ' +
            JSON.stringify(assetManager.getErrors()));
      }
    }
  }
  if (assetManager.isLoadingComplete()) {
    for (asset in skelLib) {
      if (skelLib[asset].status === 'loading') finalizeSkeletonData(asset, skelLib[asset]);
    }
    instantiatePending();
  }
  if (!readySent && !loading) { readySent = true; bcall('stageReady'); }
}, 150);

// ---------------- Actor ----------------
function SpineActor(clip) {
  this.kind = 'spine';
  this.clip = clip;
  this.ready = false;
  this.skeleton = null;
  this.state = null;
  this.curAnim = null;
  this.setupDone = false;
  this.anchor = { x: 0, y: 0 };
  this.boundsW = 100; this.boundsH = 100;
  this.pending = true;
}
SpineActor.prototype.instantiate = function (e) {
  this.skeleton = new spine.Skeleton(e.data);
  if (e.data.skins.length) {
    this.skeleton.setSkinByName(e.data.skins[0].name);
    this.skeleton.setSlotsToSetupPose();
  }
  this.skeleton.setToSetupPose();
  var sd = new spine.AnimationStateData(e.data);
  sd.defaultMix = 0;   // 确定性 seek：条目切换硬切（交叉淡化依赖 update 推进）
  this.state = new spine.AnimationState(sd);
  this.anchor = e.anchor;
  this.boundsW = e.boundsW;
  this.boundsH = e.boundsH;
  this.ready = true;
  this.pending = false;
};

function OvActor(clip, assetsBase) {
  this.kind = 'ov';
  this.clip = clip;
  this.img = null;
  var el = document.createElement('div');
  el.className = 'ov';
  el.dataset.clipId = clip.id;
  this.el = el;
  if (clip.type === 'png') {
    var img = document.createElement('img');
    img.src = assetsBase + encodeURIComponent(clip.asset);
    img.draggable = false;
    el.appendChild(img);
    this.img = img;
  } else { // svg：内联渲染，SMIL/CSS 动画才会动
    var wrap = document.createElement('div');
    el.appendChild(wrap);
    fetch(assetsBase + encodeURIComponent(clip.asset))
      .then(function (r) { return r.text(); })
      .then(function (txt) { wrap.innerHTML = txt; })
      .catch(function (e) { log('SVG 加载失败 ' + clip.asset + ': ' + e); });
  }
  overlay.appendChild(el);
}

function createActor(clip) {
  if (clip.type === 'spine') return new SpineActor(clip);
  return new OvActor(clip, model.assets);
}

function instantiatePending() {
  var changed = false;
  for (var id in actors) {
    var a = actors[id];
    if (a.kind === 'spine' && a.pending) {
      var e = skelLib[a.clip.asset];
      if (e && e.status === 'ok') { a.instantiate(e); changed = true; }
      else if (e && e.status === 'err') { a.pending = false; }
    }
  }
  if (changed) renderNow();
}

// ---------------- 求值 ----------------
// spine 片段在 t 时刻：move 条目插值 / 夹取，anim 条目 trackTime 直写
function evalSpineActor(a, t, H) {
  var c = a.clip;
  var ms = c.moves || [];
  var px = c.x, py = c.y, rot = c.rotation || 0;
  if (ms.length) {
    var m = pickEntry(ms, t);
    if (m) {
      var k = clamp01((t - m.start) / Math.max(1e-6, m.end - m.start));
      px = lerp(m.x0, m.x1, k); py = lerp(m.y0, m.y1, k);
      rot = lerp(m.rot0 || 0, m.rot1 || 0, k);
    } else if (t < ms[0].start) {
      px = ms[0].x0; py = ms[0].y0; rot = ms[0].rot0 || 0;
    } else {
      var last = ms[ms.length - 1];
      px = last.x1; py = last.y1; rot = last.rot1 || 0;
    }
  }
  // clip.scale 为倍率：1.0 = 角色高 画布半高（按骨架包围盒归一）
  var s = (0.5 * H / a.boundsH) * (c.scale || 1);
  var th = -rot * Math.PI / 180;          // 舞台顺时针 → spine 逆时针
  var ax = a.anchor.x * s, ay = a.anchor.y * s;
  var cos = Math.cos(th), sin = Math.sin(th);
  var sk = a.skeleton;
  // 绕脚底中心旋转：把锚点旋回原点再平移
  sk.x = px - (ax * cos - ay * sin);
  sk.y = (H - py) - (ax * sin + ay * cos);
  sk.rotation = -rot;
  sk.scaleX = s; sk.scaleY = s;
  if (!sk.color) sk.color = new spine.Color(1, 1, 1, 1);
  sk.color.a = clamp01(c.opacity == null ? 1 : c.opacity);

  var ae = pickEntry(c.anims || [], t);
  if (ae && ae.anim) {
    if (a.curAnim !== ae.anim) {
      a.state.setAnimation(0, ae.anim, true);
      a.curAnim = ae.anim;
      a.setupDone = false;
    }
    var tr = a.state.tracks[0];
    if (tr && tr.animation) {
      var dur = tr.animation.duration || 1e-4;
      var local = (t - ae.start) * (ae.speed || 1);
      tr.loop = !!ae.loop;
      tr.trackTime = ae.loop ? local % dur : Math.min(local, Math.max(0, dur - 1e-4));
    }
  } else if (a.curAnim === null && !a.setupDone) {
    sk.setToSetupPose();
    a.setupDone = true;
  }
  a.state.apply(sk);
  sk.updateWorldTransform();
  return true;
}

function evalOvActor(a, t) {
  var c = a.clip;
  var visible = t >= c.start && t < c.end;
  var el = a.el;
  el.style.display = visible ? 'block' : 'none';
  if (!visible) return;
  el.style.left = c.x + 'px';
  el.style.top = c.y + 'px';
  el.style.opacity = clamp01(c.opacity == null ? 1 : c.opacity);
  el.style.transform = 'translate(-50%,-50%) rotate(' + (c.rotation || 0) +
    'deg) scale(' + (c.scale || 1) + ')';
}

// ---------------- 渲染 ----------------
var time = 0, playing = false, rafId = null, lastTs = 0;
var exportMode = false, exportIdx = 0, lastCapTs = 0;

function resizeStage() {
  var vw = window.innerWidth, vh = window.innerHeight;
  var k = Math.min(vw / glState.w, vh / glState.h) || 1;
  var dw = Math.max(1, Math.floor(glState.w * k));
  var dh = Math.max(1, Math.floor(glState.h * k));
  stageBox.style.width = dw + 'px';
  stageBox.style.height = dh + 'px';
  glCanvas.style.width = dw + 'px';
  glCanvas.style.height = dh + 'px';
  overlay.style.width = glState.w + 'px';
  overlay.style.height = glState.h + 'px';
  overlay.style.transform = 'scale(' + (dw / glState.w) + ')';
}
window.addEventListener('resize', resizeStage);

function renderNow() {
  if (!model || !initGL()) return;
  var W = glState.w, H = glState.h;
  if (glCanvas.width !== W) glCanvas.width = W;
  if (glCanvas.height !== H) glCanvas.height = H;
  glCanvas.style.background = glState.bg || '#ffffff';
  var gl = context.gl;
  gl.viewport(0, 0, W, H);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);

  var cam = sceneRenderer.camera;
  cam.viewportWidth = W; cam.viewportHeight = H;
  cam.position.set(W / 2, H / 2, 0);
  cam.zoom = 1;

  // 覆盖层先求值（DOM 显隐/位置，evalOvActor 内部处理存在区间）
  var spineList = [];
  for (var id in actors) {
    var a = actors[id];
    var c = a.clip;
    if (a.kind === 'ov') { evalOvActor(a, time); continue; }
    if (time < c.start || time >= c.end || !a.ready) continue;
    evalSpineActor(a, time, H);
    spineList.push(a);
  }
  // 绘制顺序：layer 大（下层）先画，layer 小（上层）后画
  spineList.sort(function (x, y) { return y.clip.layer - x.clip.layer; });
  if (spineList.length) {
    sceneRenderer.begin();
    for (var i = 0; i < spineList.length; i++) {
      sceneRenderer.drawSkeleton(spineList[i].skeleton, true);
    }
    sceneRenderer.end();
  }
}

// ---------------- 时钟 ----------------
function setTimeInternal(t, fromClock) {
  time = Math.max(0, Math.min(t, duration));
  renderNow();
  if (!fromClock) bcall('timeUpdate', time);
}
function tick(ts) {
  if (!playing) return;
  var dt = Math.min((ts - lastTs) / 1000, 0.25);
  lastTs = ts;
  setTimeInternal(time + dt, true);
  if (exportMode) {
    // 按项目 fps 抽帧（高刷屏 rAF 更快，全抓会快放）
    var fps = (model && model.canvas && model.canvas.fps) || 30;
    var interval = 1000 / Math.max(1, fps);
    if (ts - lastCapTs >= interval - 0.5) {
      lastCapTs = ts;
      captureFrame();
    }
  }
  bcall('timeUpdate', time);
  if (time >= duration - 1e-6) { pause(); return; }
  rafId = requestAnimationFrame(tick);
}
function play() {
  if (playing) return;
  if (time >= duration - 1e-6) setTimeInternal(0, true);
  playing = true;
  lastTs = performance.now();
  rafId = requestAnimationFrame(tick);
}
function pause() {
  playing = false;
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
  bcall('timeUpdate', time);
}

// ---------------- 导出帧抓取 ----------------
var compCanvas = null, compCtx = null;
var COPY_PROPS = ('position left top width height transform transform-origin ' +
  'opacity display visibility overflow margin padding color background ' +
  'background-color border border-radius font font-size font-family ' +
  'line-height text-align fill stroke animation animation-name ' +
  'animation-duration animation-delay animation-iteration-count ' +
  'animation-timing-function animation-fill-mode white-space').split(' ');

function inlineStyles(src, dst) {
  var cs = getComputedStyle(src);
  var s = '';
  for (var i = 0; i < COPY_PROPS.length; i++) {
    var p = COPY_PROPS[i];
    var v = cs.getPropertyValue(p);
    if (v) s += p + ':' + v + ';';
  }
  dst.setAttribute('style', s);
  var sc = src.children, dc = dst.children;
  for (var j = 0; j < dc.length && j < sc.length; j++) inlineStyles(sc[j], dc[j]);
}

function captureFrame() {
  var W = glCanvas.width, H = glCanvas.height;
  if (!compCanvas) {
    compCanvas = document.createElement('canvas');
    compCtx = compCanvas.getContext('2d');
  }
  if (compCanvas.width !== W) compCanvas.width = W;
  if (compCanvas.height !== H) compCanvas.height = H;
  var ctx = compCtx;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = glState.bg || '#ffffff';
  ctx.fillRect(0, 0, W, H);
  ctx.drawImage(glCanvas, 0, 0);

  var rect = stageBox.getBoundingClientRect();
  var k = W / rect.width;
  var imgActors = [], svgActors = [];
  var kids = overlay.children;
  for (var i = 0; i < kids.length; i++) {
    if (kids[i].style.display === 'none') continue;
    var a = actors[kids[i].dataset.clipId];
    if (!a) continue;
    (a.img ? imgActors : svgActors).push(a);
  }
  // PNG：同源 file:// 图片直接 drawImage
  for (i = 0; i < imgActors.length; i++) {
    var a2 = imgActors[i], r = a2.el.getBoundingClientRect();
    try {
      ctx.drawImage(a2.img, (r.left - rect.left) * k, (r.top - rect.top) * k,
                    r.width * k, r.height * k);
    } catch (e) { log('PNG 合成失败: ' + e); }
  }
  // SVG：foreignObject + 计算样式内联（SMIL/CSS 动画取当前帧计算值）
  var finish = function () {
    // JPEG：编码快、传输小（PNG 一帧 0.3~1MB，WebChannel 传不动）
    bcall('exportFrame', compCanvas.toDataURL('image/jpeg', 0.92), exportIdx++);
  };
  if (!svgActors.length) { finish(); return; }
  var parts = [];
  for (i = 0; i < svgActors.length; i++) {
    var a3 = svgActors[i], r3 = a3.el.getBoundingClientRect();
    try {
      var clone = a3.el.cloneNode(true);
      inlineStyles(a3.el, clone);
      var xml = new XMLSerializer().serializeToString(clone);
      parts.push('<div xmlns="http://www.w3.org/1999/xhtml" style="position:absolute;left:' +
        ((r3.left - rect.left) * k) + 'px;top:' + ((r3.top - rect.top) * k) +
        'px;width:' + (r3.width * k) + 'px;height:' + (r3.height * k) + 'px;">' +
        xml + '</div>');
    } catch (e) { log('SVG 序列化失败: ' + e); }
  }
  if (!parts.length) { finish(); return; }
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H +
    '"><foreignObject width="100%" height="100%">' + parts.join('') +
    '</foreignObject></svg>';
  var img = new Image();
  img.onload = function () {
    try { ctx.drawImage(img, 0, 0); } catch (e) { log('SVG 合成失败: ' + e); }
    finish();
  };
  img.onerror = function () { finish(); };
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

// ---------------- 舞台交互（点选 / 拖动改基准位置） ----------------
function clipById(id) {
  if (!model) return null;
  for (var i = 0; i < model.clips.length; i++) {
    if (model.clips[i].id === id) return model.clips[i];
  }
  return null;
}
function toStage(clientX, clientY) {
  var r = overlay.getBoundingClientRect();
  var k = glState.w / r.width;
  return { x: (clientX - r.left) * k, y: (clientY - r.top) * k };
}
// spine 命中：脚底锚点 + 宽高构成（支持旋转的）矩形
function hitSpine(a, p) {
  var c = a.clip;
  if (time < c.start || time >= c.end || !a.ready) return false;
  var ms = c.moves || [];
  var px = c.x, py = c.y, rot = c.rotation || 0;
  var m = pickEntry(ms, time);
  if (m) {
    var k = clamp01((time - m.start) / Math.max(1e-6, m.end - m.start));
    px = lerp(m.x0, m.x1, k); py = lerp(m.y0, m.y1, k); rot = lerp(m.rot0 || 0, m.rot1 || 0, k);
  } else if (ms.length) {
    if (time < ms[0].start) { px = ms[0].x0; py = ms[0].y0; rot = ms[0].rot0 || 0; }
    else { px = ms[ms.length - 1].x1; py = ms[ms.length - 1].y1; rot = ms[ms.length - 1].rot1 || 0; }
  }
  var s = (0.5 * glState.h / a.boundsH) * (c.scale || 1);
  var th = -rot * Math.PI / 180;
  var dx = p.x - px, dy = p.y - py;
  var lx = dx * Math.cos(-th) - dy * Math.sin(-th);
  var ly = dx * Math.sin(-th) + dy * Math.cos(-th);
  var w = a.boundsW * s / 2, h = a.boundsH * s;
  var ax = a.anchor.x * s;
  var lx0 = -ax - w, lx1 = -ax + w;   // 锚点 x 居中 ±半宽
  return lx >= lx0 - 10 && lx <= lx1 + 10 && ly >= -10 && ly <= h + 10;
}

var drag = null;
stageBox.addEventListener('mousedown', function (e) {
  if (e.button !== 0) return;
  var p = toStage(e.clientX, e.clientY);
  // 覆盖层优先（DOM 自上往下）
  var t = e.target.closest ? e.target.closest('.ov') : null;
  var id = null;
  if (t) id = t.dataset.clipId;
  if (!id) {
    // spine 命中：layer 小（上）优先
    var list = [];
    for (var aid in actors) {
      var a = actors[aid];
      if (a.kind === 'spine' && hitSpine(a, p)) list.push(a);
    }
    list.sort(function (x, y) { return x.clip.layer - y.clip.layer; });
    if (list.length) id = list[0].clip.id;
  }
  bcall('clipSelected', id || '');
  if (!id) return;
  var c = clipById(id);
  drag = { id: id, sx: e.clientX, sy: e.clientY, x0: c.x, y0: c.y, moved: false };
  e.preventDefault();
});
document.addEventListener('mousemove', function (e) {
  if (!drag) return;
  var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
  if (!drag.moved && Math.abs(dx) + Math.abs(dy) <= 4) return;
  drag.moved = true;
  var r = overlay.getBoundingClientRect();
  var k = glState.w / r.width;
  var c = clipById(drag.id);
  if (!c) { drag = null; return; }
  c.x = Math.round(drag.x0 + dx * k);
  c.y = Math.round(drag.y0 + dy * k);
  renderNow();  // 拖动期间 JS 自渲染，不回流 Qt（mouseup 才报）
});
document.addEventListener('mouseup', function () {
  if (!drag) return;
  var d = drag; drag = null;
  if (d.moved) {
    var c = clipById(d.id);
    if (c) bcall('clipMoved', d.id, c.x, c.y);
  }
});

// ---------------- 模型同步 ----------------
function reconcile() {
  // 删掉消失或类型/素材变化的 actor
  for (var id in actors) {
    var c = clipById(id);
    var a = actors[id];
    if (!c || c.type !== a.clip.type ||
        (a.kind === 'spine' && c.asset !== a.clip.asset)) {
      if (a.el) a.el.remove();
      delete actors[id];
    } else {
      a.clip = c;  // 换引用，保留运行时状态
    }
  }
  // 新建
  for (var i = 0; i < model.clips.length; i++) {
    var clip = model.clips[i];
    if (!actors[clip.id]) {
      if (clip.type === 'spine') ensureSkeletonData(clip.asset, model.spine[clip.asset]);
      actors[clip.id] = createActor(clip);
    }
  }
  // 覆盖层按 layer 重排：layer 小（上）后 append → DOM 后 = 视觉上层
  var ovs = [];
  for (id in actors) {
    if (actors[id].kind === 'ov') ovs.push(actors[id]);
  }
  ovs.sort(function (x, y) { return y.clip.layer - x.clip.layer; });
  for (i = 0; i < ovs.length; i++) overlay.appendChild(ovs[i].el);
}

// ---------------- 对外 API（Qt 经 runJavaScript 调用） ----------------
window.stageApi = {
  loadProject: function (payload) {
    try {
      // Qt 侧 json.dumps 后直接内联为对象字面量；也兼容 JSON 字符串
      model = typeof payload === 'string' ? JSON.parse(payload) : payload;
      duration = Math.max(0.1, parseFloat(model.duration) || 5);
      glState = {
        w: parseInt(model.canvas && model.canvas.w, 10) || 1280,
        h: parseInt(model.canvas && model.canvas.h, 10) || 720,
        bg: (model.canvas && model.canvas.bg) || '#ffffff',
      };
      readySent = false;
      initGL();
      resizeStage();
      reconcile();
      setTimeInternal(Math.min(time, duration));
    } catch (e) { log('loadProject 失败: ' + e); }
  },
  setTime: function (t) { pause(); setTimeInternal(parseFloat(t) || 0); },
  play: play,
  pause: pause,
  setExportMode: function (on) {
    exportMode = !!on;
    exportIdx = 0;
    lastCapTs = 0;
  },
  // Qt 拖放落点换算用：舞台在窗口中的显示矩形与缩放
  viewInfo: function () {
    var r = stageBox.getBoundingClientRect();
    return JSON.stringify({
      left: r.left, top: r.top, width: r.width, height: r.height,
      scale: r.width ? glState.w / r.width : 1,
    });
  },
  // 集成测试探针：内部状态快照
  probe: function () {
    var list = [];
    for (var id in actors) {
      var a = actors[id];
      var it = { id: id, kind: a.kind, ready: !!a.ready,
                 start: a.clip.start, end: a.clip.end,
                 layer: a.clip.layer, x: a.clip.x, y: a.clip.y };
      if (a.kind === 'spine' && a.ready) {
        var tr = a.state.tracks[0];
        it.anim = tr && tr.animation ? tr.animation.name : null;
        it.trackTime = tr ? tr.trackTime : null;
        it.skelX = a.skeleton.x;
        it.skelY = a.skeleton.y;
        it.alpha = a.skeleton.color ? a.skeleton.color.a : 1;
      }
      list.push(it);
    }
    return JSON.stringify({ time: time, duration: duration,
                            canvas: glState, actors: list });
  },
};
})();
