"""拖动可靠性测试：时间窗外的片段可点选拖动；move 条目跟手且增量落库。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--autoplay-policy=no-user-gesture-required --allow-file-access-from-files")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)

from core.assets import RelayLibrary
from core.workspace import AnimEntry, Clip, MoveEntry, WorkspaceStore
from ui.workspace_page import WorkspacePage

ROOT = WorkspaceStore().root


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


store = WorkspaceStore()
import shutil
shutil.rmtree(ROOT / "_dragtest", ignore_errors=True)
proj = store.create("_dragtest")
c = Clip(id="sp", type="spine", asset="可露希尔", start=2.0, end=5.0,
         x=640.0, y=600.0)
c.anims.append(AnimEntry(start=2.0, end=5.0, anim="Default", loop=True))
c.moves = [MoveEntry(start=2.0, end=5.0, x0=640, y0=600, x1=640, y1=600)]
proj.clips.append(c)
proj.duration = 5.0
store.save(proj)
store.set_last("_dragtest")
page = WorkspacePage(RelayLibrary())
page.resize(1400, 900)
page.show()
page.stage.bridge.sigLog.connect(lambda m: print("[stage]", m))

# 播放头在 0（片段区间 [2,5] 之外）
clip = page._project.clip("sp")
page._sync_now()
page.stage.set_time(0)

sels, moves = [], []
page.stage.bridge.sigClipSelected.connect(sels.append)
page.stage.bridge.sigClipMoved.connect(
    lambda i, x, y, raw: moves.append((i, x, y, json.loads(raw))))


def probe(cb):
    page.stage.page().runJavaScript("stageApi.probe()",
                                    lambda s: cb(json.loads(s or "{}")))


def ready(_p=None):
    def dispatch(_s):
        js = ("(function(){var stage=document.getElementById('stage');"
              "var r=document.getElementById('overlay').getBoundingClientRect();"
              "var c=document.getElementById('gl');"
              "function pt(sx,sy){return [r.left+sx/c.width*r.width,"
              "                           r.top+sy/c.height*r.height];}"
              "function ev(t,a){return new MouseEvent(t,{bubbles:true,cancelable:true,button:0,clientX:a[0],clientY:a[1]});}"
              "stage.dispatchEvent(ev('mousedown',pt(640,450)));"
              "document.dispatchEvent(ev('mousemove',pt(760,380)));"
              "document.dispatchEvent(ev('mouseup',pt(760,380)));"
              "return window.__lastDown;})()")
        page.stage.page().runJavaScript(js, lambda r: print("dispatch:", r))
    page.stage.page().runJavaScript("stageApi.viewInfo()", dispatch)
    QTimer.singleShot(1000, check)


def check():
    print("选中:", sels)
    print("拖动:", moves)
    if "sp" not in sels:
        fail("区间外点选失败（拖动第一关就没过）")
    if not moves:
        fail("拖动未产生 clipMoved")
    i, x, y, raw_moves = moves[0]
    if not (x > 700 and y < 570):
        fail(f"回写位置不对: x={x} y={y}，期望约 760,529")
    c = page._project.clip("sp")
    print("模型基准:", c.x, c.y, "move条目:",
          [(m.x0, m.y0, m.x1, m.y1) for m in c.moves])
    if c.moves and abs(c.moves[0].x0 - 760) > 25:
        fail(f"move 条目没跟手：x0={c.moves[0].x0}，期望约 760")
    if not c.moves or abs(raw_moves[0]["x0"] - c.moves[0].x0) > 1e-6:
        fail("最终 move 条目没有原样写回")
    print("区间外点选、最终位置与 move 条目原样落库")
    page._undo_shortcut.activated.emit()
    QTimer.singleShot(300, check_undo)


def check_undo():
    c = page._project.clip("sp")
    print("Ctrl+Z 后:", c.x, c.y,
          [(m.x0, m.y0, m.x1, m.y1) for m in c.moves])
    if abs(c.x - 640) > 1e-6 or abs(c.y - 600) > 1e-6:
        fail("撤销没有恢复拖动前的基准位置")
    if not c.moves or abs(c.moves[0].x0 - 640) > 1e-6:
        fail("撤销没有恢复拖动前的 move 条目")
    print("PASS：拖动原样落库 + Ctrl+Z 完整撤销")
    app.exit(0)


QTimer.singleShot(3000, lambda: probe(ready))
QTimer.singleShot(30000, lambda: fail("总超时"))
sys.exit(app.exec())
