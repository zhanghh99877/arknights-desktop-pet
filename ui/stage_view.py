"""工作区舞台视图：QWebEngineView 包装 html/stage.html 渲染引擎。

单一数据流：Qt 持有文档模型，任何编辑 → sync_project() 全量推给 JS
（stageApi.loadProject）；JS 只经 stageBridge 回报交互事件
（stageReady/log/clipSelected/clipMoved/timeUpdate/exportFrame）。
素材拖放在 Qt 侧接收（dragEnter/drop），坐标换算走 JS 的 viewInfo()。
"""

from __future__ import annotations

import json

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.assets import PRTS_ROOT, RelayLibrary

VENDOR = (PRTS_ROOT / "Spine" / "vendor" / "spine-player").as_uri()
STAGE_HTML = PRTS_ROOT / "html" / "stage.html"

MIME_ASSET = "application/x-prts-asset"

_BRIDGE_JS = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
window.bridge = null;
new QWebChannel(qt.webChannelTransport, function (ch) {
  window.bridge = ch.objects.stageBridge;
});
</script>
"""


def spine_lib(library: RelayLibrary, clips: list[dict]) -> dict:
    """项目里用到的 spine 模型 → {模型名: {skel, atlas}}（file URI）。

    公用素材：直接从 Spine/ 库引用，不复制进项目。
    """
    out = {}
    for c in clips:
        if c.get("type") != "spine":
            continue
        name = c.get("asset", "")
        if name in out:
            continue
        info = library.spine_info(name)
        if info:
            out[name] = {"skel": info["skel"].as_uri(),
                         "atlas": info["atlas"].as_uri()}
    return out


class StageBridge(QObject):
    """JS → Qt 事件桥（stageBridge）。"""

    sigReady = Signal()
    sigLog = Signal(str)
    sigClipSelected = Signal(str)          # '' = 点了空白
    sigClipMoved = Signal(str, float, float)
    sigTime = Signal(float)
    sigExportFrame = Signal(str, int)      # PNG base64、帧序号

    @Slot()
    def stageReady(self):
        self.sigReady.emit()

    @Slot(str)
    def log(self, msg: str):
        self.sigLog.emit(msg)

    @Slot(str)
    def clipSelected(self, clip_id: str):
        self.sigClipSelected.emit(clip_id)

    @Slot(str, float, float)
    def clipMoved(self, clip_id: str, x: float, y: float):
        self.sigClipMoved.emit(clip_id, x, y)

    @Slot(float)
    def timeUpdate(self, t: float):
        self.sigTime.emit(t)

    @Slot(str, int)
    def exportFrame(self, b64: str, index: int):
        self.sigExportFrame.emit(b64, index)


class StageView(QWebEngineView):
    """舞台：加载 stage.html，同步项目模型，回报交互。"""

    assetDropped = Signal(str, str, float, float)  # kind, name, x, y（舞台坐标）
    pageLoaded = Signal()                          # loadFinished(ok=True)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bridge = StageBridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("stageBridge", self.bridge)
        self.page().setWebChannel(self._channel)
        self.setAcceptDrops(True)
        self.loadFinished.connect(
            lambda ok: ok and self.pageLoaded.emit())
        self._load_page()

    def _load_page(self):
        # 不用 str.format：模板里 CSS 大括号多，replace 令牌更安全
        html = STAGE_HTML.read_text(encoding="utf-8")
        html = html.replace("{vendor}", VENDOR)
        html = html.replace("{bridge_js}", _BRIDGE_JS)
        self.setHtml(html, QUrl.fromLocalFile(str(PRTS_ROOT) + "/"))

    # ---- Qt → JS ----
    def _js(self, code: str):
        self.page().runJavaScript(code)

    def sync_project(self, project: dict, library: RelayLibrary,
                     assets_base: str):
        """全量同步文档模型（canvas/duration/layers/clips/spine/assets）。"""
        payload = {
            "canvas": project["canvas"],
            "duration": project["duration"],
            "layers": project["layers"],
            "clips": project["clips"],
            "spine": spine_lib(library, project["clips"]),
            "assets": assets_base,
        }
        js = "stageApi.loadProject(" + json.dumps(payload, ensure_ascii=False) + ")"
        self._js(js)

    def set_time(self, t: float):
        self._js(f"stageApi.setTime({float(t)})")

    def play(self):
        self._js("stageApi.play()")

    def pause(self):
        self._js("stageApi.pause()")

    def set_export_mode(self, on: bool):
        self._js(f"stageApi.setExportMode({'true' if on else 'false'})")

    # ---- 拖放 ----
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_ASSET):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_ASSET):
            e.acceptProposedAction()

    def dropEvent(self, e):
        raw = bytes(e.mimeData().data(MIME_ASSET)).decode("utf-8", "replace")
        try:
            info = json.loads(raw)
        except ValueError:
            return
        pos = e.position()

        def on_view(view_json):
            try:
                v = json.loads(view_json or "{}")
            except ValueError:
                return
            scale = v.get("scale") or 1
            x = (pos.x() - v.get("left", 0)) * scale
            y = (pos.y() - v.get("top", 0)) * scale
            if 0 <= x and 0 <= y:
                self.assetDropped.emit(info.get("kind", ""),
                                       info.get("name", ""), x, y)

        self.page().runJavaScript("stageApi.viewInfo()", on_view)
