"""生成工作区动画项目「缪缪的分身大作战」：缪缪2号职场喜剧番外（≈47.5s）。

不用股票的原创小品，玩缪缪的水精灵设定（水利己体=官方设定）：
- 0-2.0    黑卡标题「番外 · 不是股票的那一集」
- 2.2-4.6  缪缪走进主任办公室；5.0 电话突响（吓一跳）
- 7.2-9.2  盯着文件山冒汗：「这么多活儿……」→ 💡 →「得意」
- 11.5-14.4 「施法」召唤：脚下水纹法阵旋开，三个半透明水分身
           依次蹦出（12.0/12.8/13.6，opacity 0.62 + 💦）
- 14-22   分工蒙太奇（真身走去右侧垫子躺平 Sleep + 💤）：
           分身A 右移给大绿植「浇水」（掌心渗水，水精灵不用壶）
           分身B 冲到桌前「狂签」，签完的纸飞向右缘
           分身C 走到座机前「耳语」通话 📞
- 21.2-22.0 白板三个待办格依次打 ✓；时钟 9:00 → 11:20
- 25.5-28  任务完成，水分身达到维持极限：抖两下 → 💦 → 瘫成一滩水
- 32.8-36.8 真身睡醒，散步把三滩水挨个「收」回体内（💧）
- 37-39.6 「得意」：「一滴都没剩。」（活儿没了，水也没了）
- 40.2-41.6 电话又响（吓一跳）→ 42.0 「施法」再召 → 44.0 硬切结论卡
           「活儿不会少，/ 但缪缪可以多。」

图层语义：正图层（背景/桌/垫/法阵/水滩/纸/钟针/✓）= 基础世界，永远在
人物之下；负图层 spine（真身+分身）= 顶层世界；气泡/emoji/黑卡 = 负图层
SVG → overlayTop，压住一切 spine。
"""
from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

PRTS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRTS_ROOT))
sys.path.insert(0, str(PRTS_ROOT / "tools"))

from core.workspace import AnimEntry, Clip, MoveEntry, Project, WorkspaceStore  # noqa: E402
import gen_scene_act1 as A1  # noqa: E402  （svg_doc/txt/大字卡/气泡）

SCENE = "缪缪的分身大作战"

# ---- 时间轴（秒） ----
T_TITLE_END = 2.0
M_WALK0, M_ARRIVE = 2.2, 4.6        # 缪缪走入
T_RING1_0, T_RING1_1 = 5.0, 6.4     # 电话响一
T_SCARE1_0, T_SCARE1_1 = 5.2, 6.6   # 吓一跳
T_CAST0, T_CAST1 = 11.5, 14.4       # 施法一
CA_POP, CB_POP, CC_POP = 12.0, 12.8, 13.6   # 分身蹦出（错峰出生+错峰出发）
T_MAT0, T_MAT1 = 14.4, 15.6         # 真身去垫子躺平
T_SLEEP_END = 32.8                  # 睡醒
CA_WALK0, CA_ARR = 12.6, 13.8       # 分身A 先走（给 B 腾出出生点）
CA_WATER0, CA_WATER1 = 14.2, 20.8
CB_WALK0, CB_ARR = 13.6, 15.2       # 分身B 狂签
CB_SIGN0, CB_SIGN1 = 15.6, 21.0
CC_WALK0, CC_ARR = 14.6, 16.2       # 分身C 电话
CC_CALL0, CC_CALL1 = 16.6, 21.4
CK = (20.8, 21.0, 21.4)             # 白板 ✓
CA_END, CB_END, CC_END = 26.0, 27.0, 27.8   # 蒸发时刻
PA_END, PB_END, PC_END = 35.1, 36.5, 37.1   # 水滩被收回
T_WAKE = 32.8
T_ABSORB0, T_ABSORB1 = 33.6, 36.8   # 收水散步
T_PROUD0, T_PROUD1 = 37.0, 39.6     # 得意
T_RING2_0, T_RING2_1 = 40.2, 41.6
T_SCARE2_0, T_SCARE2_1 = 40.4, 41.8
T_CAST2_0, T_CAST2_1 = 42.0, 44.0   # 施法二（再召）
T_CARD = 44.0
T_END = 47.5

