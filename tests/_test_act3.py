"""第三幕（明晚必涨第三幕）全剧本探针验证（不导出）。

按时间轴断言：标题卡、深夜作战室（F10→作战计划→决意+回忆气泡）、
时间黑卡、开盘全仓开心、洗盘嘴硬、闪崩（徽章翻绿+💥+弹幕+跑马灯冻结）、
缪缪入场旁观、大哭打滚清仓、对峙（暴怒→装傻→耳语→收盘牌→红包退我）、
离场、后天黑卡、低开装死、偷偷瞟惊讶、涨停（🚀+闪白+战绩单+弹幕）、
仰望跪求、得意讨红包、决意定格、结论三连卡。
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

PROJ = "明晚必涨第三幕"


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
    fail(f"项目 {PROJ} 不存在，先跑 tools/gen_scene_act3.py")
page._project = proj
page._refresh_project_combo(select=PROJ)
page._select("")
page._sync_now()

CLIPS = {c.id: c for c in proj.clips}


def probe_at(t, cb, tries=8):
    """setTime 后校验页面时间确实到位；页面加载竞态时重试。"""
    def run():
        js = (f"(function(){{stageApi.setTime({t});return stageApi.probe();}})()")
        page.stage.page().runJavaScript(js, check)
    def check(s):
        snap = json.loads(s or "{}")
        if abs((snap.get("time") if snap else -1) - t) > 0.01 and tries > 0:
            QTimer.singleShot(400, lambda: probe_at(t, cb, tries - 1))
            return
        cb(snap)
    run()


def in_window(cid, t):
    c = CLIPS[cid]
    return c.start <= t < c.end


def actor(snap, cid):
    return {a["id"]: a for a in snap.get("actors", [])}.get(cid, {})


def wait_spine():
    def got(snap):
        actors = {a["id"]: a for a in snap.get("actors", [])}
        if not actors.get("click", {}).get("ready"):
            QTimer.singleShot(700, wait_spine)
            return
        print("可露希尔骨架就绪")
        probe_at(1.0, check_title)
    probe_at(0.5, got)


def check_title(snap):
    """t=1.0：黑场标题卡；人物未出场。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if len(actors) != len(proj.clips):
        fail(f"actor 数不对: {len(actors)} vs {len(proj.clips)}")
    if not in_window("title", 1.0):
        fail("t=1.0 标题卡应在窗内")
    if in_window("click", 1.0):
        fail("t=1.0 可露希尔不应在场")
    print("t=1.0 ✓ 标题卡")
    probe_at(8.0, check_night)


def check_night(snap):
    """t=8.0：深夜房间 + F10 档案 + 时间牌，她伏案（Sit）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    for cid in ("scene_night", "info1", "chip"):
        if not in_window(cid, 8.0):
            fail(f"t=8.0 {cid} 应在窗内")
    c = actors["click"]
    if c.get("anim") != "Sit":
        fail(f"t=8.0 应在夜读（Sit），实际 {c.get('anim')}")
    if in_window("scene_day", 8.0):
        fail("t=8.0 白天房间不应在场")
    print("t=8.0 ✓ 深夜作战室 + F10 档案")
    probe_at(20.0, check_plan)


def check_plan(snap):
    """t=20.0：作战计划页 + 决意搓手 + 回忆气泡。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if not in_window("info2", 20.0):
        fail("t=20.0 作战计划页应在窗内")
    if actors["click"].get("proc") != "决意":
        fail(f"t=20.0 应在「决意」，实际 proc={actors['click'].get('proc')}")
    if not in_window("bub0", 20.0):
        fail("t=20.0 回忆气泡应在窗内")
    print("t=20.0 ✓ 作战计划 + 决意 + 回忆气泡")
    probe_at(25.0, check_card1)


def check_card1(snap):
    """t=25.0：黑卡「明天 09:25」压场（负图层 SVG）。"""
    if not in_window("card1", 25.0):
        fail("t=25.0 时间黑卡应在窗内")
    if CLIPS["card1"].layer >= 0:
        fail("时间黑卡应为负图层（盖住人物）")
    print("t=25.0 ✓ 时间黑卡（负图层）")
    probe_at(31.0, check_joy)


def check_joy(snap):
    """t=31.0：全仓委托 + 开心 + 徽章 + 跑马灯。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("proc") != "开心":
        fail(f"t=31.0 应在「开心」，实际 proc={actors['click'].get('proc')}")
    for cid in ("b11", "tick1", "curve1"):
        if not in_window(cid, 31.0):
            fail(f"t=31.0 {cid} 应在窗内")
    if not (in_window("toast1", 27.8) and not in_window("toast1", 31.0)):
        fail("全仓委托小卡窗口应为 27.0-28.4（硬切进出）")
    print("t=31.0 ✓ 全仓买入 + 开心 + 行情机械")
    probe_at(50.0, check_slide)


def check_slide(snap):
    """t=50.0：阴跌嘴硬（Interact + 洗盘台词 + 弹幕二波）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("proc") != "Interact":
        fail(f"t=50.0 应在「Interact」，实际 proc={actors['click'].get('proc')}")
    if not in_window("bub1", 50.0):
        fail("t=50.0 洗盘台词应在窗内")
    if not in_window("dm6", 50.0):
        fail("t=50.0 弹幕二波应在窗内")
    print("t=50.0 ✓ 洗盘嘴硬 + 弹幕二波")
    probe_at(60.0, check_dread)


