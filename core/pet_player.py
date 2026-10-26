"""看板渲染容器：Spine 骨架实时渲染（spine-player 3.8，Spine/vendor/）。

交互走 JS + QWebChannel（petBridge）：Chromium 渲染层会吞掉部分
系统级鼠标事件，Qt 侧事件过滤器不可靠；JS 监听器两种输入都能收到。

JS 桥事件：单击 / 双击 / 拖动开始 / 拖动位移 / 拖动结束 / 滚轮 / 动画播完。
页面还暴露 window._petMask()：把 WebGL 画面降采样成 45x45 alpha 位图，
供 Qt 侧做逐像素点击穿透（依赖 vendor 补丁 preserveDrawingBuffer）。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.assets import PRTS_ROOT

VENDOR = PRTS_ROOT / "Spine" / "vendor" / "spine-player"

# 切换动作时的交叉淡化时长（秒），0 = 硬切
_MIX_SECONDS = 0.2

# 自创程序动作运行时（Spine/proc/<模型>/*.js 注册 window.PROCS[name]）。
# 只在使用 procs 加载页面时注入。
_PROCS_RUNTIME_JS = """
<script>
/* 自创程序动作运行时：官方 apply() 之后叠加姿势（见 _PROC_HOOK_JS）。
 * 动作文件契约：window.PROCS[动作名] = {base: 打底官方动作, pose(sk, t, fx)}；
 * pose 每帧被调（t 秒，从切换起算），fx(id, bone, dxPx, dyPx, opacity, emoji)
 * 把 emoji 贴到骨骼屏幕位置。 */
window.PROCS = window.PROCS || {};
window.__procName = null;
window.__procT = 0;
window.__procDt = 1 / 60;
window.__fxIds = [];

/* 切换程序动作；name 为空 = 关闭程序层（保留当前官方动作）。
 * 切换时 setToSetupPose：官方动画每帧会重写带关键帧的骨骼，复位到
 * setup 姿势只清掉程序层留在无关键帧骨骼上的残留（如 scaleY 压扁）。 */
window.setProc = function(name, loop) {
  name = name || null;
  loop = loop !== false;
  if (name === window.__procName) return;
  window.__procName = name;
  window.__procT = 0;
  window.__clearFx();
  var p = window.player;
  if (!p || !p.loaded) return;
  try { p.skeleton.setToSetupPose(); } catch (e) {}
  if (!name) return;
  var def = window.PROCS[name];
  if (def && def.base) {
    try {
      if (p.skeleton.data.findAnimation(def.base))
        p.animationState.setAnimation(0, def.base, loop);
    } catch (e) {}
  }
};

/* 特效叠加层：骨世界坐标 + 像素偏移 → 屏幕定位（与取景框同一映射），
 * opacity<=0 隐藏。元素挂在 #player（position:relative）内。 */
window.procFx = function(id, bone, dxPx, dyPx, opacity, emoji) {
  var el = document.getElementById(id);
  if (opacity <= 0) { if (el) el.style.display = 'none'; return; }
  var p = window.player;
  if (!p || !p.currentViewport || !bone) return;
  if (!el) {
    el = document.createElement('div');
    el.id = id;
    el.style.cssText = 'position:absolute;font-size:26px;pointer-events:none;display:none;z-index:5;';
    var host = document.getElementById('player') || document.body;
    host.appendChild(el);
    window.__fxIds.push(id);
  }
  var vp = p.currentViewport, host = el.parentElement;
  var W = host.clientWidth, H = host.clientHeight;
  if (!W || !H) return;
  el.textContent = emoji;
  el.style.left = ((bone.worldX - vp.x) / vp.width * W + dxPx) + 'px';
  el.style.top = (H - (bone.worldY - vp.y) / vp.height * H + dyPx) + 'px';
  el.style.opacity = opacity;
  el.style.display = 'block';
};