FEET_Y = 660
M_X = 620.0                          # 真身主站位
SCALE = 0.75
MAT = (280.0, 648.0)                 # 午睡垫（真身睡 MAT+30）
DESK = (965.0, 570.0)                # 办公桌
PHONE = (1085.0, 470.0)              # 座机
PLANT = (670.0, 560.0)               # 大绿植（分身A的浇水对象）
CLOCK = (900.0, 95.0)                # 挂钟
CA_X, CB_X, CC_X = 560.0, 870.0, 1000.0     # 分身工位
TEAL = "#2ec4b6"
RIN = "#35b8a0"


def make_scene_png(path: Path):
    """清晨主任办公室：大窗晨光、白板待办、挂钟、木地板。"""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QImage, QLinearGradient, \
        QPainter, QPen

    img = QImage(1280, 720, QImage.Format.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    def pen(c, w=3):
        p.setPen(QPen(QColor(c), w, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

    def rrect(x, y, w, h, fill, line=None, r=10, lw=3):
        pen(line or fill, lw)
        p.setBrush(QColor(fill))
        p.drawRoundedRect(QRectF(x, y, w, h), r, r)

    # 冷调晨光墙
    wall = QLinearGradient(0, 0, 0, 720)
    wall.setColorAt(0, QColor("#f2f5f8"))
    wall.setColorAt(1, QColor("#dfe7ef"))
    p.fillRect(0, 0, 1280, 720, QBrush(wall))

    # 大窗：蓝天晨光 + 云
    rrect(200, 80, 460, 320, "#bfe3f7", "#9fb4c8", 16, 8)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffffff"))
    for cx, cy, rx, ry in ((300, 180, 64, 22), (420, 240, 84, 26),
                           (560, 160, 58, 20), (350, 320, 70, 22),
                           (520, 330, 56, 18)):
        p.drawEllipse(QPointF(cx, cy), rx, ry)
    p.setBrush(QColor(255, 236, 170, 180))
    p.drawEllipse(QPointF(600, 130), 40, 40)
    pen("#9fb4c8", 6)
    p.drawLine(430, 84, 430, 396)
    p.drawLine(204, 240, 656, 240)

    # 挂钟（针是独立片段）
    p.setBrush(QColor("#ffffff"))
    pen("#8fa6bc", 6)
    p.drawEllipse(QPointF(CLOCK[0], CLOCK[1]), 46, 46)
    pen("#b9c9d8", 3)
    for k in range(12):
        a = math.pi / 6 * k
        p.drawLine(int(CLOCK[0] + 38 * math.sin(a)),
                   int(CLOCK[1] - 38 * math.cos(a)),
                   int(CLOCK[0] + 43 * math.sin(a)),
                   int(CLOCK[1] - 43 * math.cos(a)))

    # 白板：三个待办格（简笔画：浇水/文件/电话）
    rrect(790, 140, 220, 180, "#fdfefe", "#8fa6bc", 10, 6)
    for bx in (805, 872, 939):
        rrect(bx, 160, 56, 60, "#f2f7fa", "#c3d3e0", 6, 2.5)
    pen("#7fa8c9", 2.6)
    p.drawRect(QRectF(824, 196, 18, 12))            # 盆栽
    p.drawLine(833, 196, 833, 180)
    p.drawEllipse(QPointF(826, 178), 6, 5)
    p.drawEllipse(QPointF(840, 178), 6, 5)
    p.drawRect(QRectF(884, 176, 30, 26))            # 文件
    for ly in (183, 190, 197):
        p.drawLine(889, ly, 909, ly)
    p.drawRect(QRectF(951, 182, 32, 20))            # 电话
    p.drawEllipse(QPointF(960, 176), 8, 6)
    p.drawEllipse(QPointF(974, 176), 8, 6)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#c3d3e0"))
    p.drawRect(QRectF(860, 306, 80, 7))

    # 墙牌（环境文字）
    p.setPen(QColor("#5f7f96"))
    p.setFont(QFont("Microsoft YaHei", 12, 700))
    p.drawText(QRectF(1040, 78, 220, 24), Qt.AlignmentFlag.AlignLeft |
               Qt.AlignmentFlag.AlignVCenter, "RHINE LIFE")
    p.setFont(QFont("Microsoft YaHei", 8))
    p.setPen(QColor("#93aebb"))
    p.drawText(QRectF(1042, 102, 220, 16), Qt.AlignmentFlag.AlignLeft |
               Qt.AlignmentFlag.AlignVCenter, "生态科 · 主任办公室")

    # 木地板
    floor = QLinearGradient(0, 620, 0, 720)
    floor.setColorAt(0, QColor("#dcbc90"))
    floor.setColorAt(1, QColor("#c8a678"))
    p.fillRect(0, 620, 1280, 100, QBrush(floor))
    pen("#b5946a", 3)
    for x in range(140, 1280, 190):
        p.drawLine(x, 640, x - 64, 718)
    p.setPen(QPen(QColor("#a8875e"), 4))
    p.drawLine(0, 620, 1280, 620)

    p.end()
    img.save(str(path), "PNG")


# ================= 素材 =================
def _emo(ch: str, size: float, box: int = 120) -> str:
    return A1.svg_doc(box, box, A1.txt(box / 2, box / 2 + size * 0.36, ch,
                                       size, "#33415c", "middle"))


def build_desk() -> str:
    """办公桌：桌面 + 前板 + 文件山（立在桌面）+ 台灯。局部 y=18 为桌面。"""
    b = [f'<rect x="2" y="18" width="396" height="26" rx="8" fill="#a9784f" '
         f'stroke="#8a6a44" stroke-width="4"/>',
         f'<rect x="30" y="44" width="340" height="142" rx="6" fill="#b98a5e" '
         f'stroke="#9c7248" stroke-width="4"/>',
         f'<rect x="30" y="44" width="340" height="16" fill="#c99b6e"/>']
    # 文件山（x 48-116，底在桌面 local y=18，向上叠 5 张）
    for dx, dy, rot in ((0, 0, -3), (4, -9, 2), (-3, -18, -2),
                        (5, -27, 3), (-2, -36, -4)):
        x, y = 48 + dx, -26 + dy          # 纸高 44，底 y=-26 → 落在 18
        b.append(f'<g transform="rotate({rot} {x + 34} {y + 22})">'
                 f'<rect x="{x}" y="{y}" width="68" height="44" rx="3" '
                 f'fill="#ffffff" stroke="#c3d3e0" stroke-width="2"/>'
                 f'<line x1="{x + 8}" y1="{y + 12}" x2="{x + 60}" '
                 f'y2="{y + 12}" stroke="#dce8f2" stroke-width="2.5"/>'
                 f'<line x1="{x + 8}" y1="{y + 22}" x2="{x + 56}" '
                 f'y2="{y + 22}" stroke="#dce8f2" stroke-width="2.5"/>'
                 f'<line x1="{x + 8}" y1="{y + 32}" x2="{x + 60}" '
                 f'y2="{y + 32}" stroke="#dce8f2" stroke-width="2.5"/></g>')
    # 台灯（中部，底在桌面；右侧留给座机）
    b.append(f'<rect x="180" y="8" width="44" height="10" rx="4" '
             f'fill="#2e8f7f"/>' +
             f'<path d="M 202 12 L 186 -14" stroke="#2e8f7f" '
             f'stroke-width="6" stroke-linecap="round"/>' +
             f'<path d="M 168 -10 L 196 -22 L 192 -4 Z" fill="{RIN}" '
             f'stroke="#2e8f7f" stroke-width="3"/>')
    return A1.svg_doc(400, 190, "".join(b))


def build_phone() -> str:
    return A1.svg_doc(96, 78,
        f'<rect x="8" y="26" width="80" height="42" rx="10" fill="#3c5a74" '
        f'stroke="#2c4254" stroke-width="3.5"/>' +
        f'<rect x="16" y="34" width="26" height="10" rx="4" fill="#5f8fb0"/>' +
        f'<rect x="10" y="8" width="76" height="16" rx="8" fill="#2c4254"/>' +
        f'<path d="M 84 66 q 10 4 6 10" fill="none" stroke="#2c4254" '
        f'stroke-width="3"/>')


def build_mat() -> str:
    return A1.svg_doc(300, 92,
        f'<rect x="4" y="30" width="292" height="52" rx="20" fill="#ffd9a8" '
        f'stroke="#e0b078" stroke-width="4"/>' +
        f'<rect x="196" y="16" width="92" height="34" rx="14" fill="#ffffff" '
        f'stroke="#e0d0b8" stroke-width="3.5"/>')


def build_plant() -> str:
    """地面大绿植：宽冠龟背竹（分身A 掌心渗水的对象）。"""
    b = [f'<path d="M 128 138 L 168 138 L 160 196 Q 159 204 151 204 '
         f'L 145 204 Q 137 204 136 196 Z" fill="#c97b4a" '
         f'stroke="#a85c34" stroke-width="4"/>',
         f'<rect x="120" y="122" width="56" height="20" rx="9" '
         f'fill="#d98d58" stroke="#a85c34" stroke-width="4"/>',
         f'<path d="M 148 122 C 148 84 146 52 142 24" fill="none" '
         f'stroke="#4f9e5f" stroke-width="6" stroke-linecap="round"/>',
         f'<path d="M 147 78 C 124 72 106 56 98 34" fill="none" '
         f'stroke="#4f9e5f" stroke-width="5" stroke-linecap="round"/>',
         f'<path d="M 146 48 C 172 44 192 30 200 10" fill="none" '
         f'stroke="#4f9e5f" stroke-width="5" stroke-linecap="round"/>']
    for cx, cy, r, rot in ((92, 26, 30, -28), (206, 2, 30, 26),
                           (148, 6, 32, 0), (118, 62, 22, -48),
                           (182, 52, 20, 42), (62, 52, 20, -60)):
        b.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r * 0.62}" '
                 f'fill="#57b98a" stroke="#3f8f6a" stroke-width="3" '
                 f'transform="rotate({rot} {cx} {cy})"/>')
    return A1.svg_doc(250, 210, "".join(b))


def build_hand(color: str, length: int) -> str:
    return A1.svg_doc(26, length,
        f'<line x1="13" y1="{length / 2}" x2="13" y2="4" stroke="{color}" '
        f'stroke-width="6" stroke-linecap="round"/>')


def build_check() -> str:
    return A1.svg_doc(60, 60,
        f'<path d="M 12 32 L 26 46 L 50 14" fill="none" stroke="#2eb872" '
        f'stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>')


def build_circle() -> str:
    """水纹法阵：双环 + 水滴刻度，绕中心旋转。"""
    b = [f'<circle cx="140" cy="140" r="128" fill="none" stroke="{TEAL}" '
         f'stroke-width="5" stroke-dasharray="18 12" opacity="0.85"/>',
         f'<circle cx="140" cy="140" r="96" fill="none" stroke="{TEAL}" '
         f'stroke-width="3" opacity="0.7"/>',
         f'<circle cx="140" cy="140" r="40" fill="rgba(46,196,182,0.18)" '
         f'stroke="{TEAL}" stroke-width="2.5" opacity="0.8"/>']
    for k in range(8):
        a = math.pi / 4 * k
        b.append(A1.txt(140 + 112 * math.sin(a), 140 - 112 * math.cos(a) + 7,
                        "💧", 22, "#33415c", "middle"))
    b.append(f'<path d="M 140 112 L 158 148 L 122 148 Z" fill="{TEAL}" '
             f'opacity="0.75"/>')
    return A1.svg_doc(280, 280, "".join(b))


def build_puddle() -> str:
    return A1.svg_doc(150, 40,
        f'<ellipse cx="75" cy="24" rx="68" ry="12" fill="#8fd0e8" '
        f'stroke="#5fb6d8" stroke-width="3"/>' +
        f'<ellipse cx="60" cy="21" rx="30" ry="6" fill="#c8ecf8"/>')


def build_paper() -> str:
    return A1.svg_doc(76, 56,
        f'<rect x="3" y="3" width="70" height="50" rx="4" fill="#ffffff" '
        f'stroke="#c3d3e0" stroke-width="2.5"/>' +
        f'<line x1="12" y1="16" x2="64" y2="16" stroke="#dce8f2" '
        f'stroke-width="3"/>' +
        f'<line x1="12" y1="27" x2="58" y2="27" stroke="#dce8f2" '
        f'stroke-width="3"/>' +
        f'<line x1="12" y1="38" x2="64" y2="38" stroke="#dce8f2" '
        f'stroke-width="3"/>' +
        f'<circle cx="56" cy="40" r="9" fill="none" stroke="#e05252" '
        f'stroke-width="2.5" opacity="0.8"/>')


# ================= 装配 =================
def build():
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        QGuiApplication([])              # QImage/QPainter 需要实例（无窗口）
    store = WorkspaceStore()
    shutil.rmtree(store.root / SCENE, ignore_errors=True)
    proj = store.create(SCENE)
    assets = store.assets_dir(SCENE)
    make_scene_png(assets / "scene_bg.png")

    def put(name: str, body: str):
        (assets / name).write_text(body, encoding="utf-8")

    put("title.svg", A1.build_card([
        ("番外 · 不是股票的那一集", 30, 302, "#9aa3b2", 2),
        ("缪缪的分身大作战", 108, 432, "#ffffff", 8)]))
    put("concl.svg", A1.build_card([
        ("活儿不会少，", 84, 330, "#ffffff", 6),
        ("但缪缪可以多。", 84, 470, "#ffffff", 6)]))
    put("desk.svg", build_desk())
    put("phone.svg", build_phone())
    put("mat.svg", build_mat())
    put("plant.svg", build_plant())
    put("handM.svg", build_hand("#4a5a6e", 78))
    put("handH.svg", build_hand("#4a5a6e", 60))
    put("check.svg", build_check())
    put("circle.svg", build_circle())
    put("puddle.svg", build_puddle())
    put("paper.svg", build_paper())
    put("emo_sweat.svg", _emo("💦", 74))
    put("emo_idea.svg", _emo("💡", 72))
    put("emo_zzz.svg", _emo("💤", 66))
    put("emo_call.svg", _emo("📞", 56, 96))
    put("emo_pop.svg", _emo("💦", 92, 130))
    put("emo_drop.svg", _emo("💧", 52, 90))
    speech = [
        ("bub0.svg", "这么多活儿……", TEAL),
        ("bub1.svg", "一滴都没剩。", TEAL),
    ]
    for fn, text, color in speech:
        put(fn, A1.build_speech(text, color))

    def mk(cid, asset, name, layer, start, end, x, y, moves=(),
           rotation=0.0, scale=1.0, kind="svg", opacity=1.0):
        return Clip(id=cid, type=kind, asset=asset, name=name, layer=layer,
                    start=round(start, 2), end=round(end, 2), x=x, y=y,
                    scale=scale, rotation=rotation, opacity=opacity,
                    moves=list(moves))

    def wobble(x, y, s, e, amp, hz, base=0.0):
        """绕中心 rot 摆动条目，收尾归位到 base。"""
        dur = e - s
        n = max(4, int(dur * hz * 2))
        moves = []
        for k in range(n):
            ta = round(s + dur * k / n, 3)
            tb = round(s + dur * (k + 1) / n, 3)
            aa = base + amp * (1 if k % 2 == 0 else -1)
            ab = base + amp * (1 if (k + 1) % 2 == 0 else -1)
            moves.append(MoveEntry(ta, tb, x, y, x, y, aa, ab))
        moves.append(MoveEntry(round(e - 0.04, 3), e, x, y, x, y,
                               moves[-1].rot1, base))
        return moves

    def bob_moves(x, y, s, e, swing=10.0, rot=4.0):
        """漂浮循环：上下浮 + 微转。"""
        moves = []
        n = max(4, int((e - s) / 2.6))
        span = (e - s) / n
        for k in range(n):
            dy = -swing if k % 2 == 0 else swing
            y0 = y if k == 0 else moves[-1].y1
            moves.append(MoveEntry(round(s + span * k, 2),
                                   round(s + span * (k + 1), 2),
                                   x, y0, x, y + dy,
                                   moves[-1].rot1 if k else 0.0,
                                   rot if k % 2 == 0 else -rot))
        return moves

    clips = [
        mk("scene_bg", "scene_bg.png", "场景", 7, 0, T_END, 640, 360,
           kind="png"),
        mk("desk", "desk.svg", "办公桌", 6, 0, T_END, DESK[0], DESK[1]),
        mk("mat", "mat.svg", "午睡垫", 6, 0, T_END, MAT[0], MAT[1]),
        mk("plant", "plant.svg", "绿植", 6, 0, T_END, PLANT[0], PLANT[1]),
        # 挂钟 9:00 → 11:20（分针 2.33 圈）
        mk("handM", "handM.svg", "分针", 6, 0, T_END, CLOCK[0], CLOCK[1],
           moves=[MoveEntry(14.5, 44.0, CLOCK[0], CLOCK[1], CLOCK[0],
                            CLOCK[1], 0.0, 840.0)]),
        mk("handH", "handH.svg", "时针", 6, 0, T_END, CLOCK[0], CLOCK[1],
           moves=[MoveEntry(14.5, 44.0, CLOCK[0], CLOCK[1], CLOCK[0],
                            CLOCK[1], -90.0, -30.0)]),
        # 施法法阵 ×2（脚下旋开）
        mk("circle1", "circle.svg", "法阵一", 5, 11.7, 14.4, M_X, 640,
           moves=[MoveEntry(11.7, 12.0, M_X, 700, M_X, 640, 0.0, 40.0),
                  MoveEntry(12.0, 14.4, M_X, 640, M_X, 640, 40.0, 400.0)]),
        mk("circle2", "circle.svg", "法阵二", 5, 42.0, 44.0, CC_X, 640,
           moves=[MoveEntry(42.0, 42.3, CC_X, 700, CC_X, 640, 0.0, 40.0),
                  MoveEntry(42.3, 44.0, CC_X, 640, CC_X, 640, 40.0, 240.0)]),
        # 水滩 ×3（分身蒸发后留在工位）
        mk("puddleA", "puddle.svg", "水滩A", 5, 26.3, PA_END, CA_X, 648),
        mk("puddleB", "puddle.svg", "水滩B", 5, 27.3, PB_END, CB_X, 648),
        mk("puddleC", "puddle.svg", "水滩C", 5, 28.1, PC_END, CC_X, 648),
    ]
    # 签完飞出的文件 ×4（从文件山顶抛物线飞向右缘，越过 B 的头顶）
    for i, t0 in enumerate((16.6, 17.4, 18.2, 19.0)):
        clips.append(mk(f"paper{i}", "paper.svg", f"文件{i}", 4,
                        t0, round(t0 + 1.5, 2), 845, 428,
                        moves=[MoveEntry(t0, round(t0 + 0.45, 2), 845, 428,
                                         905, 358, -16.0, 34.0),
                               MoveEntry(round(t0 + 0.45, 2), round(t0 + 1.3, 2),
                                         905, 358, 1300, 385, 34.0, 62.0)]))
    # 白板 ✓ ×3（打上后一直保留到黑卡）
    for i, (t0, bx) in enumerate(zip(CK, (833, 900, 967))):
        clips.append(mk(f"ck{i}", "check.svg", f"待办✓{i}", 6, t0,
                        T_CARD, bx, 190, scale=0.9,
                        moves=[MoveEntry(t0, round(t0 + 0.3, 2), bx, 204,
                                         bx, 190, 10.0, -4.0)]))
    # 座机：待机 → 响一 → 安静 → 摔歪 → 响二（歪着抖）
    phone_moves = [MoveEntry(0, T_RING1_0, PHONE[0], PHONE[1], PHONE[0],
                             PHONE[1], 0.0, 0.0)]
    phone_moves += wobble(PHONE[0], PHONE[1], T_RING1_0, T_RING1_1, 8.0, 8.0)
    phone_moves += [MoveEntry(T_RING1_1, 28.0, PHONE[0], PHONE[1], PHONE[0],
                              PHONE[1], 0.0, 0.0)]
    phone_moves += wobble(PHONE[0], PHONE[1], 28.0, 29.0, 4.0, 5.0)
    phone_moves += [MoveEntry(29.0, 29.6, PHONE[0], PHONE[1], PHONE[0],
                              PHONE[1], 0.0, 14.0)]        # 话筒歪掉不归位
    phone_moves += wobble(PHONE[0], PHONE[1], T_RING2_0, T_RING2_1, 10.0, 8.0,
                          base=14.0)
    phone_moves += [MoveEntry(T_RING2_1, T_END, PHONE[0], PHONE[1], PHONE[0],
                              PHONE[1], 14.0, 14.0)]
    clips.append(mk("phone", "phone.svg", "座机", 6, 0, T_END,
                    PHONE[0], PHONE[1], moves=phone_moves))
    # 📞 emoji：响一 / 通话 / 响二
    clips.append(mk("call1", "emo_call.svg", "📞响一", -4, T_RING1_0,
                    T_RING1_1, PHONE[0], PHONE[1] - 62,
                    moves=wobble(PHONE[0], PHONE[1] - 62, T_RING1_0,
                                 T_RING1_1, 6.0, 7.0)))
    clips.append(mk("call2", "emo_call.svg", "📞通话", -4, CC_CALL0,
                    CC_CALL1, PHONE[0], PHONE[1] - 62,
                    moves=bob_moves(PHONE[0], PHONE[1] - 62, CC_CALL0,
                                    CC_CALL1, swing=6.0, rot=3.0)))
    clips.append(mk("call3", "emo_call.svg", "📞响二", -4, T_RING2_0,
                    T_RING2_1, PHONE[0], PHONE[1] - 62,
                    moves=wobble(PHONE[0], PHONE[1] - 62, T_RING2_0,
                                 T_RING2_1, 7.0, 7.0)))
    # 情绪 emoji
    clips.append(mk("sweat", "emo_sweat.svg", "💦愁", -4, 7.2, 8.8, 660, 300,
                    moves=wobble(660, 300, 7.2, 8.8, 5.0, 4.0)))
    clips.append(mk("idea", "emo_idea.svg", "💡", -4, 9.6, 10.5, 660, 296,
                    moves=[MoveEntry(9.6, 9.9, 660, 320, 660, 296, 8.0, -3.0)]))
    clips.append(mk("zzz", "emo_zzz.svg", "💤", -4, 16.0, 32.0, 360, 470,
                    moves=bob_moves(360, 470, 16.0, 32.0)))
    # 分身蹦出 💦（出生点）+ 蒸发 💦（工位上化作水滩前）
    for cid, t0, cx in (("popA", CA_POP, 380.0), ("popB", CB_POP, 460.0),
                        ("popC", CC_POP, 540.0)):
        clips.append(mk(cid, "emo_pop.svg", f"💦{cid}", -4, t0,
                        round(t0 + 0.6, 2), cx, 430,
                        moves=[MoveEntry(t0, round(t0 + 0.25, 2), cx, 452,
                                         cx, 430, 10.0, -4.0)]))
    for cid, t0, cx in (("evapA", CA_END, CA_X), ("evapB", CB_END, CB_X),
                        ("evapC", CC_END, CC_X)):
        clips.append(mk(cid, "emo_pop.svg", f"💦{cid}", -4, t0,
                        round(t0 + 0.7, 2), cx, 490,
                        moves=[MoveEntry(t0, round(t0 + 0.3, 2), cx, 512,
                                         cx, 490, 10.0, -4.0)]))
    # 收水 💧 ×3（对应散步 310→1020 时经过各水滩的时刻）
    for cid, t0, px in (("dropA", 34.7, CA_X), ("dropB", 36.1, CB_X),
                        ("dropC", 36.7, CC_X)):
        clips.append(mk(cid, "emo_drop.svg", f"💧{cid}", -4, t0,
                        round(t0 + 0.55, 2), px, 600,
                        moves=[MoveEntry(t0, round(t0 + 0.3, 2), px, 624,
                                         px, 600, 6.0, -3.0)]))
    # 台词气泡
    for cid, s, e, hx in (("bub0", 7.6, 9.2, M_X), ("bub1", 37.6, 39.4, CC_X)):
        text = next(t for fn, t, _c in speech if fn == f"{cid}.svg")
        w = max(130, 44 + int(len(text) * 17.2))
        cx = round(hx + 0.15 * w, 1)
        clips.append(mk(cid, f"{cid}.svg", f"台词{cid}", -4, s, e, cx, 320,
                        rotation=-1.5,
                        moves=[MoveEntry(s, s + 0.35, cx, 300, cx, 320,
                                         5.0, -1.5)]))

    # ---- 分身工厂：半透明水分身（蹦出 → 走位 → 干活 → 待机 → 蒸发） ----
    def clone(cid, name, t0, sx, work, walk0, arr, wx, end, walk_flip):
        wf = work[3]
        c = Clip(id=cid, type="spine", asset="缪缪2号", name=name,
                 layer=-1, start=t0, end=end, x=sx, y=570, scale=SCALE,
                 opacity=0.62)
        c.moves = [MoveEntry(t0, round(t0 + 0.3, 2), sx, 570, sx, FEET_Y)]
        c.moves.append(MoveEntry(walk0, arr, sx, FEET_Y, wx, FEET_Y))
        rots = [0.0, 7.0, -7.0, 5.0, -4.0, 0.0]      # 蒸发前抖两下
        w0 = round(end - 0.5, 2)
        for k in range(5):
            c.moves.append(MoveEntry(round(w0 + 0.1 * k, 2),
                                     round(w0 + 0.1 * (k + 1), 2),
                                     wx, FEET_Y, wx, FEET_Y,
                                     rots[k], rots[k + 1]))
        c.anims = [
            AnimEntry(t0, walk0, "Default", 1.0, True, wf),
            AnimEntry(walk0, round(arr - 0.2, 2), "Move", 1.0, True,
                      walk_flip),
            AnimEntry(round(arr - 0.2, 2), work[0], "Default", 1.0, True, wf),
            AnimEntry(work[0], work[1], work[2], 1.0, True, wf),
            AnimEntry(work[1], w0, "Default", 1.0, True, wf),
        ]
        return c

    clips.append(clone("cA", "分身A", CA_POP, 380.0,
                       (CA_WATER0, CA_WATER1, "浇水", False),
                       CA_WALK0, CA_ARR, CA_X, CA_END, False))
    clips.append(clone("cB", "分身B", CB_POP, 440.0,
                       (CB_SIGN0, CB_SIGN1, "狂签", False),
                       CB_WALK0, CB_ARR, CB_X, CB_END, False))
    clips.append(clone("cC", "分身C", CC_POP, 500.0,
                       (CC_CALL0, CC_CALL1, "耳语", False),
                       CC_WALK0, CC_ARR, CC_X, CC_END, False))

    # ---- 真身：走入 → 吓 → 决意 → 施法 → 躺平 → 醒来收水 → 再施法 ----
    mlyu = Clip(id="mlyu", type="spine", asset="缪缪2号", name="缪缪",
                layer=-1, start=M_WALK0, end=T_CAST2_1, x=-160, y=FEET_Y,
                scale=SCALE)
    mlyu.moves = [
        MoveEntry(M_WALK0, M_ARRIVE, -160, FEET_Y, M_X, FEET_Y),
        MoveEntry(T_MAT0, T_MAT1, M_X, FEET_Y, MAT[0] + 30, FEET_Y),
        MoveEntry(T_ABSORB0, T_ABSORB1, MAT[0] + 30, FEET_Y, CC_X, FEET_Y),
    ]
    mlyu.anims = [
        AnimEntry(M_WALK0, M_ARRIVE, "Move", 1.0, True, False),
        AnimEntry(M_ARRIVE, T_SCARE1_0, "Default", 1.0, True, False),
        AnimEntry(T_SCARE1_0, T_SCARE1_1, "吓一跳", 1.0, True, False),
        AnimEntry(T_SCARE1_1, 9.8, "Default", 1.0, True, False),
        AnimEntry(9.8, 11.3, "得意", 1.0, True, False),
        AnimEntry(11.3, T_CAST0, "Default", 1.0, True, False),
        AnimEntry(T_CAST0, T_CAST1, "施法", 1.0, True, False),
        AnimEntry(T_CAST1, T_MAT0, "Default", 1.0, True, False),
        AnimEntry(T_MAT0, T_MAT1, "Move", 1.0, True, True),
        AnimEntry(T_MAT1, 15.8, "Default", 1.0, True, True),
        AnimEntry(15.8, T_SLEEP_END, "Sleep", 1.0, True, True),
        AnimEntry(T_SLEEP_END, T_ABSORB0, "Default", 1.0, True, True),
        AnimEntry(T_ABSORB0, T_ABSORB1, "Move", 1.15, True, False),
        AnimEntry(T_ABSORB1, T_PROUD0, "Default", 1.0, True, False),
        AnimEntry(T_PROUD0, T_PROUD1, "得意", 1.0, True, False),
        AnimEntry(T_PROUD1, T_SCARE2_0, "Default", 1.0, True, False),
        AnimEntry(T_SCARE2_0, T_SCARE2_1, "吓一跳", 1.0, True, False),
        AnimEntry(T_SCARE2_1, T_CAST2_0, "Default", 1.0, True, False),
        AnimEntry(T_CAST2_0, T_CAST2_1, "施法", 1.0, True, False),
    ]
    clips.append(mlyu)

    clips += [
        mk("title", "title.svg", "标题卡", -4, 0, T_TITLE_END, 640, 360),
        mk("concl", "concl.svg", "结论卡", -4, T_CARD, T_END, 640, 360),
    ]

    proj.canvas = {"w": 1280, "h": 720, "fps": 30, "bg": "#dfe7ef"}
    proj.duration = T_END
    proj.layers = 8
    proj.clips = clips
    store.save(proj)
    print(f"项目「{SCENE}」：总时长 {T_END}s，{len(clips)} 片段")
    print(f"  施法 {T_CAST0}s → 分身 {CA_POP}/{CB_POP}/{CC_POP}s；"
          f"蒸发 {CA_END}/{CB_END}/{CC_END}s；收水 {T_ABSORB0}-{T_ABSORB1}s；"
          f"结论卡 {T_CARD}s")


if __name__ == "__main__":
    build()