def check_dread(snap):
    """t=60.0：跳水恐惧（惊讶 + 翻绿徽章）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("proc") != "惊讶":
        fail(f"t=60.0 应在「惊讶」，实际 proc={actors['click'].get('proc')}")
    if not in_window("b14", 60.0):
        fail("t=60.0 -1.80% 徽章应在窗内")
    print("t=60.0 ✓ 跳水恐惧")
    probe_at(64.3, check_crash)


def check_crash(snap):
    """t=64.3：闪崩——徽章翻绿 + 💥 + 恐慌弹幕 + 跑马灯冻结。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("proc") != "暴怒":
        fail(f"t=64.3 应在「暴怒」，实际 proc={actors['click'].get('proc')}")
    for cid in ("b15", "giant1", "dm12"):
        if not in_window(cid, 64.3):
            fail(f"t=64.3 {cid} 应在窗内")
    t1 = actors.get("tick1")
    if not t1 or not (t1.get("ex", 1e9) < 700):
        fail(f"t=64.3 跑马灯应已冻结在屏内: {t1}")
    if not (63.9 < CLIPS["flash1"].start < 64.1):
        fail(f"闪白帧位置不对: {CLIPS['flash1'].start}")
    print("t=64.3 ✓ 闪崩：翻绿 + 💥 + 恐慌弹幕 + 冻结")
    probe_at(68.5, check_watch)


def check_watch(snap):
    """t=68.5：缪缪走入旁观中。"""
    m = actor(snap, "mlyu")
    if m.get("anim") != "Move":
        fail(f"t=68.5 缪缪应在走入（Move），实际 {m.get('anim')}")
    if not (0 < (m.get("skelX") or 0) < 380):
        fail(f"t=68.5 缪缪走入位置不对: skelX={m.get('skelX')}")
    print(f"t=68.5 ✓ 缪缪入场 skelX={m['skelX']:.0f}")
    probe_at(72.5, check_roll)


def check_roll(snap):
    """t=72.5：她大哭打滚 + 已清仓小卡；缪缪站定旁观。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m, c = actors["mlyu"], actors["click"]
    if c.get("proc") != "大哭打滚":
        fail(f"t=72.5 应在「大哭打滚」，实际 proc={c.get('proc')}")
    if not in_window("toast2", 72.5):
        fail("t=72.5 已清仓小卡应在窗内")
    if not (340 < (m.get("skelX") or 0) < 420):
        fail(f"t=72.5 缪缪应已站定屏幕左侧: skelX={m.get('skelX')}")
    print(f"t=72.5 ✓ 打滚 + 清仓 + 缪缪站定 skelX={m['skelX']:.0f}")
    probe_at(80.0, check_confront)


def check_confront(snap):
    """t=80.0：对峙——她暴怒质问，缪缪站定装傻预备。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m, c = actors["mlyu"], actors["click"]
    if c.get("proc") != "暴怒":
        fail(f"t=80.0 可露希尔应在「暴怒」，实际 proc={c.get('proc')}")
    if not in_window("bub2", 80.0):
        fail("t=80.0 质问台词应在窗内")
    if not (340 < (m.get("skelX") or 0) < 420):
        fail(f"t=80.0 缪缪应已站定屏幕左侧: skelX={m.get('skelX')}")
    print(f"t=80.0 ✓ 对峙开场（缪缪 skelX={m['skelX']:.0f}）")
    probe_at(90.0, check_whisper)


def check_whisper(snap):
    """t=90.0：缪缪耳语拖字诀 + 她沉默盯屏。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["mlyu"].get("proc") != "耳语":
        fail(f"t=90.0 缪缪应在「耳语」，实际 proc={actors['mlyu'].get('proc')}")
    if actors["click"].get("proc") != "沉默":
        fail(f"t=90.0 可露希尔应在「沉默」，实际 proc={actors['click'].get('proc')}")
    if not in_window("bub4", 90.0):
        fail("t=90.0 拖字诀台词应在窗内")
    print("t=90.0 ✓ 耳语拖字诀")
    probe_at(98.5, check_stamp)


def check_stamp(snap):
    """t=98.5：已收盘 + 红包退我暴怒。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if not in_window("stamp", 98.5):
        fail("t=98.5 收盘牌应在窗内")
    if actors["click"].get("proc") != "暴怒":
        fail(f"t=98.5 应在「暴怒」，实际 proc={actors['click'].get('proc')}")
    if not in_window("bub5", 98.5):
        fail("t=98.5 红包退我台词应在窗内")
    print("t=98.5 ✓ 已收盘 + 红包退我")
    probe_at(102.0, check_mout)


