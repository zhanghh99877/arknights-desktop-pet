"""第一幕（韭菜的诞生第一幕）全剧本探针验证（不导出）。

按时间轴断言：标题卡、走入坐下、新闻→看板揭示、追高进场、尾盘闪崩
（徽章翻绿+弹幕）、掰屏幕同步旋转、诡异角度换入闪崩尾段、案例二阴跌
台阶徽章、跌停暴怒、复盘亏单、决意、起身出画、结论大字卡。
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

PROJ = "韭菜的诞生第一幕"


def fail(msg):
    print("FAIL:", msg)
    sys.exit(2)


page = WorkspacePage(RelayLibrary())
page.resize(1500, 950)
page.show()
page.stage.bridge.sigLog.connect(lambda m: print("[stage]", m))

store = WorkspaceStore()
proj = store.load(PROJ)
if not proj:
    fail(f"项目 {PROJ} 不存在，先跑 tools/gen_scene_act1.py")
page._project = proj
page._refresh_project_combo(select=PROJ)
page._select("")
page._sync_now()

CLIPS = {c.id: c for c in proj.clips}


def probe_at(t, cb):
    js = (f"(function(){{stageApi.setTime({t});return stageApi.probe();}})()")
    page.stage.page().runJavaScript(js, lambda s: cb(json.loads(s or "{}")))


def in_window(cid, t):
    c = CLIPS[cid]
    return c.start <= t < c.end


def wait_spine():
    def got(snap):
        actors = {a["id"]: a for a in snap.get("actors", [])}
        if not actors.get("click", {}).get("ready"):
            QTimer.singleShot(700, wait_spine)
            return
        print("可露希尔骨架就绪")
        probe_at(1.0, check_title)
    probe_at(0.1, got)


def check_title(snap):
    """t=1.0：黑场标题卡在窗内。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if len(actors) != len(proj.clips):
        fail(f"actor 数不对: {len(actors)} vs {len(proj.clips)}")
    if not in_window("title", 1.0):
        fail("t=1.0 标题卡应在窗内")
    print("t=1.0 ✓ 标题卡")
    probe_at(4.5, check_walk)


def check_walk(snap):
    """t=4.5：走入中（Move），屏幕已降下并切到新闻一。"""
    c = {a["id"]: a for a in snap.get("actors", [])}["click"]
    if c.get("anim") != "Move":
        fail(f"t=4.5 应在走入（Move），实际 {c.get('anim')}")
    if not in_window("news1", 4.5):
        fail("t=4.5 新闻一应在窗内")
    if not in_window("tick1", 4.5):
        fail("t=4.5 跑马灯一应在窗内")
    print("t=4.5 ✓ 走入 + 新闻一 + 跑马灯")
    probe_at(15.0, check_buy)


def check_buy(snap):
    """t=15.0：追高进场（自创动作「开心」）+ 委托成功小卡。"""
    c = {a["id"]: a for a in snap.get("actors", [])}["click"]
    if c.get("proc") != "开心":
        fail(f"t=15.0 应在自创动作「开心」，实际 proc={c.get('proc')}")
    if not in_window("toast1", 15.0):
        fail("t=15.0 委托成功小卡应在窗内")
    print("t=15.0 ✓ 开心（追高进场）+ 委托成功")
    probe_at(20.0, check_reveal)


def check_reveal(snap):
    """t=20.0：高位横盘段揭示中（遮罩按分段映射推进）。"""
    m = {a["id"]: a for a in snap.get("actors", [])}.get("mask1")
    if not m or not (1050 < m.get("ex", -1e9) < 1170):
        fail(f"t=20.0 mask1 揭示进度不对: {m}")
    print(f"t=20.0 ✓ 揭示推进 mask1.ex={m['ex']:.0f}")
    probe_at(25.2, check_crash)


def check_crash(snap):
    """t=25.2：闪崩——徽章翻绿 + 💥 + 弹幕刷屏，曲线仍在（无尾版）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click"]
    if c.get("proc") != "惊讶":
        fail(f"t=25.2 应在「惊讶」，实际 proc={c.get('proc')}")
    for cid in ("badge13", "giant", "dm0", "dm1", "curve1a"):
        if not in_window(cid, 25.2):
            fail(f"t=25.2 {cid} 应在窗内")
    t1 = actors.get("tick1")
    if not t1 or not (t1.get("ex", 1e9) < 700):
        fail(f"t=25.2 跑马灯应已冻结在屏内: {t1}")
    print("t=25.2 ✓ 闪崩：翻绿徽章 + 💥 + 弹幕 + 跑马灯冻结")
    probe_at(28.0, check_tilt)


def check_tilt(snap):
    """t=28.0：掰屏幕——屏幕片段绕中心同步旋转（+18°→-18° 途中）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click"]
    if c.get("proc") != "掰屏幕":
        fail(f"t=28.0 应在「掰屏幕」，实际 proc={c.get('proc')}")
    b = actors.get("badge13")
    if not b or not (2 < b.get("erot", 99) < 10):
        fail(f"t=28.0 屏幕旋转角不对: {b}")
    if abs(b.get("ex", 0) - 717) > 2:
        fail(f"t=28.0 帧裁剪片段旋转时应钉在屏幕中心: {b}")
    print(f"t=28.0 ✓ 掰屏幕（同步旋转 erot={b['erot']:.1f}°）")
    probe_at(31.5, check_found)


