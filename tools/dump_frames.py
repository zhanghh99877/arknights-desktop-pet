"""把项目在指定时刻的画面导出成 JPEG，供版式自查。

用法：python tools/dump_frames.py 项目名 输出目录 t1 t2 ...
原理：exportBegin 后把 __exp.i 钳到 帧序=t*fps，exportNext 即在目标时刻
确定性抓帧（走 captureFrame 的完整合成链，与导出一致）。
"""
import base64
import json
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
from core.workspace import WorkspaceStore
from ui.workspace_page import WorkspacePage

PROJ = sys.argv[1]
OUT = sys.argv[2]
TIMES = [float(x) for x in sys.argv[3:]]
FPS = 30

page = WorkspacePage(RelayLibrary())
page.resize(1500, 950)
page.show()

store = WorkspaceStore()
proj = store.load(PROJ)
if not proj:
    print(f"项目 {PROJ} 不存在")
    sys.exit(2)
page._project = proj
page._refresh_project_combo(select=PROJ)
page._select("")
page._sync_now()

os.makedirs(OUT, exist_ok=True)
got = set()


def on_frame(b64: str, index: int):
    # exportIdx 是抓帧次序（0,1,2...），按调用顺序对应 TIMES
    if index < len(TIMES) and index not in got:
        got.add(index)
        t = TIMES[index]
        with open(os.path.join(OUT, f"t{t:05.2f}.jpg"), "wb") as f:
            f.write(base64.b64decode(b64.split(",", 1)[-1]))
        print(f"帧 {index} (t={t:.2f}s) 已保存")


page.stage.bridge.sigExportFrame.connect(on_frame)


def dump_all():
    """握手式逐帧：等上一帧回传（事件循环转起来）再抓下一帧。

    连发 exportNext 会在前一帧 SVG 异步合成未完成时改写画布，
    合成结果闹鬼——必须像真实导出那样逐帧握手。exportBegin 会把
    exportIdx 清零，所以帧序自计数。
    """
    state = {"i": 0}

    def on_frame(b64: str, _index: int):
        i = state["i"]
        if i < len(TIMES) and i not in got:
            got.add(i)
            t = TIMES[i]
            with open(os.path.join(OUT, f"t{t:05.2f}.jpg"), "wb") as f:
                f.write(base64.b64decode(b64.split(",", 1)[-1]))
            print(f"帧 {i} (t={t:.2f}s) 已保存")
        state["i"] += 1
        if state["i"] >= len(TIMES):
            QTimer.singleShot(600, finish)
            return
        t = TIMES[state["i"]]
        js = (f"(function(){{stageApi.exportBegin();"
              f"window.__exp.i={round(t * FPS)};"
              f"stageApi.exportNext();}})()")
        page.stage.page().runJavaScript(js)

    page.stage.bridge.sigExportFrame.connect(on_frame)
    js = (f"(function(){{stageApi.exportBegin();"
          f"window.__exp.i={round(TIMES[0] * FPS)};"
          f"stageApi.exportNext();}})()")
    page.stage.page().runJavaScript(js)


def wait_ready():
    def check():
        js = "stageApi.probe()"
        page.stage.page().runJavaScript(js, lambda s: kick(json.loads(s or "{}")))

    def kick(snap):
        actors = snap.get("actors", [])
        spine = [a for a in actors if a.get("kind") == "spine"]
        if spine and all(a.get("ready") for a in spine):
            print("骨架就绪，开始抓帧")
            dump_all()
            QTimer.singleShot(1500 + len(TIMES) * 400, finish)
        else:
            QTimer.singleShot(600, check)

    QTimer.singleShot(3500, check)


def finish():
    print(f"完成 {len(got)}/{len(TIMES)} 帧 → {OUT}")
    app.exit(0)


QTimer.singleShot(120000, lambda: (print("超时"), app.exit(3)))
wait_ready()
sys.exit(app.exec())
