"""后台打开工作区项目并自动播放（页面关闭即结束）。

用法：python tools/play_project.py [项目名]（缺省 = 上次打开的项目）
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
from core.workspace import WorkspaceStore
from ui.workspace_page import WorkspacePage

store = WorkspaceStore()
name = sys.argv[1] if len(sys.argv) > 1 else store.last()
proj = store.load(name) if name else None
if not proj:
    print(f"项目 {name!r} 不存在")
    sys.exit(2)

page = WorkspacePage(RelayLibrary())
page.resize(1500, 950)
page.show()
page.raise_()
page.activateWindow()
page.setWindowTitle(f"{proj.name} — PRTS 工作区")
page._project = proj
page._refresh_project_combo(select=proj.name)
page._select("")
page._sync_now()


def play():
    page.stage.play()


page.stage.bridge.sigReady.connect(lambda: QTimer.singleShot(400, play))
QTimer.singleShot(8000, play)          # 兜底：信号没来也开播
print(f"自动播放「{proj.name}」（{proj.duration}s）… 关闭页面即结束")
sys.exit(app.exec())
