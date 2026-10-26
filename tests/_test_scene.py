"""看盘小剧场（可露希尔看盘0710）全剧本探针验证（不导出）。

按 ¼速时间轴断言：入场/坐姿、看板揭示、打滚、躺平、屏幕上飞、
起身左行、「强制平仓」字幕卡。
"""
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

PROJ = "可露希尔看盘0710"


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


page = WorkspacePage(RelayLibrary())
page.resize(1500, 950)
page.show()
page.stage.bridge.sigLog.connect(lambda m: print("[stage]", m))

proj = page._store.load(PROJ)
if not proj:
    fail(f"项目 {PROJ} 不存在，先跑 tools/gen_scene_watch.py")
page._project = proj
page._refresh_project_combo(select=PROJ)
page._select("")
page._sync_now()


def probe_at(t, cb):
    js = (f"(function(){{stageApi.setTime({t});return stageApi.probe();}})()")
    page.stage.page().runJavaScript(js, lambda s: cb(json.loads(s or "{}")))


def wait_spine():
    def got(snap):
        actors = {a["id"]: a for a in snap.get("actors", [])}
        if not all(actors.get(cid, {}).get("ready") for cid in ("click", "click2")):
            QTimer.singleShot(700, wait_spine)
            return
        print("可露希尔与可露希尔2号骨架就绪")
        probe_at(11.6, check1)

    probe_at(0.1, got)


def check1(snap):
    """t=11.6：坐姿看盘（Sit），第一天遮罩揭示约中段。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if len(actors) != len(proj.clips):
        fail(f"actor 数不对: {len(actors)} vs {len(proj.clips)}")
    c = actors["click"]
    if c.get("anim") != "Sit":
        fail(f"t=11.6 应在坐姿（Sit），实际 {c.get('anim')}")
    m = actors.get("mask0")
    if not m or not (690 < m.get("ex", -1e9) < 735):
        fail(f"t=11.6 mask0 揭示进度不对: {m}")
    print(f"t=11.6 ✓ Sit 看盘, mask.ex={m['ex']:.0f}")
    probe_at(12.8, check1b)


def check1b(snap):
    """t=12.8：涨停日自创动作「开心」（欢呼弹跳）。"""
    c = {a["id"]: a for a in snap.get("actors", [])}["click"]
    if c.get("proc") != "开心":
        fail(f"t=12.8 应在自创动作「开心」，实际 proc={c.get('proc')}")
    print("t=12.8 ✓ 开心（欢呼）")
    probe_at(15.5, check1c)


def check1c(snap):
    """t=15.5：跌停日自创动作「惊讶」（后仰发抖）。"""
    c = {a["id"]: a for a in snap.get("actors", [])}["click"]
    if c.get("proc") != "惊讶":
        fail(f"t=15.5 应在自创动作「惊讶」，实际 proc={c.get('proc')}")
    print("t=15.5 ✓ 惊讶（后仰发抖）")
    probe_at(13.4, check2)


def check2(snap):
    """t=13.4：第一天整帧就绪（遮罩已停、现价徽章在窗内）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m = actors.get("mask0")
    if not m or abs(m.get("ex", 0) - 844) > 40:
        fail(f"t=13.4 mask0 应已停进面板下: {m}")
    p = actors.get("priceb0")
    if not (p["start"] <= 13.4 < p["end"]):
        fail("priceb0 应已出现")
    print(f"t=13.4 ✓ 遮罩停进面板下 mask.ex={m['ex']:.0f}，现价徽章在窗内")
    probe_at(23.0, check3)


def check3(snap):
    """t=23.0：摔在地板打滚，第三天遮罩揭示中。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click"]
    if (c.get("skelX") or 0) < 1090:
        fail(f"t=23.0 应已摔在地板: skelX={c.get('skelX')}")
    m = actors.get("mask3")
    if not m or not (690 < m.get("ex", 0) < 735):
        fail(f"t=23.0 mask3 揭示中段不对: {m}")
    print(f"t=23.0 ✓ 地板打滚 skelX={c['skelX']:.0f}, mask.ex={m['ex']:.0f}")
    probe_at(25.6, check_switch)


def check_switch(snap):
    """t=25.6：原地切换成可露希尔2号并继承 Sleep。"""
    c = {a["id"]: a for a in snap.get("actors", [])}["click2"]
    if not c.get("ready") or c.get("anim") != "Sleep":
        fail(f"t=25.6 可露希尔2号应在 Sleep: {c}")
    if abs((c.get("skelX") or 0) - 1160) > 2:
        fail(f"t=25.6 切换位置不连续: skelX={c.get('skelX')}")
    print(f"t=25.6 ✓ 可露希尔2号原地接管 skelX={c['skelX']:.0f}")
    probe_at(31.0, check4)


def check4(snap):
    """t=31.0：07-17 帧，可露希尔2号躺平（Sleep）。"""
    c = {a["id"]: a for a in snap.get("actors", [])}["click2"]
    if c.get("anim") != "Sleep":
        fail(f"t=31.0 应在 Sleep，实际 {c.get('anim')}")
    print("t=31.0 ✓ 07-17 可露希尔2号躺平麻木")
    probe_at(35.0, check5)


def check5(snap):
    """t=35.0：屏幕已上飞，可露希尔2号起身往左走。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click2"]
    if c.get("anim") != "Move":
        fail(f"t=35.0 应在起身左行（Move），实际 {c.get('anim')}")
    sx = c.get("skelX") or 0
    if not (250 < sx < 450):
        fail(f"t=35.0 应在左行途中: skelX={sx}")
    p = actors.get("popup")
    if (p.get("ey") or 0) > 0:
        fail(f"t=35.0 弹窗应已上飞: ey={p.get('ey')}")
    print(f"t=35.0 ✓ 屏幕上飞(popup.ey={p['ey']:.0f}), 左行 skelX={sx:.0f}")
    probe_at(37.4, check6)


def check6(snap):
    """t=38.0：可露希尔2号坐下（Sit），字幕卡在窗内。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click2"]
    if c.get("anim") != "Sit":
        fail(f"t=38.0 应已坐下（Sit），实际 {c.get('anim')}")
    if (c.get("skelX") or 0) > 420:
        fail(f"t=38.0 应已走到左侧: skelX={c.get('skelX')}")
    for cid in ("wipe",):
        a = actors[cid]
        if not (a["start"] <= 37.4 < a["end"]):
            fail(f"{cid} 时间窗不含 37.4")
    print(f"t=38.0 ✓ 坐下 skelX={c['skelX']:.0f}, 强制平仓字幕卡在窗内")
    print("PASS 全剧本探针")
    app.exit(0)


QTimer.singleShot(4000, wait_spine)
QTimer.singleShot(120000, lambda: fail("总超时"))
sys.exit(app.exec())
