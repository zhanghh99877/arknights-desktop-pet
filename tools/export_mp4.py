"""无头导出 MP4：Qt↔JS 步进握手逐帧抓取，JPEG 帧喂 ffmpeg。

用法：python tools/export_mp4.py 项目名 [输出.mp4]
缺省输出到 exports/<项目名>.mp4。与 UI 导出（workspace_page._on_export）
同一握手协议：exportBegin 重置 → exportNext 抓一帧 → 收到 exportFrame
再回一脚，帧数由 时间×fps 精确决定，不受抓帧快慢影响。
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--autoplay-policy=no-user-gesture-required --allow-file-access-from-files"
    " --disable-background-timer-throttling --disable-renderer-backgrounding"
    " --disable-backgrounding-occluded-windows")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)

from core.assets import RelayLibrary
from core.workspace import WorkspaceStore, WorkspaceStore as _WS  # noqa: F401
from core.workspace_exporter import VideoExporter
from ui.workspace_page import WorkspacePage

PROJ = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "exports", f"{PROJ}.mp4")

store = WorkspaceStore()
proj = store.load(PROJ)
if not proj:
    print(f"项目 {PROJ!r} 不存在")
    sys.exit(2)
FPS = int(proj.canvas.get("fps", 30))
EXPECTED = max(1, int(round(float(proj.duration) * FPS)))

page = WorkspacePage(RelayLibrary())
page.resize(1500, 950)
page.show()
page._project = proj
page._refresh_project_combo(select=PROJ)
page._select("")
page._sync_now()

exporter: VideoExporter | None = None
state = {"started": False}


def start_export():
    global exporter
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    exporter = VideoExporter(OUT, FPS, EXPECTED)
    print(f"导出 {PROJ} → {OUT}（{EXPECTED} 帧 @ {FPS}fps）")
    state["started"] = True
    page.stage.page().runJavaScript("stageApi.exportBegin(); stageApi.exportNext();")


def on_frame(b64: str, _index: int):
    ex = exporter
    if ex is None or not state["started"]:
        return
    if not ex.write_png_base64(b64):
        print(f"写帧失败：{ex.error}", file=sys.stderr)
        QTimer.singleShot(200, finish_fail)
        return
    if ex.frames % 150 == 0 or ex.done:
        print(f"  {ex.frames}/{EXPECTED} 帧")
    if ex.done:
        QTimer.singleShot(300, finish_ok)
    else:
        page.stage.page().runJavaScript("stageApi.exportNext();")


def finish_ok():
    ok, err = exporter.finish()
    page.stage.set_export_mode(False)
    print(f"完成：{OUT}" if ok else f"ffmpeg 失败：{err}", file=sys.stderr
          if not ok else sys.stdout)
    app.exit(0 if ok else 1)


def finish_fail():
    exporter.cancel()
    app.exit(1)


page.stage.bridge.sigExportFrame.connect(on_frame)


def wait_ready():
    def check():
        js = "stageApi.probe()"
        page.stage.page().runJavaScript(js, lambda s: kick(__import__("json").loads(s or "{}")))

    def kick(snap):
        if not state["started"]:
            actors = snap.get("actors", [])
            spine = [a for a in actors if a.get("kind") == "spine"]
            if spine and all(a.get("ready") for a in spine):
                QTimer.singleShot(500, start_export)
                return
            QTimer.singleShot(600, check)

    QTimer.singleShot(3500, check)


QTimer.singleShot(1800000, lambda: (print("超时"), app.exit(3)))
wait_ready()
rc = app.exec()
if exporter and not exporter.done and rc == 0:
    rc = 1
sys.exit(rc)
