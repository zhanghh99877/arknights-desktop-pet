"""时间轴拖动 + 项目切换实证（QTest 真实事件，普通 QWidget 可达）。

① 时间轴片段左右拖（move）→ 模型 start 变化
② 空区域左右拖 → 横向平移视图（pan）
③ 项目下拉切换 → page._project 变化且舞台同步
"""
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--autoplay-policy=no-user-gesture-required --allow-file-access-from-files")

from PySide6.QtCore import QPoint, QPointF, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)

from core.assets import RelayLibrary
from core.workspace import AnimEntry, Clip, WorkspaceStore
from ui.workspace_page import WorkspacePage

ROOT = WorkspaceStore().root


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


store = WorkspaceStore()
# 两个项目：A（默认项目位置 640,600）/ B（380,400），内容可区分
for name, x, y in (("_loadA", 640.0, 600.0), ("_loadB", 380.0, 400.0)):
    shutil.rmtree(ROOT / name, ignore_errors=True)
    p = store.create(name)
    c = Clip(id="sp", type="spine", asset="可露希尔", start=0.0, end=3.0, x=x, y=y)
    c.anims.append(AnimEntry(start=0, end=3, anim="Default", loop=True))
    p.clips.append(c)
    p.duration = 3.0
    store.save(p)
store.set_last("_loadA")

page = WorkspacePage(RelayLibrary())
page.resize(1400, 950)
page.show()
page.raise_()
page.activateWindow()

tl = page.timeline


def clip_widget_rect():
    """片段块（_loadA 的 sp 0~3s 图层0）在时间轴控件上的矩形。"""
    c = page._project.clip("sp")
    x0 = tl._x(c.start) + 20
    y0 = tl._row_tops[0] + 8
    return QPointF(x0, y0)


def _qp(pt):
    return QPoint(int(pt.x()), int(pt.y()))


def t1_drag_clip():
    r = clip_widget_rect()
    before = page._project.clip("sp").start
    QTest.mouseMove(tl, _qp(r))
    QTest.mousePress(tl, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier, _qp(r))
    QTest.mouseMove(tl, _qp(QPointF(r.x() + 80, r.y())))
    QTest.mouseRelease(tl, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier,
                       _qp(QPointF(r.x() + 80, r.y())))
    QTimer.singleShot(400, lambda: check1(before))


def check1(before):
    after = page._project.clip("sp").start
    print(f"① 时间轴拖动：start {before} -> {after}")
    if abs(after - before - 1.0) > 0.15:
        fail(f"片段拖动位移不对（80px@pps=80 应为 +1.0s，实际 {after - before}）")
    print("① 时间轴片段左右拖 ✓")
    t2_pan()


def t2_pan():
    tl._pps = 600.0          # 放大到内容超出视口，平移才有意义
    tl._relayout()
    page._update_timeline_width()
    QApplication.processEvents()
    sb = page.timeline_scroll.horizontalScrollBar()
    xoff0 = sb.value()
    # 空白区域（片段右侧远点）左右拖
    y = tl._row_tops[1] + 8   # 第 2 行（空行）
    x = tl._x(1.5)
    QTest.mouseMove(tl, _qp(QPointF(x, y)))
    QTest.mousePress(tl, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier, _qp(QPointF(x, y)))
    QTest.mouseMove(tl, _qp(QPointF(x - 120, y)))
    QTest.mouseRelease(tl, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier,
                       _qp(QPointF(x - 120, y)))
    QTimer.singleShot(200, lambda: check2(xoff0))


def check2(xoff0):
    value = page.timeline_scroll.horizontalScrollBar().value()
    print(f"② 横向平移：滚动条 {xoff0} -> {value}")
    if value <= xoff0 + 50:
        fail("空区域拖动没有平移时间轴视图")
    print("② 时间轴横向平移 ✓")
    t3_switch()


def t3_switch():
    idx = page.project_combo.findData("_loadB")
    if idx < 0:
        fail("下拉里没有 _loadB 项目")
    page.project_combo.setCurrentIndex(idx)
    page.project_combo.activated[int].emit(idx)
    QTimer.singleShot(600, check3)


def check3():
    proj = page._project
    print("③ 当前项目:", proj.name if proj else None)
    if not proj or proj.name != "_loadB":
        fail(f"项目切换失败：{proj.name if proj else None}")
    clip = proj.clip("sp")
    if not clip or abs(clip.x - 380) > 1:
        fail("切换后内容不对，像是没加载 _loadB 的数据")

    def check_stage(p):
        got = [a for a in p.get("actors", []) if a["id"] == "sp"]
        print("③ 舞台 actors:", [(a["id"], a["x"]) for a in p.get("actors", [])])
        if not got or abs(got[0]["x"] - 380) > 1:
            fail(f"舞台没同步到新项目: {got}")
        print("③ 项目切换加载 ✓ PASS")
        app.exit(0)

    page.stage.page().runJavaScript(
        "stageApi.probe()", lambda s: check_stage(json.loads(s or "{}")))


QTimer.singleShot(3000, t1_drag_clip)
QTimer.singleShot(30000, lambda: fail("总超时"))
sys.exit(app.exec())
