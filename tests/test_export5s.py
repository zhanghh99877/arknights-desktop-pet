"""综合测试：导出 5s 视频 = SVG鹈鹕踩自行车 + 背景PNG太阳 + spine新能源天使Die。

验证：h264/时长5s/画面有太阳/SVG在动/spine在动（帧间差异）。
"""
import json
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
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
from core.workspace import AnimEntry, Clip, WorkspaceStore
from ui.workspace_page import WorkspacePage

ROOT = WorkspaceStore().root
PROJ = "_test5s"
SUN_CENTER = (1080, 140)   # 太阳中心（逻辑像素），用于像素校验


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


# ---------- 素材 1：太阳背景 PNG ----------
def make_sun_png(path):
    from PySide6.QtGui import QImage, QPainter, QColor, QPen, QRadialGradient
    from PySide6.QtCore import QPointF
    img = QImage(1280, 720, QImage.Format.Format_RGB32)
    p = QPainter(img)
    g = QRadialGradient(QPointF(640, 780), 900)
    g.setColorAt(0.0, QColor("#b8e2f4"))
    g.setColorAt(1.0, QColor("#5aa9d6"))
    p.fillRect(img.rect(), g)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cx, cy, r = SUN_CENTER[0], SUN_CENTER[1], 70
    p.setPen(QPen(QColor("#ffd23e"), 14))
    import math
    for i in range(12):
        a = i * math.pi / 6
        p.drawLine(int(cx + math.cos(a) * (r + 16)), int(cy + math.sin(a) * (r + 16)),
                   int(cx + math.cos(a) * (r + 44)), int(cy + math.sin(a) * (r + 44)))
    p.setBrush(QColor("#ffcf3f"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(int(cx - r), int(cy - r), r * 2, r * 2)
    p.setBrush(QColor("#ffe9a3"))
    p.drawEllipse(int(cx - r * 0.62), int(cy - r * 0.62), int(r * 1.24), int(r * 1.24))
    p.end()
    img.save(str(path), "PNG")


# ---------- 素材 2：鹈鹕踩自行车 SVG（SMIL 动画） ----------
PELICAN_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 300" width="420" height="300">
  <ellipse cx="210" cy="272" rx="160" ry="9" fill="#00000022"/>
  <g stroke="#333333" stroke-width="5" fill="none">
    <circle cx="140" cy="230" r="52"/>
    <circle cx="300" cy="230" r="52"/>
  </g>
  <g stroke="#777777" stroke-width="2.5">
    <g>
      <line x1="140" y1="230" x2="140" y2="180"/><line x1="140" y1="230" x2="188" y2="230"/>
      <line x1="140" y1="230" x2="177" y2="193"/><line x1="140" y1="230" x2="103" y2="193"/>
      <line x1="140" y1="230" x2="103" y2="267"/><line x1="140" y1="230" x2="177" y2="267"/>
      <animateTransform attributeName="transform" type="rotate" from="0 140 230" to="360 140 230" dur="1s" repeatCount="indefinite"/>
    </g>
    <g>
      <line x1="300" y1="230" x2="300" y2="180"/><line x1="300" y1="230" x2="348" y2="230"/>
      <line x1="300" y1="230" x2="337" y2="193"/><line x1="300" y1="230" x2="263" y2="193"/>
      <line x1="300" y1="230" x2="263" y2="267"/><line x1="300" y1="230" x2="337" y2="267"/>
      <animateTransform attributeName="transform" type="rotate" from="0 300 230" to="360 300 230" dur="1s" repeatCount="indefinite"/>
    </g>
  </g>
  <g stroke="#d23b3b" stroke-width="7" fill="none" stroke-linecap="round">
    <path d="M140 230 L215 225 L255 160 L300 230 M215 225 L255 160"/>
    <line x1="255" y1="160" x2="300" y2="152"/>
  </g>
  <g>
    <animateTransform attributeName="transform" type="translate" values="0 0; 0 -7; 0 0" dur="0.6s" repeatCount="indefinite"/>
    <ellipse cx="210" cy="150" rx="72" ry="46" fill="#f4f1ea" stroke="#c9c2b2" stroke-width="3"/>
    <path d="M150 132 Q120 96 152 74 Q168 64 178 78 Q158 84 162 104 Q166 122 186 130 Z" fill="#f4f1ea" stroke="#c9c2b2" stroke-width="3"/>
    <circle cx="176" cy="82" r="20" fill="#f4f1ea" stroke="#c9c2b2" stroke-width="3"/>
    <path d="M192 86 Q236 92 244 116 L196 112 Z" fill="#f0a13c"/>
    <path d="M196 112 L244 116 Q238 132 200 124 Z" fill="#d9832b"/>
    <circle cx="182" cy="76" r="4.5" fill="#222222"/>
    <path d="M150 118 Q186 100 214 118" stroke="#c9c2b2" stroke-width="2.5" fill="none"/>
    <line x1="196" y1="192" x2="205" y2="224" stroke="#f0a13c" stroke-width="6" stroke-linecap="round"/>
    <line x1="232" y1="192" x2="240" y2="222" stroke="#f0a13c" stroke-width="6" stroke-linecap="round"/>
  </g>
  <g>
    <animateTransform attributeName="transform" type="rotate" from="0 218 226" to="360 218 226" dur="1.4s" repeatCount="indefinite"/>
    <line x1="218" y1="226" x2="258" y2="226" stroke="#555555" stroke-width="5" stroke-linecap="round"/>
    <rect x="252" y="219" width="13" height="14" rx="2" fill="#333333"/>
    <rect x="172" y="219" width="13" height="14" rx="2" fill="#333333"/>
  </g>
</svg>'''


# ---------- 建项目 ----------
shutil.rmtree(ROOT / PROJ, ignore_errors=True)
store = WorkspaceStore()
proj = store.create(PROJ)
assets = store.assets_dir(PROJ)
make_sun_png(assets / "sun_bg.png")
(assets / "pelican_bike.svg").write_text(PELICAN_SVG, encoding="utf-8")

proj.canvas = {"w": 1280, "h": 720, "fps": 30, "bg": "#b8e2f4"}
proj.duration = 5.0
proj.layers = 3
proj.layers_visible = [True, True, True]
# 背景太阳：最底层，0~5s
proj.clips.append(Clip(id="sun", type="png", asset="sun_bg.png", name="太阳背景",
                       layer=2, start=0.0, end=5.0, x=640, y=360))
# 鹈鹕自行车：中层，0~5s
proj.clips.append(Clip(id="peli", type="svg", asset="pelican_bike.svg",
                       name="鹈鹕踩自行车", layer=1, start=0.0, end=5.0,
                       x=380, y=400))
# 新能源天使 Die：最上层，0~5s 播一次
c = Clip(id="exu", type="spine", asset="新能源天使", name="新能源天使·死亡",
         layer=0, start=0.0, end=5.0, x=900, y=640)
c.anims.append(AnimEntry(start=0.0, end=5.0, anim="Die", speed=1.0, loop=False))
proj.clips.append(c)
store.save(proj)
store.set_last(PROJ)
print("项目已建：太阳(bg) + 鹈鹕(svg) + 新能源天使(Die)，时长 5s")

page = WorkspacePage(RelayLibrary())
page.resize(1500, 950)
page.show()
page.raise_()
page.activateWindow()
page.stage.bridge.sigLog.connect(lambda m: print("[stage]", m))

# ---------- 导出 ----------
out = ROOT / PROJ / "综合测试5s.mp4"
ORIG = (QFileDialog.getSaveFileName, QMessageBox.warning,
        QMessageBox.information, QMessageBox.exec)
QFileDialog.getSaveFileName = staticmethod(
    lambda *a, **k: (str(out), "MP4 (*.mp4)"))
QMessageBox.warning = staticmethod(lambda *a, **k: print("[warn]", str(a[1])[:100]))
QMessageBox.information = staticmethod(lambda *a, **k: print("[info]", str(a[1])[:100]))
QMessageBox.exec = lambda self: 0


def restore_dialogs():
    (QFileDialog.getSaveFileName, QMessageBox.warning,
     QMessageBox.information, QMessageBox.exec) = ORIG


def wait_ready():
    def got(p):
        spine = [a for a in p.get("actors", []) if a["id"] == "exu"]
        if not spine or not spine[0].get("ready"):
            QTimer.singleShot(700, lambda: probe(wait_ready))
            return
        print("新能源天使就绪，开始导出…")
        QTimer.singleShot(200, page._on_export)
        QTimer.singleShot(1200, poll)
    probe(got)


def probe(cb):
    page.stage.page().runJavaScript("stageApi.probe()",
                                    lambda s: cb(json.loads(s or "{}")))


def poll():
    ex = page._exporter
    if ex is None:
        QTimer.singleShot(500, verify)
        return
    print(f"  进度 {ex.frames}/150", end="\r")
    QTimer.singleShot(1000, poll)


def verify():
    restore_dialogs()
    print()
    if not out.exists():
        fail("mp4 未生成")
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run([exe, "-i", str(out)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    info = r.stderr
    if "Video: h264" not in info:
        fail("不是 h264:\n" + info[-600:])
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    if not m:
        fail("读不到时长:\n" + info[:400])
    secs = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    print(f"实际时长: {secs:.2f}s")
    if not (4.85 <= secs <= 5.3):
        fail(f"时长不在 5s 容差内: {secs:.2f}s")
    size = out.stat().st_size
    print(f"mp4 ✓ h264 / 5s / {size} bytes")
    if size < 50000:
        fail("文件过小，画面可能空白")

    # 抽帧校验：1s 与 4s 整体应不同（SVG 轮子在转）；spine 用 0.1s vs 1s
    # 对比（Die 若时长 <1s，1s/4s 都已是冻结末帧）
    from PySide6.QtGui import QImage
    fa = ROOT / PROJ / "_f1.png"
    fb = ROOT / PROJ / "_f4.png"
    fc = ROOT / PROJ / "_f0.png"
    for t, fp in ((1.0, fa), (4.0, fb), (0.1, fc)):
        subprocess.run([exe, "-y", "-ss", str(t), "-i", str(out),
                        "-frames:v", "1", str(fp)],
                       capture_output=True)
    ia, ib = QImage(str(fa)), QImage(str(fb))
    ic = QImage(str(fc))
    if ia.isNull() or ib.isNull() or ic.isNull():
        fail("抽帧失败")

    def region_diff(i1, i2):
        d_pel = d_sp = 0
        for y in range(0, i1.height(), 4):
            for x in range(0, i1.width(), 4):
                c1, c2 = i1.pixelColor(x, y), i2.pixelColor(x, y)
                if abs(c1.red() - c2.red()) + abs(c1.green() - c2.green()) + \
                   abs(c1.blue() - c2.blue()) > 24:
                    if x < i1.width() // 2:
                        d_pel += 1
                    else:
                        d_sp += 1
        return d_pel, d_sp

    d_pel, _ = region_diff(ia, ib)
    _, d_sp = region_diff(ic, ia)
    print(f"鹈鹕区 1s↔4s 差异 {d_pel}；spine区 0.1s↔1s 差异 {d_sp}")
    if d_pel < 30:
        fail(f"SVG 鹈鹕区域几乎无变化（{d_pel}）：SVG 动画可能没动")
    if d_sp < 30:
        fail(f"spine 区域 0.1s↔1s 无变化（{d_sp}）：Die 可能没播或角色没渲染")

    # 太阳像素校验：两帧的太阳中心都应是暖黄色
    from PySide6.QtGui import QImage
    for t, fp in ((1.0, fa), (4.0, fb)):
        img = QImage(str(fp))
        if img.isNull():
            fail(f"抽帧失败: {fp}")
        c = img.pixelColor(int(SUN_CENTER[0] * img.width() / 1280),
                           int(SUN_CENTER[1] * img.height() / 720))
        if not (c.red() > 200 and c.green() > 150 and c.blue() < 190):
            fail(f"t={t}s 太阳像素不对: {c.red()},{c.green()},{c.blue()}")
    print("太阳像素 ✓（两帧太阳中心均为暖黄色）")
    for fp in (fa, fb, fc):
        fp.unlink(missing_ok=True)
    print("PASS 综合测试：SVG鹈鹕 + 太阳背景 + 新能源天使Die → 5s mp4")
    print("输出:", out)
    app.exit(0)


QTimer.singleShot(4000, wait_ready)
QTimer.singleShot(120000, lambda: fail("总超时"))
sys.exit(app.exec())