window.__clearFx = function() {
  (window.__fxIds || []).forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  });
  window.__fxIds = [];
};
</script>"""

# success 钩子：monkey-patch apply，官方姿势算完后叠加程序层。
# 单独占位注入（procs 为空时页面完全不受影响）。
_PROC_HOOK_JS = """
        // 程序动作钩子：apply() 之后叠加自创姿势
        var _origApply = player.animationState.apply.bind(player.animationState);
        player.animationState.apply = function(sk) {
          _origApply(sk);
          var name = window.__procName;
          if (name && window.PROCS && window.PROCS[name]) {
            window.__procT += window.__procDt || 1 / 60;
            try { window.PROCS[name].pose(sk, window.__procT, window.procFx); } catch (e) {}
          }
        };"""

# 交互桥：JS 鼠标/动画事件 → Qt 信号
_BRIDGE_JS = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
  new QWebChannel(qt.webChannelTransport, ch => {
    window.bridge = ch.objects.petBridge;
  });
  let _pd = null, _moved = false, _clickTimer = null;
  document.addEventListener('mousedown', e => {
    if (e.button === 0) { _pd = [e.screenX, e.screenY]; _moved = false; }
  });
  document.addEventListener('mousemove', e => {
    if (!_pd) return;
    const dx = e.screenX - _pd[0], dy = e.screenY - _pd[1];
    if (_moved || Math.abs(dx) + Math.abs(dy) > 8) {
      if (!_moved && window.bridge) window.bridge.dragStart();
      _moved = true;
      if (window.bridge) window.bridge.dragBy(dx, dy);
      _pd = [e.screenX, e.screenY];
    }
  });
  document.addEventListener('mouseup', e => {
    if (e.button !== 0 || !_pd) return;
    _pd = null;
    if (_moved) {
      if (window.bridge) window.bridge.dragEnd();
      return;
    }
    // 单击/双击消歧：260ms 内没有第二击才算单击
    if (_clickTimer) {
      clearTimeout(_clickTimer);
      _clickTimer = null;
      if (window.bridge) window.bridge.doubleClicked();
    } else {
      _clickTimer = setTimeout(() => {
        _clickTimer = null;
        if (window.bridge) window.bridge.clicked();
      }, 260);
    }
  });
  document.addEventListener('wheel', e => {
    if (window.bridge) window.bridge.wheeled(Math.trunc(e.deltaY));
  }, {passive: true});
</script>"""

# 点击穿透位图：把 WebGL 画面缩到 45x45 读 alpha，
# 返回 "l,t,r,b;45x45位图(0/1)"（与 Qt 侧 _apply_hit_rect 约定一致）
_MASK_JS = """
<script>
  window._petMask = function() {
    try {
      const c = document.querySelector('canvas');
      if (!c || !window.player || !window.player.loaded) return null;
      const S = 45;
      if (!window._mc) {
        window._mc = document.createElement('canvas');
        window._mc.width = S; window._mc.height = S;
        window._mg = window._mc.getContext('2d', {willReadFrequently: true});
      }
      const g = window._mg;
      g.clearRect(0, 0, S, S);
      g.drawImage(c, 0, 0, S, S);
      const d = g.getImageData(0, 0, S, S).data;
      let x0 = S, y0 = S, x1 = -1, y1 = -1, bits = '';
      for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
        const opaque = d[(y * S + x) * 4 + 3] > 16;
        bits += opaque ? '1' : '0';
        if (opaque) {
          if (x < x0) x0 = x; if (x > x1) x1 = x;
          if (y < y0) y0 = y; if (y > y1) y1 = y;
        }
      }
      if (x1 < 0) return null;
      return [x0 / S, y0 / S, (x1 + 1) / S, (y1 + 1) / S].join(',') + ';' + bits;
    } catch (e) { return null; }
  };
</script>"""

_SPINE_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="{vendor}/spine-player.css">
  <style>
    html, body {{ margin: 0; padding: 0; background: {bg}; overflow: hidden; }}
    #player {{ width: 100vw; height: 100vh; position: relative; }}
    .spine-player {{ background: transparent !important; }}
  </style>