def check_mout(snap):
    """t=102.0：缪缪吹口哨离场。"""
    m = actor(snap, "mlyu")
    if m.get("anim") != "Move":
        fail(f"t=102.0 缪缪应在离场（Move），实际 {m.get('anim')}")
    if (m.get("skelX") or 0) > 300:
        fail(f"t=102.0 缪缪应已在左行途中: skelX={m.get('skelX')}")
    print(f"t=102.0 ✓ 缪缪离场 skelX={m['skelX']:.0f}")
    probe_at(105.0, check_card2)


def check_card2(snap):
    """t=105.0：黑卡「后天 09:30」。"""
    if not in_window("card2", 105.0):
        fail("t=105.0 时间黑卡应在窗内")
    print("t=105.0 ✓ 时间黑卡二")
    probe_at(109.0, check_gloom)


def check_gloom(snap):
    """t=109.0：低开装死（Sit + 台词 + 绿徽章 + 跑马灯二）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("anim") != "Sit":
        fail(f"t=109.0 应在装死（Sit），实际 {actors['click'].get('anim')}")
    for cid in ("bub6", "b20", "tick2"):
        if not in_window(cid, 109.0):
            fail(f"t=109.0 {cid} 应在窗内")
    print("t=109.0 ✓ 低开装死")
    probe_at(120.0, check_peek)


def check_peek(snap):
    """t=120.0：偷偷瞟（惊讶 + 爬升徽章）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("proc") != "惊讶":
        fail(f"t=120.0 应在「惊讶」，实际 proc={actors['click'].get('proc')}")
    if not in_window("b22", 120.0):
        fail("t=120.0 +2.10% 徽章应在窗内")
    print("t=120.0 ✓ 偷偷瞟")
    probe_at(133.0, check_limit)


def check_limit(snap):
    """t=133.0：涨停——🚀 + 翻红徽章 + 闪白 + 跑马灯冻结 + 她打滚。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("proc") != "大哭打滚":
        fail(f"t=133.0 应在「大哭打滚」，实际 proc={actors['click'].get('proc')}")
    for cid in ("b26", "giant2", "dm18"):
        if not in_window(cid, 132.35):
            fail(f"t=133.0 {cid} 应在窗内")
    t2 = actors.get("tick2")
    if not t2 or not (t2.get("ex", 1e9) < 700):
        fail(f"t=133.0 跑马灯应已冻结在屏内: {t2}")
    if not (131.9 < CLIPS["flash2"].start < 132.1):
        fail(f"涨停闪白帧位置不对: {CLIPS['flash2'].start}")
    print("t=133.0 ✓ 涨停：🚀 + 弹幕 + 冻结 + 打滚")
    probe_at(137.0, check_receipt)


def check_receipt(snap):
    """t=137.0：两日战绩单浮入。"""
    if not in_window("rec1", 137.0):
        fail("t=137.0 战绩单应在窗内")
    print("t=137.0 ✓ 战绩单 -29.50%")
    probe_at(148.0, check_beg)


def check_beg(snap):
    """t=148.0：仰望跪求 + 缪缪得意 + 双气泡同屏。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("proc") != "仰望":
        fail(f"t=148.0 应在「仰望」，实际 proc={actors['click'].get('proc')}")
    if actors["mlyu"].get("proc") != "得意":
        fail(f"t=148.0 缪缪应在「得意」，实际 proc={actors['mlyu'].get('proc')}")
    for cid in ("bub7", "bub8"):
        if not in_window(cid, 148.0):
            fail(f"t=148.0 {cid} 应在窗内")
    print("t=148.0 ✓ 仰望跪求 + 得意 + 双气泡")
    probe_at(153.5, check_resolve)


def check_resolve(snap):
    """t=153.5：讨红包台词 + 她决意定格（学费心得）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if actors["click"].get("proc") != "决意":
        fail(f"t=153.5 应在「决意」，实际 proc={actors['click'].get('proc')}")
    if not in_window("bub9", 153.5):
        fail("t=153.5 红包台词应在窗内")
    print("t=153.5 ✓ 决意（错误的心得）")
    probe_at(160.0, check_concl)


def check_concl(snap):
    """t=160.0：结论卡一，双人已退场。"""
    if not in_window("conclA", 160.0):
        fail("t=160.0 结论卡一应在窗内")
    for cid in ("click", "mlyu"):
        if CLIPS[cid].end > 158.0:
            fail(f"t=160.0 {cid} 应已退场")
    print("t=160.0 ✓ 结论卡一，双人已退场")
    print("PASS 第三幕全剧本探针")
    app.exit(0)


QTimer.singleShot(4000, wait_spine)
QTimer.singleShot(180000, lambda: fail("总超时"))
sys.exit(app.exec())
