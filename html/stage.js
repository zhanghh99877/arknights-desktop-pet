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
// 注意：必须按真实参数个数调用——多传 undefined 会被 QtWebChannel 序列化成
// null，导致 Slot 参数个数不匹配而被静默丢弃（timeUpdate 曾因此永远到不了 Qt）
function bcall(name, a, b, c, d, f) {
  var br = window.bridge;
  if (!br) return;
  try {
    if (a === undefined) br[name]();
    else if (b === undefined) br[name](a);
    else if (c === undefined) br[name](a, b);
    else if (d === undefined) br[name](a, b, c);
    else if (f === undefined) br[name](a, b, c, d);
    else br[name](a, b, c, d, f);
  } catch (e) { console.warn('[stage] bridge.' + name, e); }
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
// move 条目求值（spine/png/svg 通用）：命中 → 线性插值；首条目之前 →
// 其起点；条目间/全部结束 → 冻结在最近已开始条目的终点（不提前跳位置）
function evalMove(c, t) {
  var ms = c.moves;
  if (!ms || !ms.length) return { x: c.x, y: c.y, rot: c.rotation || 0 };
  var arr = ms.slice().sort(function (a, b) { return a.start - b.start; });
  if (t < arr[0].start) {
    return { x: arr[0].x0, y: arr[0].y0, rot: arr[0].rot0 || 0 };
  }
  for (var i = arr.length - 1; i >= 0; i--) {
    var m = arr[i];
    if (t < m.start) continue;
    if (t >= m.end) return { x: m.x1, y: m.y1, rot: m.rot1 || 0 };
    var k = clamp01((t - m.start) / Math.max(1e-6, m.end - m.start));
    return { x: lerp(m.x0, m.x1, k), y: lerp(m.y0, m.y1, k),
             rot: lerp(m.rot0 || 0, m.rot1 || 0, k) };
  }
  return { x: c.x, y: c.y, rot: c.rotation || 0 };
}

// ---------------- DOM ----------------
var stageBox = document.getElementById('stage');
var bgCanvas = document.getElementById('bg');
var bgCtx = bgCanvas.getContext('2d');
var glCanvas = document.getElementById('gl');
var overlay = document.getElementById('overlay');
// 顶层世界（负数图层 = 压住一切基础层）
var bgTopCanvas = document.getElementById('bgTop');
var bgTopCtx = bgTopCanvas.getContext('2d');
var glTopCanvas = document.getElementById('glTop');
var overlayTop = document.getElementById('overlayTop');

// ---------------- GL ----------------
var context = null, sceneRenderer = null, assetManager = null;
var contextTop = null, sceneRendererTop = null, assetManagerTop = null;
function initGL() {
  if (context) return true;
  try {
    context = new spine.webgl.ManagedWebGLRenderingContext(glCanvas, {
      alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true,
    });
    sceneRenderer = new spine.webgl.SceneRenderer(glCanvas, context, true);
    assetManager = new spine.webgl.AssetManager(context);
    // 顶层世界用独立 WebGL 上下文（纹理不跨上下文，负图层骨架独立加载）
    contextTop = new spine.webgl.ManagedWebGLRenderingContext(glTopCanvas, {
      alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true,
    });
    sceneRendererTop = new spine.webgl.SceneRenderer(glTopCanvas, contextTop,
                                                     true);
    assetManagerTop = new spine.webgl.AssetManager(contextTop);
    return true;
  } catch (e) { log('WebGL 初始化失败: ' + e); return false; }
}

// ---------------- 模型状态 ----------------
var model = null;              // {canvas:{w,h,bg}, duration, layers, clips, spine:{模型:{skel,atlas}}, assets}
var actors = {};               // clipId -> actor
var duration = 5;
var glState = { w: 1280, h: 720, bg: '#ffffff' };

// 骨架数据缓存：asset -> {status,data,anchor,boundsW,boundsH}。
// 基础世界与顶层世界各自一份（WebGL 纹理不跨上下文共享）
var skelLib = {};
var skelLibTop = {};

// ---------------- 骨架数据加载 ----------------
function ensureSkeletonData(asset, info, top) {
  var cache = top ? skelLibTop : skelLib;
  var am = top ? assetManagerTop : assetManager;
  var e = cache[asset];
  if (e) return e;
  e = { status: 'loading', data: null, anchor: null, boundsW: 100, boundsH: 100 };
  cache[asset] = e;
  try {
    am.loadBinary(info.skel);
    am.loadTextureAtlas(info.atlas);
  } catch (err) { e.status = 'err'; log('骨架加载发起失败 ' + asset + ': ' + err); }
  return e;
}

function finalizeSkeletonData(asset, e, top) {
  try {
    var am = top ? assetManagerTop : assetManager;
    var atlas = am.get(model.spine[asset].atlas);
    var binary = am.get(model.spine[asset].skel);
    var data = new spine.SkeletonBinary(new spine.AtlasAttachmentLoader(atlas))
      .readSkeletonData(binary);
    e.data = data;
    e.status = 'ok';   // 锚点/包围盒由 actor 实例化时从活骨架量（见下）
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
  var worlds = [[skelLib, assetManager], [skelLibTop, assetManagerTop]];
  for (var wi = 0; wi < worlds.length; wi++) {
    var cache = worlds[wi][0], am = worlds[wi][1];
    for (var asset in cache) {
      var e = cache[asset];
      if (e.status === 'loading') {
        loading = true;
        if (am.hasErrors()) {
          e.status = 'err';
          log('骨架资源加载出错 ' + asset + ': ' +
              JSON.stringify(am.getErrors()));
        }
      }
    }
  }
  if (assetManager.isLoadingComplete() && assetManagerTop.isLoadingComplete()) {
    for (asset in skelLib) {
      if (skelLib[asset].status === 'loading') finalizeSkeletonData(asset, skelLib[asset], false);
    }
    for (asset in skelLibTop) {
      if (skelLibTop[asset].status === 'loading') finalizeSkeletonData(asset, skelLibTop[asset], true);
    }
    instantiatePending();
  }
  if (!readySent && !loading) { readySent = true; bcall('stageReady'); }
}, 150);

// ---------------- Actor ----------------
function SpineActor(clip) {
  this.kind = 'spine';
  this.clip = clip;
  this.top = clip.layer < 0;            // 顶层世界（负图层）
  this.ready = false;
  this.skeleton = null;
  this.state = null;
  this.curAnim = null;
  this.setupDone = false;
  this.anchor = { x: 0, y: 0 };
  this.boundsW = 100; this.boundsH = 100;
  this.pending = true;
  // 加载占位：骨架资源就绪前显示位置提示（拖入 Spine 立即可见落点）
  var el = document.createElement('div');
  el.className = 'ov';
  el.dataset.clipId = clip.id;
  el.style.cssText = 'color:#888;font:12px sans-serif;cursor:move;white-space:nowrap;';
  el.textContent = '⏳ ' + (clip.name || clip.asset);
  (this.top ? overlayTop : overlay).appendChild(el);
  this.el = el;
}
SpineActor.prototype.instantiate = function (e) {
  if (this.el) { this.el.remove(); this.el = null; }
  this.skeleton = new spine.Skeleton(e.data);
  if (e.data.skins.length) {
    this.skeleton.setSkinByName(e.data.skins[0].name);
    this.skeleton.setSlotsToSetupPose();
  }
  this.skeleton.setToSetupPose();
  // 锚点/包围盒从「活骨架」量：origin 处、setup pose 的 bounds 底边中心。
  // 不能用临时骨架在加载时量——实测 3.8 运行时下两者结果可能差很远
  // （曾把锚点量成 423 而实际 -50，角色整体偏 470px）。
  this.skeleton.x = 0; this.skeleton.y = 0;
  this.skeleton.scaleX = 1; this.skeleton.scaleY = 1;
  this.skeleton.updateWorldTransform();
  var off = new spine.Vector2(), size = new spine.Vector2();
  this.skeleton.getBounds(off, size, []);
  this.anchor = { x: off.x + size.x / 2, y: off.y };
  this.boundsW = Math.max(1, size.x);
  this.boundsH = Math.max(1, size.y);
  var sd = new spine.AnimationStateData(e.data);
  sd.defaultMix = 0;   // 确定性 seek：条目切换硬切（交叉淡化依赖 update 推进）
  this.state = new spine.AnimationState(sd);
  this.ready = true;
  this.pending = false;
};

function OvActor(clip, assetsBase) {
  this.kind = 'ov';
  this.clip = clip;
  this.top = clip.layer < 0;            // 顶层世界（负图层）
  this.img = null;
  this.natW = 200; this.natH = 200;   // 图片未加载前的占位尺寸
  var host = this.top ? overlayTop : overlay;
  // 素材 URL 带版本参数：QtWebEngine 会缓存 file:// 响应，重新生成
  // 项目后同路径文件内容变了但缓存仍回旧版（画布整体拿旧素材）
  var url = assetsBase + encodeURIComponent(clip.asset) +
    (model.assetsRev ? '?v=' + model.assetsRev : '');
  if (clip.type === 'png') {
    // PNG 画进底层 #bg 2D 画布（可垫在 spine 下面）；不走 DOM
    var img = new Image();
    var self = this;
    img.onload = function () {
      self.natW = img.naturalWidth || 200;
      self.natH = img.naturalHeight || 200;
      renderNow();
    };
    img.src = url;
    this.img = img;
    this.el = null;
  } else { // svg：内联 DOM，SMIL/CSS 动画才会动；DOM 层永远在最上
    var el = document.createElement('div');
    el.className = 'ov';
    el.dataset.clipId = clip.id;
    this.el = el;
    var wrap = document.createElement('div');
    el.appendChild(wrap);
    fetch(url)
      .then(function (r) { return r.text(); })
      .then(function (txt) { wrap.innerHTML = txt; })
      .catch(function (e) { log('SVG 加载失败 ' + clip.asset + ': ' + e); });
    host.appendChild(el);
  }
}

// PNG 片段：画进对应世界的 2D 画布（正图层 #bg / 负图层 #bgTop）
function evalPngActor(a, t, ghost, ctx) {
  var c = a.clip;
  if (!layerVisible(c.layer) || !a.img) return;
  if (t < c.start || t >= c.end) {
    // 时间窗外只有拖动 ghost 预览（夹到窗内求值，半透明跟手）
    if (!ghost) return;
    t = Math.max(c.start, Math.min(t, c.end - 1e-3));
  }
  var mv = evalMove(c, t);
  var w = a.natW * (c.scale || 1), h = a.natH * (c.scale || 1);
  ctx.save();
  ctx.translate(mv.x, mv.y);
  ctx.rotate(mv.rot * Math.PI / 180);
  ctx.globalAlpha = clamp01(c.opacity == null ? 1 : c.opacity) *
    (ghost ? 0.55 : 1);
  try { ctx.drawImage(a.img, -w / 2, -h / 2, w, h); } catch (e) {}
  ctx.restore();
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
      var e = (a.clip.layer < 0 ? skelLibTop : skelLib)[a.clip.asset];
      if (e && e.status === 'ok') { a.instantiate(e); changed = true; }
      else if (e && e.status === 'err') { a.pending = false; }
    }
  }
  if (changed) renderNow();
}

