"""生成工作区动画项目「可露希尔看盘0710」：看盘小剧场。

剧情（40s / 30fps）：
- 1.6-7.0s 可露希尔（spine·Move）从画右走到凳子旁，随后坐下
- 8.0s      显示器和行情终端降下；8.8s 起看板播放，每天 3.8s 翻页
- 21.8s     摔下凳子「大哭打滚」；25.6s 躺平（Sleep）麻木
- 31.2s     起身左行；35.6s 到阳台坐下，38.0s 起倾斜至 -30°
- 看板经 board_clips(k=0.45) 仿射贴进屏幕；遮罩车尾藏在看板侧栏底板下

图层（0 最上）：表情气泡 / 弹窗窗体 / 刻度+侧栏底板 / 遮罩 / 曲线+标题 /
底板（PNG 场景在 GL 之下，spine 可露希尔走在场景前面、凳子 DOM 在她前面）。
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PRTS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRTS_ROOT))
sys.path.insert(0, str(PRTS_ROOT / "tools"))

from core.workspace import AnimEntry, Clip, MoveEntry, Project, WorkspaceStore  # noqa: E402
import gen_stock_board as B  # noqa: E402

SCENE = "可露希尔看盘0710"

T_WALK0, T_ARRIVE = 1.6, 7.0        # 走入 / 坐下时刻
T_DESC, T_BOARD = 8.0, 8.8          # 显示器+屏幕齐降 / 看板起播
K, OX, OY = 0.45, 430, 132          # 看板 1280x720 → 屏幕（中部偏右）
CH_X, FEET_Y = 1090, 660            # 凳子中心 / 走路脚底 y
CLICK_SCALE = 0.75                  # 正值；朝向由各动作段的 flip 控制
SIT_Y = 567                         # 坐姿 y：悬空腿底 ≈ 655（贴地）
LEAVE_X = 200                       # 阳台护栏边（最左）
T_WALK_OUT = 31.2                   # 周五提前起身，边走边抬
T_CARD = 35.6                       # 走到最左，强制平仓大字砸下

WALL = "#dff3ff"


# ================= 场景底板（PNG：画在 GL 之下，人物走在它前面） =================
def make_scene_png(path: Path):
    """罗德岛风格舱室：模块化金属墙板、阳台、书桌、舷窗和绿植。"""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import (QBrush, QColor, QFont, QImage,
                               QLinearGradient, QPainter, QPen)

    img = QImage(1280, 720, QImage.Format.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    def pen(c, w=4):
        p.setPen(QPen(QColor(c), w, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

    def rrect(x, y, w, h, fill, line=None, r=10, lw=4):
        pen(line or fill, lw)
        p.setBrush(QColor(fill))
        p.drawRoundedRect(QRectF(x, y, w, h), r, r)

    def text(x, y, w, h, value, size, color, bold=False):
        p.setPen(QColor(color))
        p.setFont(QFont("Microsoft YaHei", size, 700 if bold else 400))
        p.drawText(QRectF(x, y, w, h), Qt.AlignmentFlag.AlignLeft |
                   Qt.AlignmentFlag.AlignVCenter, value)

    def bolt(x, y):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#6f899d"))
        p.drawEllipse(QPointF(x, y), 2, 2)
        p.setBrush(QColor("#e8f5fb"))
        p.drawEllipse(QPointF(x - 0.5, y - 0.5), 0.7, 0.7)

    outdoor = QLinearGradient(0, 0, 330, 660)
    outdoor.setColorAt(0, QColor("#b9d9eb"))
    outdoor.setColorAt(1, QColor("#d9edf6"))
    p.fillRect(0, 0, 330, 720, QBrush(outdoor))
    wall = QLinearGradient(330, 0, 1280, 660)
    wall.setColorAt(0, QColor("#eaf5f9"))
    wall.setColorAt(0.55, QColor("#d7e8f0"))
    wall.setColorAt(1, QColor("#bed3df"))
    p.fillRect(330, 0, 950, 660, QBrush(wall))

    # 模块化墙板、接缝和固定螺栓
    for row, (y, h) in enumerate(((68, 246), (322, 300))):
        for col, x in enumerate(range(342, 1280, 184)):
            w = min(176, 1272 - x)
            if w <= 8:
                continue
            p.setPen(QPen(QColor("#aec5d2"), 1))
            p.setBrush(QColor("#e6f1f5") if (row + col) % 2 == 0
                       else QColor("#d3e4ec"))
            p.drawRect(QRectF(x, y, w, h))
            for bx, by in ((x + 7, y + 7), (x + w - 7, y + 7),
                           (x + 7, y + h - 7), (x + w - 7, y + h - 7)):
                bolt(bx, by)
    p.fillRect(330, 626, 950, 34, QColor("#607687"))
    pen("#2f4354", 2)
    for x in range(330, 1281, 184):
        p.drawLine(x, 626, x, 660)
    p.fillRect(330, 626, 950, 3, QColor("#8fa8b8"))

    # 顶部结构梁和冷色灯带
    p.fillRect(0, 0, 1280, 30, QColor("#283b4b"))
    p.fillRect(0, 30, 1280, 6, QColor("#60798b"))
    p.fillRect(330, 39, 950, 3, QColor("#53d7df"))
    p.fillRect(330, 43, 950, 1, QColor("#b9ffff"))
    for x in range(352, 1280, 184):
        bolt(x, 15)

    # 罗德岛式舱室标识
    p.fillRect(454, 55, 5, 42, QColor("#35bcc8"))
    text(470, 52, 260, 25, "RHODES ISLAND", 17, "#30485b", True)
    text(471, 77, 230, 16, "B-04  /  OPERATIONS", 8, "#688498")
    rrect(342, 145, 82, 88, "#f3f8fa", "#60798b", 7, 2)
    p.fillRect(342, 145, 82, 5, QColor("#53d7df"))
    grad = QLinearGradient(352, 0, 388, 0)
    grad.setColorAt(0.5, QColor("#e6544c"))
    grad.setColorAt(0.5001, QColor("#2eb872"))
    p.setPen(QPen(QBrush(grad), 0))
    p.setFont(QFont("Microsoft YaHei", 30, 900))
    p.drawText(QRectF(344, 160, 48, 60), Qt.AlignmentFlag.AlignCenter, "A")
    p.setPen(QPen(QColor("#33415c"), 1))
    p.setFont(QFont("Microsoft YaHei", 17))
    p.drawText(QRectF(390, 160, 28, 60), Qt.AlignmentFlag.AlignCenter, "区")
    p.setBrush(Qt.BrushStyle.NoBrush)

    # 通风格栅与检修盖板
    rrect(354, 286, 74, 116, "#8da4b3", "#40596b", 4, 2)
    p.fillRect(360, 294, 62, 82, QColor("#d5e2e9"))
    pen("#617b8d", 3)
    for y in range(302, 374, 12):
        p.drawLine(364, y, 418, y)
    text(363, 379, 58, 14, "VENT 04", 7, "#334f63", True)
    bolt(360, 292)
    bolt(422, 292)
    bolt(360, 396)
    bolt(422, 396)

    # 室内外地台：金属地板、分区和安全标线
    floor = QLinearGradient(0, 660, 0, 720)
    floor.setColorAt(0, QColor("#bdcbd3"))
    floor.setColorAt(1, QColor("#8fa6b4"))
    p.fillRect(330, 660, 950, 60, QBrush(floor))
    p.fillRect(0, 648, 330, 12, QColor("#8caabd"))
    pen("#425e71", 3)
    p.drawLine(330, 660, 1280, 660)
    pen("#6e8798", 2)
    for x in range(400, 1280, 140):
        p.drawLine(x, 664, x - 30, 718)
    p.drawLine(330, 692, 1280, 692)
    for x in range(352, 1260, 56):
        p.fillRect(x, 674, 32, 4, QColor("#d7b64b"))
    p.fillRect(326, 0, 14, 660, QColor("#354e61"))
    p.fillRect(330, 44, 3, 582, QColor("#54d8e0"))
    pen("#7893a6", 2)
    p.drawLine(340, 0, 340, 660)

    # 阳台远景与地板
    p.fillRect(0, 620, 130, 100, QColor("#c2dce9"))
    p.setPen(Qt.PenStyle.NoPen)
    for bx, bw, bh, color in ((4, 24, 80, "#8fb1c6"),
                              (30, 18, 108, "#7d9fb6"),
                              (52, 22, 62, "#9ab8ca"),
                              (76, 16, 90, "#86a9bd")):
        p.fillRect(bx, 720 - bh, bw, bh, QColor(color))
    pen("#c2d8e4", 1)
    for bx, bw, bh in ((4, 24, 80), (30, 18, 108), (52, 22, 62), (76, 16, 90)):
        for wy in range(720 - bh + 8, 712, 12):
            p.drawLine(bx + 3, wy, bx + bw - 3, wy)
    p.fillRect(144, 660, 186, 60, QColor("#a8b6bf"))
    pen("#708797", 2)
    for x in range(160, 330, 36):
        p.drawLine(x, 664, x - 22, 718)

    # 右移后的护栏：金属框、磨砂内板和顶部灯条
    p.fillRect(130, 468, 44, 192, QColor("#6f8797"))
    p.fillRect(136, 476, 32, 176, QColor("#bfd6e1"))
    pen("#91adbd", 2)
    for y in range(492, 650, 26):
        p.drawLine(137, y, 167, y)
    rrect(122, 452, 60, 20, "#3b5365", "#233c4e", 5, 2)
    p.fillRect(130, 458, 44, 3, QColor("#57dce2"))
    bolt(136, 486)
    bolt(164, 486)
    bolt(136, 642)
    bolt(164, 642)

    # 书桌：金属包边、青色嵌条和支撑脚
    rrect(402, 508, 632, 42, "#3c5262", "#263d4d", 8, 2)
    desk = QLinearGradient(0, 512, 0, 540)
    desk.setColorAt(0, QColor("#d6e1e7"))
    desk.setColorAt(1, QColor("#91a8b6"))
    p.setBrush(QBrush(desk))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(408, 512, 620, 26), 5, 5)
    p.fillRect(420, 541, 590, 3, QColor("#4bd2da"))
    pen("#3c5668", 8)
    p.drawLine(440, 550, 440, 658)
    p.drawLine(994, 550, 994, 658)
    pen("#92a9b7", 3)
    p.drawLine(440, 550, 440, 658)
    p.drawLine(994, 550, 994, 658)
    p.fillRect(428, 652, 28, 6, QColor("#354e60"))
    p.fillRect(982, 652, 28, 6, QColor("#354e60"))

    # 舷窗：深色金属框、渐变天空和远景建筑
    rrect(1056, 96, 148, 203, "#354e61", "#1f3546", 13, 3)
    sky = QLinearGradient(0, 108, 0, 288)
    sky.setColorAt(0, QColor("#8fc9e5"))
    sky.setColorAt(1, QColor("#d9edf4"))
    p.setBrush(QBrush(sky))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(QRectF(1068, 108, 124, 178))
    for bx, bw, bh in ((1072, 20, 46), (1095, 28, 72), (1128, 17, 54),
                       (1148, 34, 88)):
        p.fillRect(bx, 286 - bh, bw, bh, QColor("#7e9fb2"))
    p.fillRect(1124, 104, 8, 188, QColor("#405b6e"))
    p.fillRect(1064, 192, 132, 8, QColor("#405b6e"))
    pen("#8bdde5", 2)
    p.drawLine(1070, 110, 1188, 110)
    bolt(1066, 106)
    bolt(1194, 106)
    bolt(1066, 288)
    bolt(1194, 288)

    # 绿植和纸团保留在原有位置
    rrect(1135, 606, 76, 54, "#c76c58", "#704b47", 8, 2)
    p.fillRect(1133, 606, 80, 9, QColor("#e09579"))
    pen("#2f8065", 5)
    p.setBrush(QColor("#4dbb83"))
    for dx, dy, rw, rh in ((0, -18, 26, 40), (-24, -6, 20, 28), (24, -8, 22, 30)):
        p.drawEllipse(QPointF(1173 + dx, 596 + dy), rw / 2, rh / 2)
    for x, y, r in ((1030, 650, 10), (1072, 654, 9), (1108, 646, 8)):
        p.setBrush(QColor("#f4f7f8"))
        pen("#9fb4c1", 2)
        p.drawEllipse(QPointF(x, y), r, r)
    p.end()
    img.save(str(path), "PNG")


# ================= DOM 素材（在她前面的东西 / 弹窗 / 气泡） =================
def svg_doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
            f'height="{h}" viewBox="0 0 {w} {h}">{body}</svg>')


def txt(x, y, s, size, fill, anchor="start", weight="normal",
        family="Microsoft YaHei UI, Microsoft YaHei, Segoe UI Emoji"):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{s}</text>')


def build_stool() -> str:
    """凳子（DOM：坐时挡在她大腿前面，形成「坐上去」的层次）。"""
    return svg_doc(128, 150,
        f'<rect x="8" y="8" width="112" height="26" rx="12" fill="#ff8fab" '
        f'stroke="#e56b8c" stroke-width="4"/>' +
        "".join(
            f'<line x1="{x}" y1="34" x2="{x}" y2="140" stroke="#c76b86" '
            f'stroke-width="7" stroke-linecap="round"/>' for x in (26, 102)) +
        '<line x1="26" y1="56" x2="102" y2="56" stroke="#c76b86" '
        'stroke-width="6" stroke-linecap="round"/>')


def build_monitor() -> str:
    """显示器（黑板）：边框 + 待机暗屏。独立 DOM 片段，可随弹窗升降。"""
    return svg_doc(604, 426,
        f'<rect x="2" y="2" width="600" height="422" rx="18" fill="#4b5b74" '
        f'stroke="#38455c" stroke-width="4"/>' +
        f'<rect x="14" y="14" width="576" height="394" rx="8" '
        f'fill="#1c2735" stroke="#2c3a50" stroke-width="3"/>')


def build_popup() -> str:
    """行情终端弹窗：标题栏（空，仅关闭钮）+ 屏幕开孔（evenodd）。

    开孔 576x324 = 看板 1280x720 缩放后；无右边框柱——看板遮罩整车
    停进加宽的侧栏面板之下，画面右侧不再有白色长条。
    """
    return svg_doc(592, 362,
        f'<path fillRule="evenodd" fill="#ffffff" stroke="#8fa3c0" '
        f'stroke-width="4" d="M 15 2 L 581 2 Q 590 2 590 11 L 590 351 '
        f'Q 590 360 581 360 L 11 360 Q 2 360 2 351 L 2 11 Q 2 2 11 2 Z '
        f'M 10 32 L 582 32 L 582 352 L 10 352 Z"/>' +
        f'<rect x="2" y="2" width="588" height="28" rx="9" fill="#f2f6fb" '
        f'stroke="#8fa3c0" stroke-width="3"/>' +
        f'<circle cx="562" cy="16" r="8" fill="#ff6b6b" stroke="#e05252" '
        f'stroke-width="2"/>' +
        txt(562, 20, "✕", 11, "#ffffff", "middle", "bold"))


def build_emotion(emoji: str, color: str) -> str:
    """表情气泡：只留一个大 emoji（去掉头上的小字）。"""
    return svg_doc(92, 104,
        f'<rect x="3" y="3" width="86" height="80" rx="18" fill="#ffffff" '
        f'stroke="{color}" stroke-width="4"/>' +
        f'<path d="M 34 82 L 56 82 L 40 100 Z" fill="#ffffff" '
        f'stroke="{color}" stroke-width="4" stroke-linejoin="round"/>' +
        f'<rect x="32" y="76" width="26" height="10" fill="#ffffff"/>' +
        txt(46, 58, emoji, 36, "#33415c", "middle"))


def build_liquidation() -> str:
    """「强制平仓」：只要四个正式黑体大白字，无描边。"""
    return svg_doc(1280, 400,
        f'<text x="627" y="300" font-family="SimHei, Microsoft YaHei" '
        f'font-size="250" fill="#ffffff" font-weight="bold" '
        f'letter-spacing="30" text-anchor="middle">强制平仓</text>')


# ================= 场景装配 =================
def build():
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        QGuiApplication([])          # QImage/QPainter 需要实例（无窗口）
    store = WorkspaceStore()
    # 数据复用看板项目的缓存（gen_stock_board 先跑）
    board_cache = store.root / B.PROJECT / "_data.json"
    if not board_cache.exists():
        print("先跑 python tools/gen_stock_board.py 生成数据")
        sys.exit(1)
    data = json.loads(board_cache.read_text(encoding="utf-8"))
    days = [d for d in B.WEEK if data["intraday"].get(d)]
    rows = B.load_rows(data, days)

    shutil.rmtree(store.root / SCENE, ignore_errors=True)
    proj = store.create(SCENE)
    assets = store.assets_dir(SCENE)
    make_scene_png(assets / "scene_bg.png")
    (assets / "stool.svg").write_text(build_stool(), encoding="utf-8")
    (assets / "popup.svg").write_text(build_popup(), encoding="utf-8")
    (assets / "monitor.svg").write_text(build_monitor(), encoding="utf-8")
    (assets / "veil.svg").write_text(
        svg_doc(1280, 720,
                '<rect width="1280" height="720" fill="#08080e" '
                'opacity="0.88"/>'), encoding="utf-8")
    (assets / "wipe.svg").write_text(build_liquidation(), encoding="utf-8")

    t_day = lambda i: round(T_BOARD + B.INTRO + i * B.FRAME, 2)   # noqa: E731
    T_D3, T_D4, T_D5 = t_day(2), t_day(3), t_day(4)
    # 情绪动作窗口：现价徽章亮出（T+2.0）起，到次日翻页止
    E0, E1, E2 = round(t_day(0) + 2.0, 2), t_day(1), t_day(2)
    T_FLY = round(T_D4 + 0.1, 2)          # 凳子被撞飞
    T_UP = t_day(len(days))               # 屏幕+显示器齐升（她已在途中）
    duration = round(T_CARD + 4.4, 2)
    prop_end = round(T_CARD + 2.4, 2)

    # 看板贴进屏幕（时间平移 T_BOARD；缩放后字号偏小 → 字体增强 1.45 倍
    # 保可读；exit=片尾看板随显示器/弹窗整体上飞）
    B.FONT_BOOST = 1.45
    bclips, board_dur = B.board_clips(assets, data, days, rows, t0=T_BOARD,
                                      k=K, ox=OX, oy=OY,
                                      exit=T_UP - T_BOARD)
    B.FONT_BOOST = 1.0
    for c in bclips:
        if c.id in ("chrome_main", "chrome_side", "title"):
            c.end = duration

    clips = [
        Clip(id="scene_bg", type="png", asset="scene_bg.png", name="场景",
             layer=6, start=0, end=duration, x=640, y=360),
        Clip(id="stool", type="svg", asset="stool.svg", name="凳子",
             layer=2, start=0, end=prop_end, x=CH_X, y=591,
             moves=[MoveEntry(T_FLY, round(T_FLY + 0.6, 2),
                              CH_X, 591, 1650, 130, 0.0, 180.0)]),
        # 显示器（黑板）：开场随弹窗齐降，片尾看板+弹窗+显示器齐升
        Clip(id="monitor", type="svg", asset="monitor.svg", name="显示器",
             layer=5, start=0, end=prop_end, x=718, y=297,
             moves=[MoveEntry(T_DESC, round(T_DESC + 0.6, 2),
                              718, -263, 718, 297),
                    MoveEntry(T_UP, round(T_UP + 0.8, 2),
                              718, 297, 718, -263)]),
        # 弹窗（层4 压住遮罩层3）：屏幕开孔透出看板；开场齐降、片尾齐升
        Clip(id="popup", type="svg", asset="popup.svg", name="弹窗",
             layer=4, start=0, end=prop_end, x=716, y=281,
             moves=[MoveEntry(T_DESC, round(T_DESC + 0.6, 2),
                              716, -279, 716, 281),
                    MoveEntry(T_UP, round(T_UP + 0.8, 2),
                              716, 281, 716, -279)]),
        # 「强制平仓」：走到最左时直接出现，无描边无过渡
        Clip(id="wipe", type="svg", asset="wipe.svg", name="平仓字幕",
             layer=0, start=T_CARD, end=duration, x=640, y=360),
    ]
    # 可露希尔：走位 → 坐 → 越哭越瘫 → 摔下凳子打滚 → 躺平麻木 →
    # 屏幕上飞后起身往左走（准备"跳楼"）→ 坐下倾斜
    click = Clip(id="click", type="spine", asset="可露希尔", name="可露希尔",
                 layer=-1, start=0, end=duration, x=1340, y=FEET_Y,
                 scale=CLICK_SCALE)
    click.moves = [
        MoveEntry(T_WALK0, T_ARRIVE, 1340, FEET_Y, CH_X, FEET_Y),
        # 一屁股坐下（Sit 姿势腿悬到锚点下方，y 提到 SIT_Y 才贴地）
        MoveEntry(T_ARRIVE, round(T_ARRIVE + 0.01, 2),
                  CH_X, FEET_Y, CH_X, SIT_Y),
        # 越哭越瘫
        MoveEntry(T_D3, T_D4, CH_X + 13, 610, CH_X + 13, 612, 0.0, 7.0),
        # 摔下凳子 → 地板打滚
        MoveEntry(T_D4, round(T_D4 + 0.6, 2), CH_X, SIT_Y + 16,
                  CH_X + 70, FEET_Y - 8, 7.0, 0.0),
        # 周五提前起身（边走边抬），一路走到阳台护栏边 → 大字砸下
        MoveEntry(T_WALK_OUT, T_CARD, CH_X + 70, FEET_Y - 8,
                  LEAVE_X, FEET_Y),
        MoveEntry(T_CARD, prop_end, 137, 522, 137, 522, 0.0, -0.0),
        MoveEntry(prop_end, duration, 137, 522, 137, 522, 0.0, -30.0),
    ]
    click.anims = [
        # 周三之前面向屏幕（flip=True 镜像）；周四起"转过来"背对
        AnimEntry(T_WALK0, T_ARRIVE, "Move", 1.0, True, True),
        AnimEntry(T_ARRIVE, E0, "Sit", 1.0, True, True),
        # 自创情绪动作：涨停日欢呼、首跌日震惊（Spine/proc/可露希尔/）
        AnimEntry(E0, E1, "开心", 1.0, True, True),
        AnimEntry(E1, E2, "惊讶", 0.3, True, True),
        # 周二摆手（官方 Interact）
        AnimEntry(E2, T_D4, "Interact", 1.0, True, True),
        # 礼拜三打滚也"转过来"（背对屏幕）
        AnimEntry(T_D4, T_D5, "大哭打滚", 1.0, True, False),
        # 礼拜三之后转过来：躺平、起身、走向阳台都背对屏幕
        AnimEntry(T_D5, T_WALK_OUT, "Sleep", 1.0, True, False),
        AnimEntry(T_WALK_OUT, T_CARD, "Move", 0.5, True, False),
        AnimEntry(T_CARD, duration, "Sit", 1.0, True, False),
    ]
    click2 = Clip.from_dict(click.to_dict())
    click2.id = "click2"
    click2.asset = click2.name = "可露希尔2号"
    click2.start = T_D5
    click2.x, click2.y = CH_X + 70, FEET_Y - 8
    click.moves = [m for m in click.moves if m.start < T_D5]
    click.anims = [a for a in click.anims if a.start < T_D5]
    click.end = T_D5
    click2.moves = [m for m in click2.moves if m.start >= T_D5]
    click2.anims = [a for a in click2.anims if a.start >= T_D5]
    clips += [click, click2]

    # 表情气泡（对齐每天帧，只留 emoji）
    EMO = [
        (0, "😂", "#ff9f1c", 1100, 350),
        (1, "😲", "#4cc9f0", 1100, 350),
        (4, "🫥", "#adb5bd", 1140, 500),
    ]
    for i, emoji, color, ex, ey in EMO:
        fn = f"emo{i}.svg"
        (assets / fn).write_text(build_emotion(emoji, color),
                                 encoding="utf-8")
        T = t_day(i)
        clips.append(Clip(
            id=f"emo{i}", type="svg", asset=fn, name=f"表情{i}", layer=0,
            start=round(T + 0.8, 2),
            end=duration if i == len(days) - 1 else round(t_day(i + 1), 2),
            x=ex, y=ey, rotation=-2.0,
            moves=[MoveEntry(round(T + 0.8, 2), round(T + 1.3, 2),
                             ex, ey - 26, ex, ey, 8.0, -2.0)]))

    clips += bclips
    proj.canvas = {"w": 1280, "h": 720, "fps": 30, "bg": WALL}
    proj.duration = duration
    proj.layers = 8
    proj.clips = clips
    store.save(proj)
    print(f"项目「{SCENE}」：总时长 {duration}s，{len(clips)} 片段")
    print(f"  走入 {T_WALK0}-{T_ARRIVE}s，显示器+屏幕齐降 {T_DESC}s，"
          f"看板 {T_BOARD}s 起，每天帧 {'/'.join(str(t_day(i)) for i in range(len(days)))}s")


if __name__ == "__main__":
    build()
