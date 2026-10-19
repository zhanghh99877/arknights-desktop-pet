"""旋转修复验证：debugBounds 直接量骨架包围盒。

rot=0：脚底（包围盒底边中点）必须落在 (px, py)。
rot=90：宽高应互换，且包围盒左下角贴着脚底（绕脚底转）。
"""
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
from core.workspace import WorkspaceStore
from ui.workspace_page import WorkspacePage

ROOT = WorkspaceStore().root
PX, PY = 640.0, 600.0


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


store = WorkspaceStore()
proj = store.load("_diag")   # 复用上个诊断项目（可露希尔 sp 片段在 640,600）
if proj is None:
    fail("先跑诊断项目 _diag")
page = WorkspacePage(RelayLibrary())
page.resize(1400, 900)
page.show()
page.stage.bridge.sigLog.connect(lambda m: print("[stage]", m))

results = {}


def bounds(cb):
    page.stage.page().runJavaScript(
        "stageApi.debugBounds('sp')", lambda s: cb(json.loads(s or "null")))


def step(rot):
    for cl in page._project.clips:
        cl.x, cl.y = PX, PY
        cl.rotation = float(rot)
    page._sync_now()
    QTimer.singleShot(600, lambda: bounds(lambda b: got(rot, b)))


def got(rot, b):
    if not b:
        fail("debugBounds 返回空")
    foot_world_y = b["canvasH"] - PY          # 120
    results[rot] = b
    inside = (b["x"] - 10 <= PX <= b["x"] + b["w"] + 10 and
              b["y"] - 10 <= foot_world_y <= b["y"] + b["h"] + 10)
    print(f"rot={rot}: bounds x={b['x']} y={b['y']} w={b['w']} h={b['h']}"
          f" | 目标点(640,120)在包围盒内: {inside}")
    if not inside:
        fail(f"rot={rot} 目标点不在角色包围盒内：角色跑偏了")
    if rot == 0:
        print("rot=0 根骨骼定位 ✓")
        QTimer.singleShot(300, lambda: step(90.0))
    else:
        b0 = results[0.0]
        if not (0.7 * b0["h"] <= b["w"] <= 1.4 * b0["h"] and
                0.7 * b0["w"] <= b["h"] <= 1.4 * b0["w"]):
            fail(f"rot=90 宽高未互换：rot0 {b0['w']}x{b0['h']} vs rot90 {b['w']}x{b['h']}")
        print("rot=90 绕根骨骼旋转 ✓（宽高互换，锚点不动）")
        print("PASS")
        app.exit(0)


QTimer.singleShot(3000, lambda: step(0.0))
QTimer.singleShot(30000, lambda: fail("总超时"))
sys.exit(app.exec())