</head>
<body>
  <div id="player"></div>
  <script src="{vendor}/spine-core.js"></script>
  <script src="{vendor}/spine-webgl.js"></script>
  <script src="{vendor}/spine-player.js"></script>
  <script>
    window.player = new spine.SpinePlayer(document.getElementById('player'), {{
      skelUrl: '{skel}',
      atlasUrl: '{atlas}',
      // 取景框只在加载时按 fit 动作（常态动作）算一次，之后永不重算：
      // 若按 Start 这类大范围动作取景，主模型会被压缩显示
      animation: '{fit}',
      alpha: true,
      backgroundColor: '#00000000',
      showControls: false,
      success: function (player) {{
        // 动作切换交叉淡化，避免硬切
        player.animationState.data.defaultMix = {mix};
        // 非循环动画播完 → 通知 Qt 切回默认
        player.animationState.addListener({{ complete: function (entry) {{
          if (entry.loop || !window.bridge) return;
          var reported = entry.animation.name;
          var procName = window.__procName;
          if (procName && window.PROCS[procName] &&
              window.PROCS[procName].base === reported)
            reported = procName;
          window.bridge.animComplete(reported);
        }} }});
        // 取景框 = 全部已配置动作包围盒的并集（封顶 fit 动作的 5 倍），
        // 之后切换动作不再重算：模型大小恒定，大动作也播得下。
        // 计算结果由 Qt 侧缓存：有缓存直接套用，跳过采样
        var uvp = {cached_vp};
        var names = {fit_all};
        if (!uvp && names.length && player.currentViewport) {{
          var fv = player.calculateAnimationViewport('{fit}');
          var cx = fv.x + fv.width / 2, cy = fv.y + fv.height / 2;
          var maxW = fv.width * 5, maxH = fv.height * 5;
          var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
          names.push('{fit}');
          for (var i = 0; i < names.length; i++) {{
            try {{
              var av = player.calculateAnimationViewport(names[i]);
              x0 = Math.min(x0, av.x); y0 = Math.min(y0, av.y);
              x1 = Math.max(x1, av.x + av.width); y1 = Math.max(y1, av.y + av.height);
            }} catch (e) {{}}
          }}
          x0 = Math.max(x0, cx - maxW / 2); x1 = Math.min(x1, cx + maxW / 2);
          y0 = Math.max(y0, cy - maxH / 2); y1 = Math.min(y1, cy + maxH / 2);
          uvp = {{ x: x0, y: y0, width: x1 - x0, height: y1 - y0,
                  padLeft: '10%', padRight: '10%',
                  padTop: '10%', padBottom: '10%' }};
          uvp.padLeft = player.percentageToWorldUnit(uvp.width, uvp.padLeft);
          uvp.padRight = player.percentageToWorldUnit(uvp.width, uvp.padRight);
          uvp.padTop = player.percentageToWorldUnit(uvp.height, uvp.padTop);
          uvp.padBottom = player.percentageToWorldUnit(uvp.height, uvp.padBottom);
          if (window.bridge) window.bridge.cacheViewport(JSON.stringify(uvp));
        }}
        if (uvp) {{
          player.currentViewport = uvp;
          player.previousViewport = uvp;  // 不要初始过渡动画
          player.viewportTransitionStart = 0;
        }}
        // 首个动作（如启动）必须最后设置：
        // calculateAnimationViewport 内部会 clearTracks()，先设会被并集计算清掉
        var anim = '{animation}';
        var procAnim = {proc_animation};
        if (procAnim) window.setProc(procAnim, {loop});
        else if (anim) player.animationState.setAnimation(0, anim, {loop});
        // 显示缩放：view_scale=0.5 → 取景框以中心放大一倍，动画显示为一半
        var vs = {view_scale};
        if (vs > 0 && vs !== 1 && player.currentViewport) {{
          var vp = player.currentViewport, k = 1 / vs;
          vp.x -= vp.width * (k - 1) / 2;
          vp.y -= vp.height * (k - 1) / 2;
          vp.width *= k;
          vp.height *= k;
        }}
        {proc_hook}
      }},
    }});
  </script>
  {proc_scripts}
  {mask}
  {bridge}