def check_found(snap):
    """t=31.5：诡异角度 -26°——带闪崩尾段的曲线已换入，人屏一起沉默。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click"]
    if c.get("proc") != "沉默":
        fail(f"t=31.5 应在「沉默」，实际 proc={c.get('proc')}")
    if not in_window("curve1b", 31.5):
        fail("t=31.5 带闪崩尾段的曲线应在窗内")
    b = actors.get("badge13")
    if not b or abs(b.get("erot", 99) + 26) > 2.5:
        fail(f"t=31.5 应停在诡异角度 -26°: {b}")
    print(f"t=31.5 ✓ 诡异角度 {b['erot']:.1f}° + 闪崩尾段换入 + 沉默")
    probe_at(36.0, check_news2)


def check_news2(snap):
    """t=36.0：屏幕转正，新闻二（多索雷斯啤酒）播报中。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click"]
    if c.get("anim") != "Sit":
        fail(f"t=36.0 应回到坐姿，实际 {c.get('anim')}")
    if not in_window("news2", 36.0):
        fail("t=36.0 新闻二应在窗内")
    b = actors.get("badge13")
    if b and abs(b.get("erot", 0)) > 0.5:
        fail(f"t=36.0 屏幕应已转正: {b}")
    print("t=36.0 ✓ 新闻二 + 屏幕转正")
    probe_at(44.0, check_case2)


def check_case2(snap):
    """t=44.0：案例二温水煮青蛙——阴跌揭示中，+1.20% 徽章在窗内。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if not in_window("badge23", 44.0):
        fail("t=44.0 +1.20% 徽章应在窗内")
    m = actors.get("mask2")
    if not m or not (940 < m.get("ex", -1e9) < 1040):
        fail(f"t=44.0 mask2 揭示进度不对: {m}")
    if not in_window("curve2", 44.0):
        fail("t=44.0 案例二分时应 在窗内")
    print(f"t=44.0 ✓ 案例二阴跌揭示 mask2.ex={m['ex']:.0f}")
    probe_at(50.5, check_rage)


def check_rage(snap):
    """t=50.5：跌停暴怒 + 第二波弹幕。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click"]
    if c.get("proc") != "暴怒":
        fail(f"t=50.5 应在「暴怒」，实际 proc={c.get('proc')}")
    for cid in ("badge26", "dm6", "dm7"):
        if not in_window(cid, 50.5):
            fail(f"t=50.5 {cid} 应在窗内")
    print("t=50.5 ✓ 跌停暴怒 + 弹幕")
    probe_at(58.5, check_resolve)


def check_resolve(snap):
    """t=58.5：复盘亏单 + 决意。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click"]
    if c.get("proc") != "决意":
        fail(f"t=58.5 应在「决意」，实际 proc={c.get('proc')}")
    for cid in ("rec1", "rec2", "bub8"):
        if not in_window(cid, 58.5):
            fail(f"t=58.5 {cid} 应在窗内")
    print("t=58.5 ✓ 复盘亏单 + 决意")
    probe_at(62.0, check_exit)


def check_exit(snap):
    """t=62.0：起身左行出画（接第二幕）。"""
    c = {a["id"]: a for a in snap.get("actors", [])}["click"]
    if c.get("anim") != "Move":
        fail(f"t=62.0 应在起身左行（Move），实际 {c.get('anim')}")
    if (c.get("skelX") or 0) > 600:
        fail(f"t=62.0 应已行至左半场: skelX={c.get('skelX')}")
    print(f"t=62.0 ✓ 出画左行 skelX={c['skelX']:.0f}")
    probe_at(65.0, check_concl)


def check_concl(snap):
    """t=65.0：结论大字卡（硬切）。"""
    if not in_window("concl", 65.0):
        fail("t=65.0 结论卡应在窗内")
    if CLIPS["click"].end > 65.0:
        fail("t=65.0 可露希尔应已退场")
    print("t=65.0 ✓ 结论大字卡，人物已退场")
    print("PASS 第一幕全剧本探针")
    app.exit(0)


QTimer.singleShot(4000, wait_spine)
QTimer.singleShot(120000, lambda: fail("总超时"))
sys.exit(app.exec())
