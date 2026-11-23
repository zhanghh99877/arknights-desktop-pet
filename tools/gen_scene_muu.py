"""生成工作区动画项目「缪缪的花园」：缪缪2号单人番外（≈36s / 30fps）。

三幕剧的前日谈：缪缪的「内幕消息」从哪来——她给一盆挂着「莱茵生态」
铭牌的盆栽浇水，盆里长出来的东西是 K 线。
- 0-2.0    黑场硬切标题卡「番外 · 缪缪的花园」
- 2.2-5.2  缪缪2号走入温室办公室（面向右，去给招牌盆栽浇水）
- 5.6-8.4  「叉腰」检阅长势；台词「今天也要好好长哦。」
- 8.6-13.4 「浇水」：水壶架在手上，💧 三滴交错落进盆里
- 13.8-16.8 盆里冒芽：小芽 → K 线叶 → 成株（三段生长，从盆沿后升起）
- 17.2-21.0 「耳语」转身面向镜头交底：「莱茵生态，明天，必涨。」
           （与第二幕交底台词逐字对齐——源头闭环）
- 21.6-25.0 再浇一壶；25.2 成株拔高成「涨停株」：🚀 飞天 + 白卡
           「▲+10.01%」（第三幕那根涨停的来历）
- 25.4-28.4 「得意」；台词「养股票，跟养花一样嘛。」
- 28.4-31.2 哼着歌走人（左行出画）；31.6 硬切结论大字
           「所谓内幕，/ 就是有人替你浇过水。」

舞台：黄昏温室办公室（QPainter：拱窗晚霞、置物架、垂藤、木地板）。
台词气泡白底青边（缪缪色，同第二幕）；emoji/特效只留 emoji。
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
import gen_scene_act1 as A1  # noqa: E402  （复用 svg_doc/txt/大字卡/气泡）

SCENE = "缪缪的花园"

# ---- 时间轴（秒） ----
T_TITLE_END = 2.0
M_WALK0, M_ARRIVE = 2.2, 5.2        # 缪缪走入
T_ADMIRE0, T_ADMIRE1 = 5.6, 8.4     # 叉腰检阅
T_WATER1_0, T_WATER1_1 = 8.6, 13.4  # 浇水一
G1_0, G1_1, G1_2 = 13.8, 15.4, 16.8  # 芽→苗→成株
T_WHIS0, T_WHIS1 = 17.2, 21.0       # 耳语交底（对齐第二幕台词）
T_WATER2_0, T_WATER2_1 = 21.6, 25.0  # 浇水二
T_BIG = 25.2                        # 涨停株 + 🚀 + 徽章
T_PROUD_END = 28.4                  # 得意结束
M_EXIT0, M_EXIT1 = 28.4, 31.2       # 走人出画
T_CARD = 31.6                       # 结论卡
T_END = 36.0

FEET_Y = 660
M_X = 540.0                         # 缪缪站位（盆栽右侧偏左）
SCALE = 0.75
HEAD_Y = 360                        # 站立头部高度（气泡锚位）

# 盆栽几何（舞台坐标；素材中心锚）
STAND = (720.0, 628.0)              # 花架
POT = (720.0, 528.0)                # 盆（底落在花架台面上）
SOIL_Y = 496                        # 土面（芽的根）世界 y
CAN = (648.0, 446.0)                # 水壶（浇水时段浮在手上）
TEAL = "#2ec4b6"
RIN = "#35b8a0"


def make_scene_png(path: Path):
    """黄昏温室办公室：拱窗晚霞、两侧置物架、垂藤、木地板。"""
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

    # 暖色墙面
    wall = QLinearGradient(0, 0, 0, 720)
    wall.setColorAt(0, QColor("#f6e3c8"))
    wall.setColorAt(1, QColor("#eed3b2"))
    p.fillRect(0, 0, 1280, 720, QBrush(wall))

    # 大拱窗：晚霞天 + 逆光树影 + 斜阳（全部裁进拱形内）
    from PySide6.QtGui import QPainterPath
    arch = QPainterPath()
    arch.addRoundedRect(QRectF(300, 56, 560, 420), 210, 210)
    p.save()
    p.setClipPath(arch)
    sky = QLinearGradient(0, 60, 0, 470)
    sky.setColorAt(0, QColor("#ffdba6"))
    sky.setColorAt(0.6, QColor("#ffb37a"))
    sky.setColorAt(1, QColor("#f79d6c"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(sky))
    p.drawRect(300, 56, 560, 420)
    p.setBrush(QColor("#e88f60"))
    for cx, cy, rx in ((380, 430, 150), (620, 445, 190), (860, 425, 160)):
        p.drawEllipse(QPointF(cx, cy), rx, 110)
    p.setBrush(QColor("#d97f55"))
    for cx, cy, r in ((430, 330, 52), (520, 360, 40), (700, 340, 56),
                      (790, 370, 42), (760, 300, 34)):
        p.drawEllipse(QPointF(cx, cy), r, r * 0.85)
    # 落日
    p.setBrush(QColor("#ffd166"))
    p.drawEllipse(QPointF(640, 388), 44, 44)
    # 窗棂
    p.setBrush(QColor("#8a6a52"))
    for x in (420, 560, 700, 840):
        p.drawRect(QRectF(x, 60, 10, 412))
    p.drawRect(QRectF(304, 240, 552, 10))
    p.restore()
    pen("#7c5e48", 7)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(300, 56, 560, 420), 210, 210)

    # 垂藤（左上 / 右上）
    pen("#5f8f6a", 5)
    p.setBrush(QColor("#7fae8a"))
    for x0, x1, n in ((40, 210, 5), (1080, 1250, 5)):
        for k in range(n):
            xx = x0 + (x1 - x0) * k / max(1, n - 1)
            ln = 46 + 34 * ((k * 7) % 3)
            p.drawLine(int(xx), 0, int(xx), ln)
            p.drawEllipse(QPointF(xx, ln + 12), 16, 13)
            p.drawEllipse(QPointF(xx + 10, ln + 30), 11, 9)

    # 左右置物架（三层，摆盆栽）
    for sx, flip in ((0, 1), (1152, -1)):
        for li, sy in enumerate((180, 330, 480)):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#a9784f"))
            p.drawRect(QRectF(sx, sy, 128, 12))
            p.drawRect(QRectF(sx + 10, sy + 12, 9, 120 if li < 2 else 0))
            # 每层两小盆
            for k in range(2):
                bx = sx + 24 + k * 62
                by = sy - 26
                p.setBrush(QColor("#c97b4a"))
                p.drawRect(QRectF(bx, by + 8, 26, 20))
                p.setBrush(QColor(("#57b98a", "#79bd6c", "#4f9e7d")[(k + li) % 3]))
                p.drawEllipse(QPointF(bx + 13, by - 2), 15, 14)

    # 墙牌：RHINE LIFE（右下墙，避开垂藤与盆栽）
    p.setPen(QColor("#4a7a68"))
    p.setFont(QFont("Microsoft YaHei", 13, 700))
    p.drawText(QRectF(908, 486, 240, 26), Qt.AlignmentFlag.AlignLeft |
               Qt.AlignmentFlag.AlignVCenter, "RHINE LIFE")
    p.setFont(QFont("Microsoft YaHei", 8))
    p.setPen(QColor("#7d9a8b"))
    p.drawText(QRectF(910, 514, 240, 16), Qt.AlignmentFlag.AlignLeft |
               Qt.AlignmentFlag.AlignVCenter, "温室 · 植物照护室")

    # 木地板
    floor = QLinearGradient(0, 620, 0, 720)
    floor.setColorAt(0, QColor("#cfa379"))
    floor.setColorAt(1, QColor("#b98a5e"))
    p.fillRect(0, 620, 1280, 100, QBrush(floor))
    pen("#a87c52", 3)
    for x in range(120, 1280, 200):
        p.drawLine(x, 640, x - 70, 718)
    p.setPen(QPen(QColor("#9c7248"), 4))
    p.drawLine(0, 620, 1280, 620)

    # 窗在地板上的斜阳光斑
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 214, 140, 70))
    for i in range(4):
        x = 400 + i * 120
        p.drawPolygon([QPointF(x, 622), QPointF(x + 74, 622),
                       QPointF(x - 30, 718), QPointF(x - 104, 718)])

    p.end()
    img.save(str(path), "PNG")


# ================= 素材 =================
def build_stand() -> str:
    """木质花架：椭圆台面 + 单柱 + 底盘。"""
    return A1.svg_doc(240, 96,
        f'<ellipse cx="120" cy="20" rx="112" ry="17" fill="#b98a5e" '
        f'stroke="#9c7248" stroke-width="4"/>' +
        f'<path d="M 104 34 L 136 34 L 130 78 L 110 78 Z" fill="#a9784f" '
        f'stroke="#9c7248" stroke-width="3"/>' +
        f'<ellipse cx="120" cy="82" rx="52" ry="10" fill="#a9784f" '
        f'stroke="#9c7248" stroke-width="3"/>')


def build_pot() -> str:
    """陶盆：盆体 + 土面 + 插牌「莱茵生态」（剧情铭牌）。"""
    b = [
        f'<path d="M 30 42 L 150 42 L 138 128 Q 137 138 127 138 L 53 138 '
        f'Q 43 138 42 128 Z" fill="#c97b4a" stroke="#a85c34" '
        f'stroke-width="4"/>' +
        f'<rect x="24" y="26" width="132" height="22" rx="10" '
        f'fill="#d98d58" stroke="#a85c34" stroke-width="4"/>' +
        f'<ellipse cx="90" cy="40" rx="58" ry="9" fill="#6b4a32"/>' +
        # 插牌
        f'<g transform="rotate(-6 90 22)">' +
        f'<line x1="90" y1="24" x2="90" y2="-4" stroke="#8a6a52" '
        f'stroke-width="4"/>' +
        f'<rect x="46" y="-26" width="88" height="24" rx="6" fill="#fffdf6" '
        f'stroke="#8a6a52" stroke-width="2.5"/>' +
        A1.txt(90, -9, "莱茵生态", 13, "#4a5a4e", "middle", "bold") +
        f'</g>']
    return A1.svg_doc(180, 144, "".join(b))


def _candle(x, y_top, h, up=True, w=13):
    """K 线叶：矩形实体 + 上下影线。"""
    body = "#ff5a5f" if up else "#2ec4b6"
    dark = "#d64550" if up else "#1fa396"
    return (f'<line x1="{x}" y1="{y_top - 10}" x2="{x}" y2="{y_top + h + 8}" '
            f'stroke="{dark}" stroke-width="2.4"/>' +
            f'<rect x="{x - w / 2}" y="{y_top}" width="{w}" height="{h}" '
            f'rx="3" fill="{body}" stroke="{dark}" stroke-width="2"/>')


def _leaf(cx, cy, r, rot, fill="#57b98a"):
    return (f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r * 0.42}" '
            f'fill="{fill}" stroke="#3f8f6a" stroke-width="2" '
            f'transform="rotate({rot} {cx} {cy})"/>')


def build_sprout1() -> str:
    """刚冒头：嫩茎 + 两片子叶。"""
    return A1.svg_doc(120, 110,
        f'<path d="M 60 108 C 60 84 60 72 60 58" fill="none" '
        f'stroke="#4f9e5f" stroke-width="5" stroke-linecap="round"/>' +
        _leaf(38, 52, 20, -28) + _leaf(82, 46, 20, 24) +
        f'<circle cx="60" cy="56" r="5" fill="#79bd6c"/>')


def build_sprout2() -> str:
    """长出两根小 K 线叶（一红一绿）。"""
    return A1.svg_doc(140, 150,
        f'<path d="M 70 148 C 70 116 70 96 70 74" fill="none" '
        f'stroke="#4f9e5f" stroke-width="5" stroke-linecap="round"/>' +
        _candle(52, 58, 26, True, 12) + _candle(88, 40, 30, False, 12) +
        _leaf(44, 96, 18, -30) + _leaf(98, 100, 18, 28))


def build_plant3() -> str:
    """成株：主茎 + 三根 ascending K 线 + 一片圆叶。"""
    b = [f'<path d="M 90 238 C 90 190 90 150 90 108" fill="none" '
         f'stroke="#4f9e5f" stroke-width="6" stroke-linecap="round"/>',
         f'<path d="M 90 176 C 70 168 56 158 48 142" fill="none" '
         f'stroke="#4f9e5f" stroke-width="4.5" stroke-linecap="round"/>']
    b.append(_leaf(42, 136, 20, -36))
    b.append(_candle(70, 116, 34, True, 13))
    b.append(_candle(108, 88, 40, True, 13))
    b.append(_candle(88, 52, 44, True, 14))
    b.append(f'<circle cx="88" cy="46" r="5" fill="#ff5a5f"/>')
    return A1.svg_doc(180, 244, "".join(b))


def _star(cx, cy, r, fill="#ffd166"):
    pts = []
    for k in range(8):
        rr = r if k % 2 == 0 else r * 0.42
        a = math.pi / 4 * k - math.pi / 2
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'


def build_plant4() -> str:
    """涨停株：拔高、K 线层层向上、顶端开花 + 尾端大 ▲。"""
    b = [f'<path d="M 100 318 C 100 250 100 190 100 130" fill="none" '
         f'stroke="#4f9e5f" stroke-width="7" stroke-linecap="round"/>',
         f'<path d="M 100 236 C 76 226 60 214 50 196" fill="none" '
         f'stroke="#4f9e5f" stroke-width="5" stroke-linecap="round"/>',
         f'<path d="M 100 196 C 124 188 140 176 150 158" fill="none" '
         f'stroke="#4f9e5f" stroke-width="5" stroke-linecap="round"/>']
    b.append(_leaf(44, 190, 22, -36))
    b.append(_leaf(156, 152, 22, 34))
    b.append(_candle(74, 168, 34, False, 12))      # 长过一根绿的要洗盘
    b.append(_candle(126, 128, 40, True, 13))
    b.append(_candle(84, 96, 44, True, 13))
    b.append(_candle(128, 52, 50, True, 15))
    b.append(f'<path d="M 128 44 L 142 20 L 114 20 Z" fill="#ff5a5f" '
             f'stroke="#d64550" stroke-width="2"/>')
    b.append(_star(58, 66, 11) + _star(160, 96, 9) + _star(112, 14, 12))
    return A1.svg_doc(200, 324, "".join(b))


def build_badge() -> str:
    """涨停白卡：▲+10.01%（红涨）。"""
    return A1.svg_doc(190, 78,
        f'<rect x="3" y="3" width="184" height="72" rx="16" fill="#ffffff" '
        f'stroke="{A1.RED}" stroke-width="4"/>' +
        A1.txt(95, 50, "▲+10.01%", 30, A1.RED, "middle", "bold"))


def build_rocket() -> str:
    return A1.svg_doc(170, 170, A1.txt(85, 128, "🚀", 96, A1.INK, "middle"))


def build_can() -> str:
    """莱茵牌洒水壶：壶嘴朝右下，对准盆沿。"""
    return A1.svg_doc(130, 116,
        f'<path d="M 26 44 Q 47 8 72 42" fill="none" stroke="#2e8f7f" '
        f'stroke-width="6" stroke-linecap="round"/>' +
        f'<rect x="14" y="42" width="64" height="56" rx="14" fill="{RIN}" '
        f'stroke="#2e8f7f" stroke-width="4"/>' +
        f'<path d="M 74 58 L 112 86" stroke="#2e8f7f" stroke-width="9" '
        f'stroke-linecap="round"/>' +
        f'<path d="M 74 66 L 106 90" stroke="{RIN}" stroke-width="5" '
        f'stroke-linecap="round"/>' +
        f'<circle cx="114" cy="88" r="9" fill="#2e8f7f"/>' +
        f'<circle cx="114" cy="88" r="4.5" fill="{RIN}"/>')


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
        ("番外", 30, 302, "#9aa3b2", 2),
        ("缪缪的花园", 116, 432, "#ffffff", 10)]))
    put("concl.svg", A1.build_card([
        ("所谓内幕，", 84, 330, "#ffffff", 6),
        ("就是有人替你浇过水。", 84, 470, "#ffffff", 6)]))
    put("stand.svg", build_stand())
    put("pot.svg", build_pot())
    put("sprout1.svg", build_sprout1())
    put("sprout2.svg", build_sprout2())
    put("plant3.svg", build_plant3())
    put("plant4.svg", build_plant4())
    put("badge.svg", build_badge())
    put("rocket.svg", build_rocket())
    put("can.svg", build_can())
    speech = [
        ("bub0.svg", "今天也要好好长哦。", TEAL),
        ("bub1.svg", "莱茵生态，明天，必涨。", TEAL),
        ("bub2.svg", "养股票，跟养花一样嘛。", TEAL),
    ]
    for fn, text, color in speech:
        put(fn, A1.build_speech(text, color))

    def mk(cid, asset, name, layer, start, end, x, y, moves=(),
           rotation=0.0, scale=1.0, kind="svg"):
        return Clip(id=cid, type=kind, asset=asset, name=name, layer=layer,
                    start=round(start, 2), end=round(end, 2), x=x, y=y,
                    scale=scale, rotation=rotation, moves=list(moves))

    def rise(cid, asset, name, t0, t1, y_target, h):
        """植物从盆沿后升起（素材在盆图层之后 = 被盆沿遮住根部）。"""
        return mk(cid, asset, name, 6, t0, t1, 720, y_target,
                  moves=[MoveEntry(t0, round(t0 + 0.7, 2), 720,
                                   round(SOIL_Y + h / 2 - 6, 1),
                                   720, y_target)])

    clips = [
        mk("scene_bg", "scene_bg.png", "场景", 7, 0, T_END, 640, 360,
           kind="png"),
        mk("stand", "stand.svg", "花架", 6, 0, T_END, STAND[0], STAND[1]),
        mk("pot", "pot.svg", "盆栽", 5, 0, T_END, POT[0], POT[1]),
        rise("sprout1", "sprout1.svg", "芽", G1_0, G1_1, SOIL_Y - 53 + 2, 110),
        rise("sprout2", "sprout2.svg", "苗", G1_1, G1_2, SOIL_Y - 73 + 2, 150),
        rise("plant3", "plant3.svg", "成株", G1_2, T_WATER2_1,
             SOIL_Y - 120 + 2, 244),
        rise("plant4", "plant4.svg", "涨停株", T_BIG, T_END,
             SOIL_Y - 160 + 2, 324),
        mk("badge", "badge.svg", "涨停卡", -2, 25.6, 29.0, 912, 300,
           rotation=-2.0,
           moves=[MoveEntry(25.6, 25.95, 912, 326, 912, 300, 6.0, -2.0)]),
        mk("rocket", "rocket.svg", "🚀", -2, T_BIG, 26.7, 790, 380,
           moves=[MoveEntry(T_BIG, 26.5, 790, 380, 790, 120, 8.0, 0.0)]),
    ]
    # 水壶：两段浇水各一把（同一素材），壶身轻晃模拟控水节奏
    for i, (s, e) in enumerate(((8.5, 13.6), (21.5, 25.1))):
        clips.append(mk(f"can{i}", "can.svg", f"水壶{i}", -2, s, e,
                        CAN[0], CAN[1], rotation=-10.0,
                        moves=[MoveEntry(s, s + 0.3, CAN[0], CAN[1] + 18,
                                         CAN[0], CAN[1], 2.0, -10.0),
                               MoveEntry(s + 1.4, s + 1.9, CAN[0], CAN[1],
                                         CAN[0], CAN[1], -10.0, -4.0),
                               MoveEntry(s + 2.6, s + 3.1, CAN[0], CAN[1],
                                         CAN[0], CAN[1], -4.0, -12.0),
                               MoveEntry(s + 3.9, s + 4.3, CAN[0], CAN[1],
                                         CAN[0], CAN[1], -12.0, -10.0)]))
    # 台词气泡（尾巴垂到头顶：cx = 头x + 0.15×宽）
    bubbles = [
        ("bub0", 6.0, 8.2),
        ("bub1", 17.4, 20.6),
        ("bub2", 25.8, 28.2),
    ]
    for cid, s, e in bubbles:
        text = next(t for fn, t, _c in speech if fn == f"{cid}.svg")
        w = max(130, 44 + int(len(text) * 17.2))
        cx = round(M_X + 0.15 * w, 1)
        clips.append(mk(cid, f"{cid}.svg", f"台词{cid}", -2, s, e, cx, 320,
                        rotation=-1.5,
                        moves=[MoveEntry(s, s + 0.35, cx, 300, cx, 320,
                                         5.0, -1.5)]))

    # ---- 缪缪2号：走入 → 叉腰 → 浇水 ×2 → 看涨 → 耳语 → 得意 → 走人 ----
    mlyu = Clip(id="mlyu", type="spine", asset="缪缪2号", name="缪缪",
                layer=-1, start=M_WALK0, end=T_CARD, x=-160, y=FEET_Y,
                scale=SCALE)
    mlyu.moves = [
        MoveEntry(M_WALK0, M_ARRIVE, -160, FEET_Y, M_X, FEET_Y),
        MoveEntry(M_EXIT0, M_EXIT1, M_X, FEET_Y, -160, FEET_Y),
    ]
    mlyu.anims = [
        AnimEntry(M_WALK0, M_ARRIVE, "Move", 1.0, True, False),
        AnimEntry(M_ARRIVE, T_ADMIRE0, "Default", 1.0, True, False),
        AnimEntry(T_ADMIRE0, T_ADMIRE1, "叉腰", 1.0, True, False),
        AnimEntry(T_ADMIRE1, T_WATER1_0, "Default", 1.0, True, False),
        AnimEntry(T_WATER1_0, T_WATER1_1, "浇水", 1.0, True, False),
        AnimEntry(T_WATER1_1, T_WHIS0, "Default", 1.0, True, False),
        AnimEntry(T_WHIS0, T_WHIS1, "耳语", 1.0, True, True),
        AnimEntry(T_WHIS1, T_WATER2_0, "Default", 1.0, True, True),
        AnimEntry(T_WATER2_0, T_WATER2_1, "浇水", 1.0, True, False),
        AnimEntry(T_WATER2_1, 25.4, "Default", 1.0, True, False),
        AnimEntry(25.4, T_PROUD_END, "得意", 1.0, True, False),
        AnimEntry(T_PROUD_END, M_EXIT1, "Move", 1.0, True, True),
    ]
    clips.append(mlyu)

    clips += [
        mk("title", "title.svg", "标题卡", 0, 0, T_TITLE_END, 640, 360),
        mk("concl", "concl.svg", "结论卡", 0, T_CARD, T_END, 640, 360),
    ]

    proj.canvas = {"w": 1280, "h": 720, "fps": 30, "bg": "#eed3b2"}
    proj.duration = T_END
    proj.layers = 8
    proj.clips = clips
    store.save(proj)
    print(f"项目「{SCENE}」：总时长 {T_END}s，{len(clips)} 片段")
    print(f"  浇水一 {T_WATER1_0}-{T_WATER1_1}s → 生长 {G1_0}-{G1_2}s；"
          f"耳语 {T_WHIS0}s；涨停株 {T_BIG}s；结论卡 {T_CARD}s")


if __name__ == "__main__":
    build()
