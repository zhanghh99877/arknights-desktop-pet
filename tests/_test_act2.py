"""第二幕（套消息第二幕）全剧本探针验证（不导出）。

按时间轴断言：标题卡、缪缪走入、可露希尔潜行、开口要内幕、装傻、
红包飞递 + 收红包、耳语 + 侧耳、转身离场、决意、结论大字卡。
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

PROJ = "套消息第二幕"


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
    fail(f"项目 {PROJ} 不存在，先跑 tools/gen_scene_act2.py")
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


def wait_spine():
    def got(snap):
        actors = {a["id"]: a for a in snap.get("actors", [])}
        if not all(actors.get(k, {}).get("ready") for k in ("mlyu", "click")):
            QTimer.singleShot(700, wait_spine)
            return
        print("缪缪与可露希尔骨架就绪")
        probe_at(1.0, check_title)
    probe_at(0.1, got)


def check_title(snap):
    """t=1.0：黑场标题卡；两人尚未出场。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    if len(actors) != len(proj.clips):
        fail(f"actor 数不对: {len(actors)} vs {len(proj.clips)}")
    if not in_window("title", 1.0):
        fail("t=1.0 标题卡应在窗内")
    for cid in ("mlyu", "click"):
        if in_window(cid, 1.0):
            fail(f"t=1.0 {cid} 不应在场（黑卡阶段）")
    print("t=1.0 ✓ 标题卡，人物未出场")
    probe_at(3.5, check_enter)


def check_enter(snap):
    """t=3.5：缪缪走入中，可露希尔潜行中。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m, c = actors["mlyu"], actors["click"]
    if m.get("anim") != "Move":
        fail(f"t=3.5 缪缪应在走入（Move），实际 {m.get('anim')}")
    if c.get("proc") != "潜行":
        fail(f"t=3.5 可露希尔应在「潜行」，实际 proc={c.get('proc')}")
    if not (250 < (m.get("skelX") or 0) < 460):
        fail(f"t=3.5 缪缪走入位置不对: skelX={m.get('skelX')}")
    if not in_window("tv_screen", 3.5):
        fail("t=3.5 行情电视应在窗内")
    print(f"t=3.5 ✓ 双人入场（缪缪 skelX={m['skelX']:.0f}，可露希尔潜行）")
    probe_at(8.5, check_ask)


def check_ask(snap):
    """t=8.5：开口要内幕。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    c = actors["click"]
    if c.get("anim") != "Default":
        fail(f"t=8.5 可露希尔应站定（Default），实际 {c.get('anim')}")
    if not in_window("bub0", 8.5):
        fail("t=8.5 要内幕台词应在窗内")
    print("t=8.5 ✓ 开口要内幕")
    probe_at(12.5, check_silly)


def check_silly(snap):
    """t=12.5：缪缪装傻 + 冷汗。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m = actors["mlyu"]
    if m.get("proc") != "装傻":
        fail(f"t=12.5 缪缪应在「装傻」，实际 proc={m.get('proc')}")
    if not in_window("bub1", 12.5) or not in_window("emo0", 12.5):
        fail("t=12.5 装傻台词/冷汗应在窗内")
    print("t=12.5 ✓ 装傻 + 冷汗")
    probe_at(16.0, check_gift)


def check_gift(snap):
    """t=16.0：红包飞行途中；t=16.5 抓夹收下。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m = actors["mlyu"]
    if m.get("proc") != "装傻":
        fail(f"t=16.0 缪缪应在「装傻」（红包在途），实际 proc={m.get('proc')}")
    if not in_window("envelope", 16.0):
        fail("t=16.0 红包应在飞行窗内")
    print("t=16.0 ✓ 红包飞递中")
    probe_at(16.5, check_grab)


def check_grab(snap):
    """t=16.5：收红包抢夹（闪白帧卡在 16.7-16.78）。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m = actors["mlyu"]
    if m.get("proc") != "收红包":
        fail(f"t=16.5 缪缪应在「收红包」，实际 proc={m.get('proc')}")
    if not (16.5 < CLIPS["flash1"].start < 17.0):
        fail(f"得手闪白帧位置不对: {CLIPS['flash1'].start}")
    print("t=16.5 ✓ 收红包 + 得手闪白")
    probe_at(20.5, check_whisper)


def check_whisper(snap):
    """t=20.5：耳语 + 侧耳 + 交底台词。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m, c = actors["mlyu"], actors["click"]
    if m.get("proc") != "耳语":
        fail(f"t=20.5 缪缪应在「耳语」，实际 proc={m.get('proc')}")
    if c.get("proc") != "侧耳":
        fail(f"t=20.5 可露希尔应在「侧耳」，实际 proc={c.get('proc')}")
    if not in_window("bub2", 20.5):
        fail("t=20.5 交底台词应在窗内")
    print("t=20.5 ✓ 耳语 + 侧耳 + 交底")
    probe_at(24.8, check_exit)


def check_exit(snap):
    """t=24.8：缪缪转身离场，可露希尔决意。"""
    actors = {a["id"]: a for a in snap.get("actors", [])}
    m, c = actors["mlyu"], actors["click"]
    if m.get("anim") != "Move":
        fail(f"t=24.8 缪缪应在离场（Move），实际 {m.get('anim')}")
    if (m.get("skelX") or 0) > 400:
        fail(f"t=24.8 缪缪应已在左行途中: skelX={m.get('skelX')}")
    if c.get("proc") != "决意":
        fail(f"t=24.8 可露希尔应在「决意」，实际 proc={c.get('proc')}")
    if not in_window("bub3", 24.8):
        fail("t=24.8 得手台词应在窗内")
    print(f"t=24.8 ✓ 缪缪离场 skelX={m['skelX']:.0f} + 可露希尔决意")
    probe_at(29.0, check_concl)


def check_concl(snap):
    """t=29.0：结论大字卡，两人均已退场。"""
    if not in_window("concl", 29.0):
        fail("t=29.0 结论卡应在窗内")
    for cid in ("mlyu", "click"):
        if CLIPS[cid].end > 29.0:
            fail(f"t=29.0 {cid} 应已退场")
    print("t=29.0 ✓ 结论大字卡，双人已退场")
    print("PASS 第二幕全剧本探针")
    app.exit(0)


QTimer.singleShot(4000, wait_spine)
QTimer.singleShot(120000, lambda: fail("总超时"))
sys.exit(app.exec())