// ---------------- 求值 ----------------
// spine 片段在 t 时刻：move 条目走通用 evalMove，anim 条目 trackTime 直写
function evalSpineActor(a, t, H) {
  var c = a.clip;
  var mv = evalMove(c, t);
  var px = mv.x, py = mv.y, rot = mv.rot;
  // 朝向先行：当前动作条目的 flip 决定水平镜像（"转身"）
  var ae = pickEntry(c.anims || [], t);
  a.curFlip = !!(ae && ae.flip);
  // clip.scale 为倍率：1.0 = 角色高 画布半高（按 setup 包围盒归一）；
  // 负值 = 静态水平镜像；AnimEntry.flip 在其之上按段切换（转身）
  var s = (0.5 * H / a.boundsH) * Math.abs(c.scale || 1);
  var sk = a.skeleton;
  var flip = (a.curFlip !== ((c.scale || 1) < 0)) ? -1 : 1;
  sk.scaleX = s * flip;
  sk.scaleY = Math.abs(s);
  if (!sk.color) sk.color = new spine.Color(1, 1, 1, 1);
  sk.color.a = clamp01(c.opacity == null ? 1 : c.opacity);

  var ae = pickEntry(c.anims || [], t);
  var isProc = false, procLocal = 0, targetAnim = '';
  if (ae && ae.anim) {
    // 自创程序动作：PROCS 注册表命中 → 底层播其 base 官方动作，姿势叠加
    isProc = !!(window.PROCS && window.PROCS[ae.anim]);
    targetAnim = ae.anim;
    if (isProc) {
      var base = window.PROCS[ae.anim].base;
      targetAnim = (base && sk.data.findAnimation(base)) ? base : '';
    }
    if (a.curAnim !== ae.anim) {
      if (window.__clearFx) window.__clearFx();
      try {
        if (targetAnim) a.state.setAnimation(0, targetAnim, true);
        else if (sk.data.findAnimation(ae.anim)) a.state.setAnimation(0, ae.anim, true);
        else a.state.setToSetupPose ? null : null;
      } catch (e) { try { a.state.setAnimation(0, ae.anim, true); } catch (e2) {} }
      a.curAnim = ae.anim;
      a.setupDone = false;
    }
    var tr = a.state.tracks[0];
    if (tr && tr.animation) {
      var dur = tr.animation.duration || 1e-4;
      var local = (t - ae.start) * (ae.speed || 1);
      procLocal = local;
      tr.loop = !!ae.loop;
      tr.trackTime = ae.loop ? local % dur : Math.min(local, Math.max(0, dur - 1e-4));
    }
  } else if (a.curAnim === null && !a.setupDone) {
    sk.setToSetupPose();
    a.setupDone = true;
  }
  a.state.apply(sk);
  // 旋转：spine 3.8 的 skeleton.rotation 是死字段（运行时无消费者），
  // 必须拧根骨骼，正值=世界逆时针=屏幕逆时针，用户角是屏幕顺时针→取负。
  var root = sk.bones[0];
  if (root) {
    root.rotation = (root.data ? root.data.rotation : 0) - rot;
  }
  // 程序动作叠加（updateWorldTransform 之前改骨骼才生效）
  if (isProc) {
    window.__fxOwner = c.id;
    try { window.PROCS[ae.anim].pose(sk, procLocal, window.procFx); } catch (e) {}
  }
  sk.updateWorldTransform();
  // 根骨骼锚定：动画常整体平移根骨骼（宿舍系 Default 能偏 470px），
  // 把动画后的根骨骼世界位置钉到目标点——动画内部运动保留，
  // 但整体不跑偏。旋转也自然绕根骨骼（≈身体中心）进行。
  var twx = px, twy = H - py;   // 世界 y 向上
  sk.x += twx - root.worldX;
  sk.y += twy - root.worldY;
  sk.updateWorldTransform();
  // 缓存本轮包围盒（世界坐标，含旋转）：给点选命中用
  var off = evalSpineActor._off || (evalSpineActor._off = new spine.Vector2());
  var size = evalSpineActor._sz || (evalSpineActor._sz = new spine.Vector2());
  try {
    sk.getBounds(off, size, []);
    a.lastBounds = { x: off.x, y: off.y, w: size.x, h: size.y };
  } catch (e) {}
  return true;
}

