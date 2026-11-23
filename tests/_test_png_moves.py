"""PNG/SVG 平移旋转条目（moves）验证。

probe() 的 ex/ey/erot 是 evalMove 后的有效变换，逐时间点断言：
首条目前→起点；命中→线性插值；条目间→冻结上一条目终点；
全部结束→末条目终点。SVG 走同一套求值（DOM transform 路径）。
"""
import json
import os
import shutil
import struct
import sys
import zlib

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
from core.workspace import Clip, MoveEntry, WorkspaceStore
from ui.workspace_page import WorkspacePage

ROOT = WorkspaceStore().root
TOL = 1.1

# 期望：t, 片段id, {字段: 值}
CASES = [
    (0.5, "img", {"ex": 100, "ey": 120, "erot": 0}),    # 首条目之前 → 起点
    (1.5, "img", {"ex": 150, "ey": 145, "erot": 0}),    # 命中条目1 → 中点
    (2.5, "img", {"ex": 200, "ey": 170, "erot": 0}),    # 条目间 → 冻结条目1终点
    (3.5, "img", {"ex": 350, "ey": 240, "erot": 45}),   # 命中条目2 → 中点
    (4.5, "img", {"ex": 400, "ey": 280, "erot": 90}),   # 全部结束 → 终点
    (2.0, "vec", {"ex": 650, "ey": 400, "erot": 90}),   # SVG 命中 → 中点
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


def png_bytes(w=8, h=8):
    """最小合法 PNG（红色，供 <img> 加载出 natW/natH）。"""
    def chunk(t, d):
        return (struct.pack(">I", len(d)) + t + d +
                struct.pack(">I", zlib.crc32(t + d) & 0xffffffff))
    raw = b"".join(b"\x00" + b"\xff\x00\x00\xff" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
       '<circle cx="20" cy="20" r="18" fill="#2f8cff"/></svg>')

store = WorkspaceStore()
shutil.rmtree(ROOT / "_pngmovetest", ignore_errors=True)
proj = store.create("_pngmovetest")
(store.assets_dir("_pngmovetest") / "dot.png").write_bytes(png_bytes(200, 100))
(store.assets_dir("_pngmovetest") / "vec.svg").write_text(SVG, encoding="utf-8")

img = Clip(id="img", type="png", asset="dot.png", start=0.0, end=5.0,
           x=640, y=360)
img.moves = [
    MoveEntry(start=1, end=2, x0=100, y0=120, x1=200, y1=170),
    MoveEntry(start=3, end=4, x0=300, y0=200, x1=400, y1=280,
              rot0=0, rot1=90),
]
vec = Clip(id="vec", type="svg", asset="vec.svg", start=0.0, end=5.0,
           x=600, y=400)
vec.moves = [MoveEntry(start=0, end=4, x0=600, y0=400, x1=700, y1=400,
                       rot0=0, rot1=180)]
proj.clips += [img, vec]
proj.duration = 5.0
store.save(proj)
store.set_last("_pngmovetest")

page = WorkspacePage(RelayLibrary())
page.resize(1400, 900)
page.show()
page.stage.bridge.sigLog.connect(lambda m: print("[stage]", m))

queue = list(CASES)


def run_case():
    if not queue:
        print("PNG/SVG moves 求值全部符合预期")
        QTimer.singleShot(250, check_rotated_hit)
        return
    t, cid, want = queue.pop(0)
    js = (f"(function(){{stageApi.setTime({t});return stageApi.probe();}})()")
    page.stage.page().runJavaScript(
        js, lambda s: got(t, cid, want, json.loads(s or "{}")))


def got(t, cid, want, snap):
    actor = next((a for a in snap.get("actors", []) if a.get("id") == cid), None)
    if not actor:
        fail(f"probe 里找不到片段 {cid}")
    bad = [f"{k}={actor.get(k)}(期望{v})"
           for k, v in want.items() if abs(actor.get(k, 1e9) - v) > TOL]
    print(f"t={t} {cid}: " +
          " ".join(f"{k}={actor.get(k, None):.1f}" for k in want) +
          ("  ✓" if not bad else ""))
    if bad:
        fail(f"t={t} {cid} 求值不对：{'，'.join(bad)}")
    QTimer.singleShot(250, run_case)


def check_rotated_hit():
    js = "(function(){stageApi.setTime(3.5);return stageApi.debugHit(414,304);})()"
    page.stage.page().runJavaScript(
        js, lambda s: got_rotated_hit(json.loads(s or "[]")))


def got_rotated_hit(result):
    hits = result[-1].get("hitsAt", []) if result else []
    print("旋转 PNG 可见边缘命中:", hits)
    if "img" not in hits:
        fail("rot=45 的 PNG 可见位置未命中")
    js = ("(function(){var stage=document.getElementById('stage');"
          "var r=document.getElementById('overlay').getBoundingClientRect();"
          "var c=document.getElementById('gl');"
          "function pt(sx,sy){return [r.left+sx/c.width*r.width,"
          "                           r.top+sy/c.height*r.height];}"
          "function ev(t,a){return new MouseEvent(t,{bubbles:true,cancelable:true,button:0,clientX:a[0],clientY:a[1]});}"
          "stage.dispatchEvent(ev('mousedown',pt(414,304)));"
          "document.dispatchEvent(ev('mousemove',pt(464,334)));"
          "document.dispatchEvent(ev('mouseup',pt(464,334)));"
          "return true;})()")
    page.stage.page().runJavaScript(js)
    QTimer.singleShot(500, check_rotated_drag)


def check_rotated_drag():
    move = page._project.clip("img").moves[1]
    print("旋转 PNG 拖动后的 move 起点:", move.x0, move.y0)
    if move.x0 < 320 or move.y0 < 220:
        fail("命中成功但拖动没有落库")
    print("PASS：PNG/SVG moves + 旋转 PNG 命中拖动")
    app.exit(0)


QTimer.singleShot(3000, run_case)
QTimer.singleShot(30000, lambda: fail("总超时"))
sys.exit(app.exec())
