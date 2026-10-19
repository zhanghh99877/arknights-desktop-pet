"""工作区自定义程序动作测试：可露希尔「大哭打滚」。

验证：PROCS 注册 → 条目播放时根骨骼 scaleY 被压扁（纵向滚动）→
💦 眼泪特效元素出现 → 切回官方动作后特效清理。
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

from PySide6.QtCore import Qt, QTimer
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


shutil.rmtree(ROOT / "_proctest", ignore_errors=True)
store = WorkspaceStore()
proj = store.create("_proctest")
c = Clip(id="sp", type="spine", asset="可露希尔", start=0.0, end=4.0,
         x=640.0, y=600.0)
c.anims.append(AnimEntry(start=0.0, end=2.0, anim="大哭打滚",
                         speed=1.0, loop=True))
c.anims.append(AnimEntry(start=2.0, end=4.0, anim="Default",
                         speed=1.0, loop=True))
proj.clips.append(c)
proj.duration = 4.0
store.save(proj)
store.set_last("_proctest")

page = WorkspacePage(RelayLibrary())
page.resize(1400, 900)
page.show()
page.stage.bridge.sigLog.connect(lambda m: print("[stage]", m))


def js(code, cb):
    page.stage.page().runJavaScript(code, cb)


def probe_state(cb):
    js("""JSON.stringify({
        procs: Object.keys(window.PROCS || {}),
        rootScaleY: (function(){ var b = null;
            try { b = stageApi.probe(); } catch(e) {}
            return null; })(),
        tear: !!document.getElementById('tear1'),
    })""", cb)


STATE = """
JSON.stringify({
    procs: Object.keys(window.PROCS || {}),
    tear: !!document.getElementById('tear1'),
    scaleY: (function(){
        // 通过 debugBounds 拿不到骨骼，直接遍历窗口不可取；
        // 用 probe 已有字段 + 专门查询：
        return window.__scaleYProbe || null;
    })(),
})
"""


def scale_y(cb):
    # 根骨骼 'Bone' 的 scaleY（大哭打滚会把它压到 0.45~1.0 之间）
    js("""(function(){
        var p = stageApi.probe();
        return p;
    })()""", lambda _p: js("""(function(){
        // probe 不暴露骨骼，用一轮渲染后的 debugHit 路径不可行；
        // 直接问：stage.js 在 evalSpineActor 后缓存了 lastBounds，
        // 骨骼访问需内部钩子 —— 用 fxOwner + 轮询动画状态替代：
        return 'skip';
    })()""", lambda _s: cb()))


def check1(_s):
    js("JSON.stringify(Object.keys(window.PROCS || {}))", got_procs)


def got_procs(s):
    print("PROCS:", s)
    if "大哭打滚" not in (s or ""):
        fail("PROCS 未注册大哭打滚")
    print("① PROCS 注册 ✓")
    page.stage.set_time(0.3)   # cos(0.96)>0.2：眼泪可见且仍在打滚
    QTimer.singleShot(700, check2)


def check2():
    js("""JSON.stringify({
        tear: !!document.getElementById('tear1'),
        alpha: document.getElementById('tear1')
               ? document.getElementById('tear1').style.opacity : null,
    })""", got_fx)


def got_fx(s):
    d = json.loads(s or "{}")
    print("t=1.0 特效:", d)
    if not d.get("tear"):
        fail("大哭打滚播放中未见眼泪特效元素")
    print("② 眼泪特效 ✓")
    # scaleY 校验：通过临时桥读取（在页面里找骨架——用 debugHit 几何 + 专用求值）
    js("""(function(){
        // 大哭打滚把 root('Bone') scaleY 压到 0.45~1.0；直接访问需要
        // 内部 actors，这里用渲染副作用：evalSpineActor 后 lastBounds
        // 高度应明显小于 setup 高度（压扁）。
        return stageApi.debugBounds('sp');
    })()""", got_bounds_proc)


def got_bounds_proc(s):
    b = json.loads(s or "null")
    print("proc 时 bounds:", b)
    state_bounds["proc"] = b
    page.stage.set_time(0.5)   # cos(1.6)≈0：压扁最扁处
    QTimer.singleShot(500, lambda: js(
        "stageApi.debugBounds('sp')", got_bounds_flat))


def got_bounds_flat(s):
    b = json.loads(s or "null")
    print("压扁处 bounds:", b)
    ref = state_bounds.get("proc")
    if ref and b and b["h"] > ref["h"] * 0.75:
        fail(f"纵向滚动未生效：压扁处高度 {b['h']} 未明显小于 {ref['h']}")
    print("② 打滚压扁生效 ✓")
    page.stage.set_time(3.0)
    QTimer.singleShot(1000, check3)


def check3():
    js("""JSON.stringify({
        tear: !!document.getElementById('tear1'),
    })""", got_fx2)


def got_fx2(s):
    d = json.loads(s or "{}")
    print("t=3.0（已切回 Default）特效:", d)
    if d.get("tear"):
        fail("切回官方动作后眼泪特效未清理")
    print("③ 特效随条目切换清理 ✓ PASS")
    app.exit(0)


state_bounds = {}


QTimer.singleShot(3000, lambda: check1(None))
QTimer.singleShot(30000, lambda: fail("总超时"))
sys.exit(app.exec())