</body>
</html>"""


def _build_proc_scripts(procs: dict | None) -> str:
    """程序动作注入块：运行时 + 每个动作一个 <script>（源码原样内联）。

    源码里可能出现的 </script> 转义为 <\\/script，防止提前闭合标签。
    """
    if not procs:
        return ""
    blocks = [_PROCS_RUNTIME_JS]
    for name, src in procs.items():
        src = src.replace("</script", "<\\/script")
        blocks.append(f"<script>\n/* proc: {name} */\n{src}\n</script>")
    return "\n".join(blocks)


class PetBridge(QObject):
    """JS → Qt 交互桥。JS 调 clicked / doubleClicked / dragStart /
    dragBy / dragEnd / wheeled / animComplete。"""

    petClicked = Signal()
    petDoubleClicked = Signal()
    dragStarted = Signal()
    dragDelta = Signal(int, int)
    dragEnded = Signal()
    wheelDelta = Signal(int)      # 滚轮 deltaY：负值向上滚（放大），正值向下滚（缩小）
    animCompleted = Signal(str)   # 非循环动画播完（动画名）
    viewportComputed = Signal(str)  # 并集取景框算出来了（JSON），Qt 侧缓存用

    @Slot()
    def clicked(self):
        self.petClicked.emit()

    @Slot()
    def doubleClicked(self):
        self.petDoubleClicked.emit()

    @Slot()
    def dragStart(self):
        self.dragStarted.emit()

    @Slot(int, int)
    def dragBy(self, dx: int, dy: int):
        self.dragDelta.emit(dx, dy)

    @Slot()
    def dragEnd(self):
        self.dragEnded.emit()

    @Slot(int)
    def wheeled(self, dy: int):
        self.wheelDelta.emit(dy)

    @Slot(str)
    def animComplete(self, name: str):
        self.animCompleted.emit(name)

    @Slot(str)
    def cacheViewport(self, vp_json: str):
        self.viewportComputed.emit(vp_json)


class PetPlayer(QWebEngineView):
    """看板渲染器：加载 spine 骨架并播放动作。

    background: "transparent" 表示穿透到底层窗口（悬浮窗用），
    也可传 CSS 颜色（内嵌展示区用，如 "#ffffff"）。
    bridge: JS 交互桥（见 PetBridge 信号）。
    """

    def __init__(self, background: str = "transparent", parent=None):
        super().__init__(parent)
        self._background = background
        self.settings().setAttribute(
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False
        )
        if background == "transparent":
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.bridge = PetBridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("petBridge", self.bridge)
        self.page().setWebChannel(self._channel)

    def _set_bg(self):
        self.page().setBackgroundColor(
            QColor(0, 0, 0, 0) if self._background == "transparent"
            else QColor(self._background)
        )

    def play_spine(self, skel: Path, atlas: Path, animation: str = "",
                   loop: bool = True, fit: str = "", view_scale: float = 1.0,
                   fit_all: list = (), viewport: dict | None = None,
                   procs: dict | None = None):
        """整套加载 spine 骨架（切模型时用）。

        animation 为首个播放的骨架内动画名；传入了 procs 且 animation
        是程序动作名时，会先进入其 base 官方动作再叠加程序层。
        fit 为取景参照动作（取景框只在加载时计算一次，之后切换动作不再
        重算，保证模型显示大小恒定），必须是官方动画名。
        fit_all：参与取景并集的全部动作名（缺省只有 fit）。
        并集尺寸封顶为 fit 包围盒的 5 倍，防止离谱动作把主体缩太小。
        viewport：缓存的并集取景框（由 viewportComputed 信号回传后落库），
        传入则跳过采样直接套用。
        view_scale 为显示缩放：0.5 = 动画显示为取景框的一半大小（预览用）。
        procs：自创程序动作 {动作名: JS 源码}（Spine/proc/<模型>/ 下的
        .js 文件内容），注入后可用 set_proc() 在官方动作之上叠加播放。
        """
        import json
        initial_proc = animation if procs and animation in procs else ""
        initial_anim = "" if initial_proc else animation
        self._set_bg()
        self.setHtml(
            _SPINE_HTML.format(
                vendor=VENDOR.as_uri(), bg=self._background,
                skel=skel.as_uri(), atlas=atlas.as_uri(),
                animation=initial_anim,
                proc_animation=json.dumps(initial_proc),
                fit=fit or initial_anim,
                loop='true' if loop else 'false',
                view_scale=view_scale,
                fit_all=json.dumps(list(fit_all)),
                cached_vp=json.dumps(viewport) if viewport else 'null',
                mix=_MIX_SECONDS, mask=_MASK_JS, bridge=_BRIDGE_JS,
                proc_scripts=_build_proc_scripts(procs),
                proc_hook=_PROC_HOOK_JS if procs else ""),
            QUrl.fromLocalFile(str(PRTS_ROOT) + "/"),
        )

    def set_animation(self, animation: str, loop: bool = True):
        """同骨架内切换动作（不重载页面、不重算取景框，交叉淡化）。

        先关程序动作层：回官方动作时自动清掉叠加姿势与特效。
        """
        safe = animation.replace("'", "\\'")
        self.page().runJavaScript(
            f"window.setProc && window.setProc(null);"
            f"window.player && window.player.animationState"
            f".setAnimation(0, '{safe}', {'true' if loop else 'false'});"
        )

    def set_proc(self, name: str, loop: bool = True):
        """切换到自创程序动作（页面需带 procs 加载）；空名关闭程序层。"""
        safe = name.replace("\\", "\\\\").replace("'", "\\'")
        self.page().runJavaScript(
            f"window.setProc && window.setProc('{safe}', "
            f"{'true' if loop else 'false'});"
        )

    def render_pose(self, animation: str = "", proc: str = "", t: float = 0.0,
                    fps: int = 25, callback=None):
        """确定性渲染一帧：暂停实时循环，把官方/程序动作推到 t 秒后重绘。"""
        import json
        anim_json = json.dumps(animation or "")
        proc_json = json.dumps(proc or "")
        dt = 1.0 / max(1, int(fps))
        js = f"""
        (function() {{
          var p = window.player;
          if (!p || !p.loaded) return false;
          p.pause();
          window.__procDt = {dt};
          if ({proc_json}) {{
            window.__procName = null;
            window.setProc({proc_json}, false);
            p.animationState.update({float(t)});
            window.__procT = {float(t)};
          }} else {{
            window.setProc && window.setProc(null);
            p.animationState.clearTracks();
            p.skeleton.setToSetupPose();
            p.animationState.setAnimation(0, {anim_json}, false);
            p.animationState.update({float(t)});
          }}
          p.animationState.apply(p.skeleton);
          p.skeleton.updateWorldTransform();
          p.drawFrame(false);
          return true;
        }})()
        """
        self.page().runJavaScript(js, callback)

    def grab_canvas_png(self, callback):
        """从页面 WebGL 画布抓当前帧 PNG（dataURL 字符串回传）。

        QWebEngineView.grab() 抓 WebGL 内容不可靠（常出空白/残影），
        必须在页面内 drawImage 读回（vendor 补丁 preserveDrawingBuffer）。
        """
        js = """
        (function() {
          var host = document.getElementById('player');
          var c = host ? host.querySelector('canvas') : document.querySelector('canvas');
          if (!c || !window.player || !window.player.loaded) return null;
          var off = document.createElement('canvas');
          off.width = c.width; off.height = c.height;
          var ctx = off.getContext('2d');
          ctx.drawImage(c, 0, 0);
          try { return off.toDataURL('image/png'); }
          catch (e) { return null; }
        })()
        """
        self.page().runJavaScript(js, callback)
        self.page().runJavaScript(js, callback)

    def stop(self):
        self.setHtml("<html><body style='background:transparent'></body></html>")
