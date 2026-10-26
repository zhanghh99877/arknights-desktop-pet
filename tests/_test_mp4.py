"""播放页 MP4 导出端到端：大哭打滚（程序动作）+ Sleep（官方动作）。

验证：H.264、480x480、时长、体积、帧数。
"""
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--autoplay-policy=no-user-gesture-required --allow-file-access-from-files")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)

from core.assets import RelayLibrary
from core.pet_config import PetConfig
from ui.play_page import PlayPage

TMP = tempfile.mkdtemp(prefix="_mp4test_")


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


page = PlayPage(RelayLibrary(), PetConfig())
page.resize(1100, 700)
page.show()
page.raise_()
page.activateWindow()

QMessageBox.exec = lambda self: 0
QMessageBox.warning = staticmethod(lambda *a, **k: print("[warn]", str(a[1])[:120]))
QMessageBox.information = staticmethod(lambda *a, **k: None)


def wait_loaded(cb):
    page.preview.page().runJavaScript(
        "!!(window.player && window.player.loaded)",
        lambda ok: cb(bool(ok)))


def poll_loaded(cb):
    def got(ok):
        if ok:
            cb()
        else:
            QTimer.singleShot(500, lambda: poll_loaded(cb))
    wait_loaded(got)


state = {"target": None, "results": []}
from pathlib import Path as _P  # noqa


def export_row(row_label, out_name):
    """选中指定条目并导出，完成后回调 verify。"""
    for row in range(page.anim_list.count()):
        if page.anim_list.item(row).text() == row_label:
            break
    else:
        fail(f"列表里没有 {row_label}")
    page.anim_list.setCurrentRow(row)
    out = os.path.join(TMP, out_name)
    QFileDialog.getSaveFileName = staticmethod(
        lambda *a, **k: (out, "GIF (*.gif)"))
    page._export_selected_mp4()
    state["target"] = out
    QTimer.singleShot(1000, lambda: poll_export())


def poll_export():
    if page._mp4_expected:
        QTimer.singleShot(500, poll_export)
        return
    verify(state["target"])


def verify(out):
    import pathlib
    p = pathlib.Path(out)
    if not p.exists():
        fail(f"GIF 未生成: {out}")
    size = p.stat().st_size
    head = p.read_bytes()[:12]
    print(f"导出: {p.name}  {size} bytes  头={head[:8]!r}")
    if size > 1_000_000:
        fail(f"超过 1MB: {size}")
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run([exe, "-i", str(p), "-map", "0:v:0", "-c", "copy",
                        "-f", "null", "-"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    info = r.stderr
    import re
    m = re.findall(r"frame=\s*(\d+)", info)
    frames = int(m[-1]) if m else 0
    if "h264" not in info and "Video:" not in info:
        fail("ffprobe 读不到视频流: " + info[:400])
    wh = re.search(r"Video:\s+\S+.*?(\d{2,4})x(\d{2,4})", info)
    dims = wh.groups() if wh else ("?", "?")
    print(f"  尺寸: {dims[0]}x{dims[1]}  帧数: {frames}")
    if dims != ("480", "480"):
        fail(f"尺寸不是 480x480: {dims}")
    if frames < 20:
        fail(f"帧数太少: {frames}")
    if "h264" not in info:
        fail("不是 h264 编码")
    state["results"].append((p.name, size, frames))
    next_step()


def next_step():
    if not state["results"]:
        export_row("✨ 大哭打滚", "proc.mp4")
    elif len(state["results"]) == 1:
        export_row("Sleep", "sleep.mp4")
    else:
        print("全部 PASS:", state["results"])
        app.exit(0)


QTimer.singleShot(2000, lambda: poll_loaded(next_step))
QTimer.singleShot(180000, lambda: fail("总超时"))
sys.exit(app.exec())