// spine 加载占位：跟随片段基准位置，就绪前提示落点
function evalPlaceholder(a, t) {
  var c = a.clip;
  var vis = layerVisible(c.layer) && t >= c.start && t < c.end;
  a.el.style.display = vis ? 'block' : 'none';
  if (!vis) return;
  a.el.style.left = c.x + 'px';
  a.el.style.top = c.y + 'px';
  a.el.style.transform = 'translate(-50%,-100%)';
}

function evalOvActor(a, t, ghost) {
  if (!a.el) return;   // PNG 走 #bg 画布，无 DOM
  var c = a.clip;
  if (!layerVisible(c.layer)) { a.el.style.display = 'none'; return; }
  if (t < c.start || t >= c.end) {
    if (!ghost) { a.el.style.display = 'none'; return; }
    t = Math.max(c.start, Math.min(t, c.end - 1e-3));   // 拖动 ghost 预览
  }
  var mv = evalMove(c, t);
  var el = a.el;
  el.style.display = 'block';
  el.style.left = mv.x + 'px';
  el.style.top = mv.y + 'px';
  el.style.opacity = clamp01(c.opacity == null ? 1 : c.opacity) *
    (ghost ? 0.55 : 1);
  el.style.transform = 'translate(-50%,-50%) rotate(' + mv.rot +
    'deg) scale(' + (c.scale || 1) + ')';
  el.__lastRect = el.getBoundingClientRect();  // 供时间窗外点选命中
}

