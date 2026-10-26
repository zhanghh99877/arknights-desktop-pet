"""行情回放看板（航天工程分时0717）渲染 + 导出验证。

probe 断言：遮罩 moves 插值位置（揭示进度）；导出 mp4 后抽帧留盘
（0.2/0.6/2.0/3.8/5.4s）供人工检查 UI。
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--autoplay-policy=no-user-gesture-required --allow-file-access-from-files"
    " --disable-background-timer-throttling --disable-renderer-backgrounding"
    " --disable-backgrounding-occluded-windows")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)

from core.assets import RelayLibrary
from core.workspace import WorkspaceStore
from ui.workspace_page import WorkspacePage

PROJ = "航天工程分时0717"
ROOT = WorkspaceStore().root
FRAMES = [0.2, 0.6, 2.0, 3.8, 5.4]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


page = WorkspacePage(RelayLibrary())
page.resize(1500, 950)
page.show()
page.stage.bridge.sigLog.connect(lambda m: print("[stage]", m))

proj = page._store.load(PROJ)
if not proj:
    fail(f"项目 {PROJ} 不存在，先跑 tools/gen_stock_board.py")
page._project = proj
page._refresh_project_combo(select=PROJ)
page._select("")
page._sync_now()

out = ROOT / PROJ / "行情回放.mp4"
QFileDialog.getSaveFileName = staticmethod(
    lambda *a, **k: (str(out), "MP4 (*.mp4)"))
QMessageBox.warning = staticmethod(
    lambda *a, **k: print("[warn]", str(a[1])[:120]))
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.exec = lambda self: 0


def probe_at(t, cb):
    js = (f"(function(){{stageApi.setTime({t});return stageApi.probe();}})()")
    page.stage.page().runJavaScript(js, lambda s: cb(json.loads(s or "{}")))


def check1(snap):
    """t=2.8：第一天揭示中段（开场 1.6s + 帧长 3.8s 的 ¼速节奏）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if len(actors) != len(proj.clips):
        fail(f"actor 数不对: {len(actors)} vs {len(proj.clips)}")
    m = actors.get("mask0")
    if not m or not (580 < m.get("ex", -1e9) < 680):
        fail(f"t=2.8 mask0 揭示进度不对: {m}")
    for cid in ("curve0", "labels0", "dateb0"):
        a = actors[cid]
        if not (a["start"] <= 2.8 < a["end"]):
            fail(f"{cid} 时间窗不含 2.8")
    print(f"t=2.8 ✓ mask0.ex={m['ex']:.0f}（揭示中段）")
    probe_at(8.0, check2)


def check2(snap):
    """t=8.0：第二天整帧就绪（遮罩停进侧栏面板下、现价徽章在窗内）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m = actors["mask1"]
    if not (870 < m.get("ex", 0) < 970):
        fail(f"t=8.0 mask1 应已停进侧栏面板下: {m}")
    p = actors["priceb1"]
    if not (p["start"] <= 8.0 < p["end"]):
        fail("priceb1 应已出现")
    print(f"t=8.0 ✓ mask1.ex={m['ex']:.0f}（已停进面板下）现价徽章在窗内")
    QTimer.singleShot(300, start_export)


def start_export():
    print("开始导出 mp4（实时 5.5s）…")
    page._on_export()
    QTimer.singleShot(1500, poll)


def poll():
    ex = page._exporter
    if ex is None:
        QTimer.singleShot(400, extract)
        return
    print(f"  进度 {ex.frames}/{ex.expected}", end="\r")
    QTimer.singleShot(800, poll)


def extract():
    if not out.exists():
        fail("mp4 未生成")
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    kept = []
    for t in FRAMES:
        fp = ROOT / PROJ / f"_f{t}.png"
        r = subprocess.run([exe, "-y", "-i", str(out), "-ss", str(t),
                            "-frames:v", "1", str(fp)], capture_output=True)
        if not fp.exists():
            fail(f"抽帧失败 t={t}: {r.stderr[-200:]}")
        kept.append(str(fp))
    print("抽帧完成（供人工检查）：")
    for p in kept:
        print("  ", p)
    print("PASS 渲染+导出+抽帧")
    app.exit(0)


QTimer.singleShot(3500, lambda: probe_at(2.8, check1))
QTimer.singleShot(120000, lambda: fail("总超时"))
sys.exit(app.exec())