// ---------------- 渲染 ----------------
var time = 0, playing = false, rafId = null, lastTs = 0;
var exportMode = false, exportIdx = 0, capAcc = 0;

function resizeStage() {
  var vw = window.innerWidth, vh = window.innerHeight;
  var k = Math.min(vw / glState.w, vh / glState.h) || 1;
  var dw = Math.max(1, Math.floor(glState.w * k));
  var dh = Math.max(1, Math.floor(glState.h * k));
  stageBox.style.width = dw + 'px';
  stageBox.style.height = dh + 'px';
  bgCanvas.style.width = dw + 'px';
  bgCanvas.style.height = dh + 'px';
  glCanvas.style.width = dw + 'px';
  glCanvas.style.height = dh + 'px';
  bgTopCanvas.style.width = dw + 'px';
  bgTopCanvas.style.height = dh + 'px';
  glTopCanvas.style.width = dw + 'px';
  glTopCanvas.style.height = dh + 'px';
  overlay.style.width = glState.w + 'px';
  overlay.style.height = glState.h + 'px';
  overlay.style.transform = 'scale(' + (dw / glState.w) + ')';
  overlayTop.style.width = glState.w + 'px';
  overlayTop.style.height = glState.h + 'px';
  overlayTop.style.transform = 'scale(' + (dw / glState.w) + ')';
}
window.addEventListener('resize', resizeStage);

function renderNow() {
  if (!model || !initGL()) return;
  var W = glState.w, H = glState.h;
  if (glCanvas.width !== W) glCanvas.width = W;
  if (glCanvas.height !== H) glCanvas.height = H;
  if (bgCanvas.width !== W) bgCanvas.width = W;
  if (bgCanvas.height !== H) bgCanvas.height = H;
  if (glTopCanvas.width !== W) glTopCanvas.width = W;
  if (glTopCanvas.height !== H) glTopCanvas.height = H;
  if (bgTopCanvas.width !== W) bgTopCanvas.width = W;
  if (bgTopCanvas.height !== H) bgTopCanvas.height = H;
  glCanvas.style.background = 'transparent';
  glTopCanvas.style.background = 'transparent';
  var bg = glState.bg || '#ffffff';
  bgCanvas.style.background = bg;
  bgCtx.fillStyle = bg;
  bgCtx.fillRect(0, 0, W, H);
  bgTopCtx.clearRect(0, 0, W, H);

  // 1) 基础底层：正图层 PNG（layer 大先画，小的后画在上）；
  //    负图层 PNG 进顶层世界（更少负的先画，更多负的在后=更上）
  var pngsPos = [], pngsNeg = [];
  for (var id in actors) {
    var pa = actors[id];
    if (pa.kind === 'ov' && pa.img) {
      (pa.clip.layer < 0 ? pngsNeg : pngsPos).push(pa);
    }
  }
  pngsPos.sort(function (x, y) { return y.clip.layer - x.clip.layer; });
  pngsNeg.sort(function (x, y) { return x.clip.layer - y.clip.layer; });
  for (var pi = 0; pi < pngsPos.length; pi++) {
    evalPngActor(pngsPos[pi], time, drag && drag.id === pngsPos[pi].clip.id,
                 bgCtx);
  }
  for (pi = 0; pi < pngsNeg.length; pi++) {
    evalPngActor(pngsNeg[pi], time, drag && drag.id === pngsNeg[pi].clip.id,
                 bgTopCtx);
  }

  // 2) 中层：spine（GL 透明底）
  var gl = context.gl;
  gl.viewport(0, 0, W, H);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);

  var cam = sceneRenderer.camera;
  cam.viewportWidth = W; cam.viewportHeight = H;
  cam.position.set(W / 2, H / 2, 0);
  cam.zoom = 1;

  // 3) DOM/SVG 与 spine 求值：正图层走基础层，负图层走顶层世界
  var spineList = [], spineTopList = [];
  for (id in actors) {
    var a = actors[id];
    var c = a.clip;
    if (a.kind === 'ov') {
      if (a.el) evalOvActor(a, time, drag && drag.id === c.id);
      continue;
    }
    if (!layerVisible(c.layer)) {
      if (a.el) a.el.style.display = 'none';
      if (window.__fxOwner === c.id && window.__clearFx) window.__clearFx();
      continue;
    }
    if (!a.ready) {
      if (a.el) evalPlaceholder(a, time);   // spine 加载占位
      continue;
    }
    if (time < c.start || time >= c.end) {
      if (window.__fxOwner === c.id && window.__clearFx) window.__clearFx();
      // 拖时间窗外的 spine：画半透明 ghost，让拖动有视觉反馈
      if (drag && drag.id === c.id) {
        var gt = Math.max(c.start, Math.min(time, c.end - 1e-3));
        evalSpineActor(a, gt, H);
        var gsk = a.skeleton;
        if (!gsk.color) gsk.color = new spine.Color(1, 1, 1, 1);
        gsk.color.a *= 0.55;
        gsk.updateWorldTransform();
        (a.clip.layer < 0 ? spineTopList : spineList).push(a);
      }
      continue;
    }
    evalSpineActor(a, time, H);
    (a.clip.layer < 0 ? spineTopList : spineList).push(a);
  }
  // 绘制顺序：layer 大（下层）先画，layer 小（上层）后画；
  // 顶层世界内更少负的先画、更多负的在后=更上
  spineList.sort(function (x, y) { return y.clip.layer - x.clip.layer; });
  spineTopList.sort(function (x, y) { return x.clip.layer - y.clip.layer; });
  if (spineList.length) {
    sceneRenderer.begin();
    for (var i = 0; i < spineList.length; i++) {
      sceneRenderer.drawSkeleton(spineList[i].skeleton, true);
    }
    sceneRenderer.end();
  }

  // 4) 顶层世界：负图层 PNG 画布 + 负图层 spine（压住一切基础层）
  var glT = contextTop.gl;
  glT.viewport(0, 0, W, H);
  glT.clearColor(0, 0, 0, 0);
  glT.clear(glT.COLOR_BUFFER_BIT);
  var camT = sceneRendererTop.camera;
  camT.viewportWidth = W; camT.viewportHeight = H;
  camT.position.set(W / 2, H / 2, 0);
  camT.zoom = 1;
  if (spineTopList.length) {
    sceneRendererTop.begin();
    for (i = 0; i < spineTopList.length; i++) {
      sceneRendererTop.drawSkeleton(spineTopList[i].skeleton, true);
    }
    sceneRendererTop.end();
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
  var rawMs = Math.min(ts - lastTs, 250);   // 抽帧累积用原始间隔（钳上限防爆）
  var dt = Math.min((ts - lastTs) / 1000, 0.25);
  lastTs = ts;
  setTimeInternal(time + dt, true);
  if (exportMode) {
    // 按项目 fps 抽帧：累积真实流逝时间到阈值就抓，避免闸值比较在
    // 16.7ms rAF 网格下漂移（实测平均 24fps → 视频变 4.3s）
    var fps = (model && model.canvas && model.canvas.fps) || 30;
    capAcc += rawMs;
    var interval = 1000 / Math.max(1, fps);
    while (capAcc >= interval - 0.01) {
      capAcc -= interval;
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
  // 合成顺序与预览一致：#bg（底色+正PNG）→ #gl（正spine）→ 正SVG DOM →
  // 顶层世界 #bgTop（负PNG）→ #glTop（负spine）→ 负SVG DOM
  ctx.clearRect(0, 0, W, H);
  try { ctx.drawImage(bgCanvas, 0, 0); } catch (e) {}
  try { ctx.drawImage(glCanvas, 0, 0); } catch (e) {}

  var rect = stageBox.getBoundingClientRect();
  var k = W / rect.width;
  // SVG：foreignObject + 计算样式内联（SMIL/CSS 动画取当前帧计算值）
  var finish = function () {
    // JPEG：编码快、传输小（PNG 一帧 0.3~1MB，WebChannel 传不动）
    bcall('exportFrame', compCanvas.toDataURL('image/jpeg', 0.92), exportIdx++);
  };
  var buildSvgImage = function (container, cb) {
    var svgActors = [];
    var kids = container.children;
    for (var i = 0; i < kids.length; i++) {
      if (kids[i].style.display === 'none') continue;
      var a = actors[kids[i].dataset.clipId];
      if (a && a.el) svgActors.push(a);   // 只剩 SVG/HTML
    }
    if (!svgActors.length) { cb(null); return; }
    var parts = [];
    for (i = 0; i < svgActors.length; i++) {
      var a3 = svgActors[i], r3 = a3.el.getBoundingClientRect();
      try {
        var clone = a3.el.cloneNode(true);
        inlineStyles(a3.el, clone);
        // wrapper 按屏幕 AABB 定位；克隆体需复现原元素的 scale/rotate：
        // 取其计算矩阵，前面补 translate(wrapper半宽高) 让中心对齐
        // （transform:none 会丢缩放——1280 宽的板按原尺寸溢出 wrapper）
        clone.style.position = 'absolute';
        clone.style.left = '0px';
        clone.style.top = '0px';
        var csw = r3.width * k, csh = r3.height * k;
        clone.style.transformOrigin = '50% 50%';
        clone.style.transform =
          'translate(' + csw / 2 + 'px,' + csh / 2 + 'px) ' +
          getComputedStyle(a3.el).transform;
        var xml = new XMLSerializer().serializeToString(clone);
        parts.push('<div xmlns="http://www.w3.org/1999/xhtml" style="position:absolute;left:' +
          ((r3.left - rect.left) * k) + 'px;top:' + ((r3.top - rect.top) * k) +
          'px;width:' + (r3.width * k) + 'px;height:' + (r3.height * k) + 'px;">' +
          xml + '</div>');
      } catch (e) { log('SVG 序列化失败: ' + e); }
    }
    if (!parts.length) { cb(null); return; }
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H +
      '"><foreignObject width="100%" height="100%">' + parts.join('') +
      '</foreignObject></svg>';
    var img = new Image();
    img.onload = function () { cb(img); };
    img.onerror = function () { cb(null); };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  };
  // 合成链：正SVG → 顶层世界画布 → 负SVG → 交付
  buildSvgImage(overlay, function (img1) {
    if (img1) { try { ctx.drawImage(img1, 0, 0); } catch (e) {} }
    try { ctx.drawImage(bgTopCanvas, 0, 0); } catch (e) {}
    try { ctx.drawImage(glTopCanvas, 0, 0); } catch (e) {}
    buildSvgImage(overlayTop, function (img2) {
      if (img2) { try { ctx.drawImage(img2, 0, 0); } catch (e) {} }
      finish();
    });
  });
}

// ---------------- 舞台交互（点选 / 拖动改基准位置） ----------------
// 素材拖放走 HTML5 DnD（Qt 侧 QWebEngineView 开 acceptDrops 会吞掉
// 页面鼠标事件，导致点选/拖动失效——这是 Qt on Windows 的已知行为）。
// Qt 列表拖来的自定义 mime 不一定映射进 dataTransfer，故同时用
// text/plain 携带 JSON 兜底。
var DROP_MIME = 'application/x-prts-asset';
stageBox.addEventListener('dragover', function (e) {
  var types = e.dataTransfer ? e.dataTransfer.types : [];
  if (types.indexOf(DROP_MIME) >= 0 || types.indexOf('text/plain') >= 0) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }
});
stageBox.addEventListener('drop', function (e) {
  var raw = '';
  try {
    raw = e.dataTransfer.getData(DROP_MIME) ||
          e.dataTransfer.getData('text/plain') || '';
  } catch (err) { return; }
  var info = null;
  try { info = JSON.parse(raw); } catch (err) { return; }
  if (!info || !info.name) return;
  e.preventDefault();
  var p = toStage(e.clientX, e.clientY);
  bcall('assetDropped', info.kind || '', info.name, p.x, p.y);
});

function layerVisible(idx) {
  var v = model && model.layersVisible;
  return !v || v[idx] !== false;
}

// ---------------- 自创程序动作（Spine/proc/<模型>/*.js） ----------------
// 与播放页同一套契约：动作文件注册 window.PROCS[动作名] = {base, pose}；
// pose(sk, t, fx) 在官方 apply 之后、updateWorldTransform 之前叠加姿势。
window.PROCS = {};
window.__fxOwner = null;

/* 特效叠加层：骨世界坐标 + 像素偏移 → 屏幕定位（emoji 挂在 #overlay 里） */
window.procFx = function (id, bone, dxPx, dyPx, opacity, emoji) {
  var el = document.getElementById(id);
  if (opacity <= 0) { if (el) el.style.display = 'none'; return; }
  if (!bone || !model) return;
  var W = glState.w, H = glState.h;
  if (!el) {
    el = document.createElement('div');
    el.id = id;
    el.style.cssText = 'position:absolute;font-size:26px;pointer-events:none;display:none;z-index:5;transform:translate(-50%,-50%);';
    overlay.appendChild(el);
    window.__fxIds = window.__fxIds || [];
    window.__fxIds.push(id);
  }
  // 世界 → 舞台逻辑像素（y 翻转）
  el.textContent = emoji;
  el.style.left = bone.worldX + 'px';
  el.style.top = (H - bone.worldY) + 'px';
  el.style.marginLeft = dxPx + 'px';
  el.style.marginTop = dyPx + 'px';
  el.style.opacity = opacity;
  el.style.display = 'block';
};
window.__clearFx = function () {
  (window.__fxIds || []).forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  });
  window.__fxIds = [];
  window.__fxOwner = null;
};

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
// spine 命中：用上一轮渲染的真实包围盒（世界坐标，含动画姿态与旋转）
function hitSpine(a, p) {
  var c = a.clip;
  if (time < c.start || time >= c.end || !a.ready || !a.lastBounds) return false;
  var wx = p.x, wy = glState.h - p.y;
  var b = a.lastBounds;
  return wx >= b.x - 14 && wx <= b.x + b.w + 14 &&
         wy >= b.y - 14 && wy <= b.y + b.h + 14;
}

// 点选：收集落点命中的全部片段（覆盖层矩形 + spine 包围盒），
// 多次点击循环切换选中——重叠时 buried 对象也能选中
function hitsAt(p) {
  var hits = [];
  // PNG 片段（画在 #bg）：中心锚点旋转矩形命中。
  // 不做时间窗判定——播放头在区间外也应能选中拖走（配合 ghost 预览）。
  for (var pid in actors) {
    var pa = actors[pid];
    if (!(pa.kind === 'ov' && pa.img)) continue;
    var pc = pa.clip;
    if (!layerVisible(pc.layer)) continue;
    var pw = pa.natW * (pc.scale || 1), phh = pa.natH * (pc.scale || 1);
    var mv = evalMove(pc, time);   // 命中跟随 move 后的实际位置
    var pth = -(mv.rot) * Math.PI / 180;
    var pdx = p.x - mv.x, pdy = p.y - mv.y;
    var plx = pdx * Math.cos(-pth) - pdy * Math.sin(-pth);
    var ply = pdx * Math.sin(-pth) + pdy * Math.cos(-pth);
    if (Math.abs(plx) <= pw / 2 + 12 && Math.abs(ply) <= phh / 2 + 12) {
      hits.push(pc.id);
    }
  }
  var domContainers = [overlay, overlayTop];
  for (var di = 0; di < domContainers.length; di++) {
    var orect = domContainers[di].getBoundingClientRect();
    var k = glState.w / orect.width;
    var kids = domContainers[di].children;
    for (var i = 0; i < kids.length; i++) {
      var el = kids[i];
      var cid = el.dataset.clipId;
      if (!cid) continue;
      var c = clipById(cid);
      if (!c || !layerVisible(c.layer)) continue;
      // SVG：优先当前矩形；display:none 时用上次可见矩形（拖时间窗外的片段）
      var r = el.getBoundingClientRect();
      if ((r.width === 0 || r.height === 0) && el.__lastRect) r = el.__lastRect;
      var x0 = (r.left - orect.left) * k, y0 = (r.top - orect.top) * k;
      var x1 = (r.right - orect.left) * k, y1 = (r.bottom - orect.top) * k;
      if (p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1) hits.push(c.id);
    }
  }
  for (var aid in actors) {
    var a = actors[aid];
    if (a.kind !== 'spine' || !a.ready || !layerVisible(a.clip.layer)) continue;
    var hit;
    if (a.lastBounds) {
      var wx = p.x, wy = glState.h - p.y;
      var b = a.lastBounds;
      hit = wx >= b.x - 20 && wx <= b.x + b.w + 20 &&
            wy >= b.y - 20 && wy <= b.y + b.h + 20;
    } else {
      // 从未渲染过（播放头从未进过区间）：setup 包围盒近似
      var sc = a.clip;
      var s0 = (0.5 * glState.h / a.boundsH) * (sc.scale || 1);
      var w0 = a.boundsW * s0, h0 = a.boundsH * s0;
      hit = Math.abs(p.x - sc.x) <= w0 / 2 + 20 &&
            Math.abs(p.y - (sc.y - h0 / 2)) <= h0 / 2 + 20;
    }
    if (hit) hits.push(a.clip.id);
  }
  // layer 小（上）优先
  hits.sort(function (x, y) {
    var cx = clipById(x), cy = clipById(y);
    return (cx ? cx.layer : 99) - (cy ? cy.layer : 99);
  });
  return hits;
}

var drag = null;
stageBox.addEventListener('mousedown', function (e) {
  if (e.button !== 0) return;
  var p = toStage(e.clientX, e.clientY);
  window.__lastDown = JSON.stringify(p);   // 调试
  var hits = hitsAt(p);
  // 拖动优先：已选中的片段在指针下 → 直接拖它（不再触发循环切换，
  // 之前点一下选中、再按下想拖时选中被切走，拖到了别的对象上）；
  // 否则取最上层的命中。被压住的片段靠「单击松手循环」逐层点选。
  var id = (window.__selId && hits.indexOf(window.__selId) >= 0)
           ? window.__selId : (hits[0] || '');
  window.__selId = id;
  bcall('clipSelected', id);
  if (!id) return;
  var c = clipById(id);
  // 快照 move 条目：拖动时让活动的平移条目整体跟手（否则视觉不跟：
  // 条目插值优先于基准位置，拖了像没拖）。松手时把增量报给 Qt 落库。
  drag = { id: id, sx: e.clientX, sy: e.clientY, x0: c.x, y0: c.y,
           px: p.x, py: p.y, moved: false,
           moves: c.moves && c.moves.length
                  ? c.moves.map(function (m) { return Object.assign({}, m); })
                  : null };
  e.preventDefault();
});
document.addEventListener('mousemove', function (e) {
  if (!drag) return;
  var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
  if (!drag.moved && Math.abs(dx) + Math.abs(dy) <= 4) return;
  drag.moved = true;
  var r = overlay.getBoundingClientRect();
  var k = glState.w / r.width;
  var ddx = dx * k, ddy = dy * k;
  var c = clipById(drag.id);
  if (!c) { drag = null; return; }
  c.x = Math.round(drag.x0 + ddx);
  c.y = Math.round(drag.y0 + ddy);
  if (drag.moves) {
    c.moves = drag.moves.map(function (m) {
      return Object.assign({}, m,
        { x0: m.x0 + ddx, y0: m.y0 + ddy, x1: m.x1 + ddx, y1: m.y1 + ddy });
    });
  }
  renderNow();  // 拖动期间 JS 自渲染，不回流 Qt（mouseup 才报）
});
document.addEventListener('mouseup', function () {
  if (!drag) return;
  var d = drag; drag = null;
  if (d.moved) {
    var c = clipById(d.id);
    if (c) {
      bcall('clipMoved', d.id, c.x, c.y,
            Math.round((c.x - d.x0) * 10) / 10,
            Math.round((c.y - d.y0) * 10) / 10);
    }
  } else {
    // 单击（未拖动）：在同一位置的堆叠命中里循环推进选择，
    // 下次点击即可选中下一层被压住的片段
    var hits = hitsAt({ x: d.px, y: d.py });
    var idx = hits.indexOf(window.__selId);
    if (hits.length > 1 && idx >= 0) {
      window.__selId = hits[(idx + 1) % hits.length];
      bcall('clipSelected', window.__selId);
    }
  }
});

// ---------------- 模型同步 ----------------
function reconcile() {
  // 删掉消失、类型/素材变化或图层跨越正负（换世界）的 actor
  for (var id in actors) {
    var c = clipById(id);
    var a = actors[id];
    if (!c || c.type !== a.clip.type ||
        (a.kind === 'spine' && c.asset !== a.clip.asset) ||
        ((c.layer < 0) !== (a.clip.layer < 0))) {
      if (a.el) a.el.remove();
      delete actors[id];
    } else {
      a.clip = c;  // 换引用，保留运行时状态
    }
  }
  // 新建（负图层 spine 用顶层世界的资源）
  for (var i = 0; i < model.clips.length; i++) {
    var clip = model.clips[i];
    if (!actors[clip.id]) {
      if (clip.type === 'spine') {
        ensureSkeletonData(clip.asset, model.spine[clip.asset],
                           clip.layer < 0);
      }
      actors[clip.id] = createActor(clip);
    }
  }
  // 覆盖层按 layer 重排：正图层进 #overlay（layer 小后 append=在上）；
  // 负图层进 #overlayTop（更少负的先 append，更多负的在后=更上）。
  // spine 加载占位也参与（它有 el）。
  var ovsPos = [], ovsNeg = [];
  for (id in actors) {
    if (actors[id].el) {
      (actors[id].clip.layer < 0 ? ovsNeg : ovsPos).push(actors[id]);
    }
  }
  ovsPos.sort(function (x, y) { return y.clip.layer - x.clip.layer; });
  ovsNeg.sort(function (x, y) { return x.clip.layer - y.clip.layer; });
  for (i = 0; i < ovsPos.length; i++) overlay.appendChild(ovsPos[i].el);
  for (i = 0; i < ovsNeg.length; i++) overlayTop.appendChild(ovsNeg[i].el);
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
      // 自创程序动作：eval 各模型的 proc 源码（注册 window.PROCS）
      window.PROCS = {};
      if (window.__clearFx) window.__clearFx();
      var procs = model.procs || {};
      for (var pm in procs) {
        for (var pn in procs[pm]) {
          try { (0, eval)('(function(){\n' + procs[pm][pn] + '\n})()'); }
          catch (e) { log('程序动作加载失败 ' + pm + '/' + pn + ': ' + e); }
        }
      }
      resizeStage();
      reconcile();
      setTimeInternal(Math.min(time, duration));
    } catch (e) { log('loadProject 失败: ' + e); }
  },
  setTime: function (t) {
    // 只改时间：播放中拉时间条不中断播放（暂停/停止由专门按钮控制）
    setTimeInternal(parseFloat(t) || 0, true);
  },
  // Qt 侧（时间轴/属性面板）选中变化 → 同步给点选循环
  selectClip: function (id) { window.__selId = id || null; },
  // 调试：舞台坐标点命中了哪些 spine（含几何数据）
  debugHit: function (x, y) {
    var p = { x: x, y: y };
    var out = [];
    for (var aid in actors) {
      var a = actors[aid];
      if (a.kind !== 'spine') continue;
      out.push({ id: aid, ready: a.ready, hit: a.ready ? hitSpine(a, p) : false,
                 boundsW: Math.round(a.boundsW), boundsH: Math.round(a.boundsH),
                 scale_eff: (0.5 * glState.h / a.boundsH) * (a.clip.scale || 1) });
    }
    out.push({ hitsAt: hitsAt(p) });
    return JSON.stringify(out);
  },
  // 调试：片段骨架当前渲染包围盒（世界坐标 y 向上）
  debugBounds: function (id) {
    renderNow();
    var a = actors[id];
    if (!a || !a.skeleton) return null;
    var off = new spine.Vector2(), size = new spine.Vector2();
    try { a.skeleton.getBounds(off, size, []); } catch (e) { return null; }
    return JSON.stringify({
      x: Math.round(off.x * 10) / 10, y: Math.round(off.y * 10) / 10,
      w: Math.round(size.x * 10) / 10, h: Math.round(size.y * 10) / 10,
      canvasH: glState.h, anchor: a.anchor,
    });
  },
  play: play,
  pause: pause,
  setExportMode: function (on) {
    exportMode = !!on;
    exportIdx = 0;
    capAcc = 0;
  },
  // 步进导出（Qt 握手驱动）：exportBegin 重置；exportNext 步进一帧并抓取，
  // Qt 收到 exportFrame 后再调 exportNext。时间=帧序/fps 确定性推进，
  // 抓帧快慢不影响帧数与时长——rAF 实时抽帧在重场景（多 SVG）下
  // rAF<fps 会欠帧，视频时长缩水（实测 5.5s→4.13s）。
  exportBegin: function () {
    pause();
    exportMode = true;
    exportIdx = 0;
    capAcc = 0;
    var fps = (model && model.canvas && model.canvas.fps) || 30;
    window.__exp = {
      fps: fps,
      total: Math.max(1, Math.round(duration * fps)),
      i: 0,
    };
  },
  exportNext: function () {
    var e = window.__exp;
    if (!e) return;
    if (e.i >= e.total) { bcall('timeUpdate', duration); return; }
    setTimeInternal(e.i / e.fps, true);
    e.i++;
    captureFrame();
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
      if (a.kind === 'ov') {
        var mv = evalMove(a.clip, time);   // move 后的有效变换
        it.ex = mv.x; it.ey = mv.y; it.erot = mv.rot;
      }
      if (a.kind === 'spine' && a.ready) {
        var tr = a.state.tracks[0];
        it.anim = tr && tr.animation ? tr.animation.name : null;
        it.proc = a.curAnim || null;   // 程序动作名（base 之上的叠加层）
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
