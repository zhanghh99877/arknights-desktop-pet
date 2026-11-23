"""生成工作区动画项目「套消息第二幕」：可露希尔 × 缪缪。

第二幕（≈31s / 30fps），接第一幕「只有内幕才是钱」的结论：
- 0-2.0    黑场硬切标题卡「第二幕 · 套消息」
- 2.2-4.8  缪缪2号走入生态科大厅（面向右）；2.6-7.0 可露希尔
           「潜行」猫腰入场
- 7.2-10.2 可露希尔开口要内幕；10.6-15.2 缪缪「装傻」（摊手吹口哨）
- 15.2-16.8 红包从可露希尔手中抛物线飞到缪缪手里；缪缪「收红包」
           （前 0.7s 双手一夹，之后反剪背后得意）
- 18.2-23.2 缪缪「耳语」凑近 + 可露希尔「侧耳」；交代消息：
           「莱茵生态，明天，必涨。」
- 23.4-27.0 缪缪转身飘然离场；可露希尔「决意」（💡→😏）
- 27.2-31.0 硬切结论大字「莱茵生态，明天必涨。」（悬念收尾，接第三幕）

彩蛋：墙上行情电视（帧裁剪内容）滚动莱茵系五只 + 大帝系两只
（塞壬唱片/企鹅物流同涨同跌，与第一幕联动）。
台词气泡白底彩边：可露希尔红边、缪缪青边；emoji 只留 emoji。
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

SCENE = "套消息第二幕"

# ---- 时间轴（秒） ----
T_TITLE_END = 2.0
M_WALK0, M_ARRIVE = 2.2, 4.8       # 缪缪走入
C_WALK0, C_ARRIVE = 2.6, 7.0       # 可露希尔潜行入场
T_ASK0, T_ASK1 = 7.2, 10.2         # 开口要内幕
T_ACT_SILLY = 10.6                 # 缪缪装傻
T_GIFT0, T_GIFT1 = 15.2, 16.8      # 红包飞行→被收下
T_WHIS = 18.2                      # 耳语 + 侧耳
T_WHIS_END = 23.2
M_EXIT0, M_EXIT1 = 23.4, 27.0      # 缪缪离场
T_EXIT = 27.2                      # 可露希尔定格退场 & 硬切结论卡
T_END = 31.0

FEET_Y = 660
M_X, C_X = 560.0, 950.0            # 两人站位（缪缪左、可露希尔右）
SCALE = 0.75
HEAD_Y = 360                       # 站立头部高度（气泡/emoji 锚位参考）

# 墙上行情电视（舞台坐标，内容帧 236x132 居中锚）
TV = (1150.0, 205.0)
TVW, TVH = 236, 132

WALL_TEXT = "#37a58e"


def svg_doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
            f'height="{h}" viewBox="0 0 {w} {h}">{body}</svg>')


def make_scene_png(path: Path):
    """莱茵生命生态科大厅：生态园玻璃幕墙、水培柱、种植槽、行情电视墙。"""
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

    # 玻璃幕墙外的生态园：天光 + 两层丛林丘陵
    sky = QLinearGradient(0, 0, 0, 720)
    sky.setColorAt(0, QColor("#eafaf3"))
    sky.setColorAt(1, QColor("#d2ecdf"))
    p.fillRect(0, 0, 1280, 720, QBrush(sky))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#a9d9c0"))
    for cx, cy, rx in ((160, 560, 240), (520, 590, 300), (900, 570, 280),
                       (1220, 600, 260)):
        p.drawEllipse(QPointF(cx, cy), rx, 150)
    p.setBrush(QColor("#8cc9ae"))
    for cx, cy, rx in ((60, 640, 200), (420, 660, 260), (820, 645, 240),
                       (1180, 668, 230)):
        p.drawEllipse(QPointF(cx, cy), rx, 120)
    # 远景树冠
    p.setBrush(QColor("#79bd9c"))
    for cx, cy, r in ((240, 470, 54), (330, 500, 40), (760, 480, 58),
                      (860, 505, 42), (1120, 490, 50), (1010, 515, 34)):
        p.drawEllipse(QPointF(cx, cy), r, r * 0.8)

    # 玻璃竖梃与横梁
    p.setBrush(QColor("#b9d8cc"))
    for x in range(96, 1280, 158):
        p.drawRect(QRectF(x, 56, 9, 592))
    p.drawRect(QRectF(0, 214, 1280, 9))
    pen("#a5c9ba", 2)
    p.drawLine(0, 452, 1280, 452)

    # 顶部墙带：RHINE LIFE 标识
    p.fillRect(0, 0, 1280, 56, QColor("#f4fbf8"))
    p.fillRect(0, 52, 1280, 5, QColor("#35b8a0"))
    p.fillRect(452, 12, 5, 34, QColor("#35b8a0"))
    p.setPen(QColor("#2e8f7f"))
    p.setFont(QFont("Microsoft YaHei", 17, 700))
    p.drawText(QRectF(468, 8, 300, 28), Qt.AlignmentFlag.AlignLeft |
               Qt.AlignmentFlag.AlignVCenter, "RHINE LIFE")
    p.setFont(QFont("Microsoft YaHei", 8))
    p.setPen(QColor("#6fae9d"))
    p.drawText(QRectF(470, 34, 300, 16), Qt.AlignmentFlag.AlignLeft |
               Qt.AlignmentFlag.AlignVCenter, "ECOLOGY DEPT · 生态科")

    # 地板
    floor = QLinearGradient(0, 640, 0, 720)
    floor.setColorAt(0, QColor("#e6efe9"))
    floor.setColorAt(1, QColor("#c9d9d0"))
    p.fillRect(0, 640, 1280, 80, QBrush(floor))
    pen("#b5c9bf", 2)
    for x in range(140, 1280, 220):
        p.drawLine(x, 664, x - 60, 718)
    p.setPen(QPen(QColor("#9fc2b2"), 3))
    p.drawLine(0, 640, 1280, 640)

    # 水培柱 ×3（左区，金属底座 + 水位线 + 气泡）
    for x in (128, 226, 324):
        rrect(x, 258, 54, 382, "#c9ecf4", "#8fd0de", 24, 3)
        p.fillRect(x + 5, 300, 44, 6, QColor("#7fd4e8"))
        pen("#8fd0de", 2)
        p.setBrush(QColor("#ffffff"))
        for bx, by, r in ((x + 18, 360, 4), (x + 34, 420, 3), (x + 24, 500, 5),
                          (x + 38, 560, 3), (x + 16, 590, 4)):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 150))
            p.drawEllipse(QPointF(bx, by), r, r)
        rrect(x - 8, 622, 70, 26, "#9fb8ac", "#7ea294", 6, 2)
    # 柱顶灯带
    for x in (128, 226, 324):
        p.fillRect(x + 6, 252, 42, 5, QColor("#57d7c2"))

    # 种植槽（中区，人物身后）
    rrect(392, 596, 386, 52, "#d8e8df", "#a8c8ba", 10, 3)
    pen("#3f9e74", 4)
    p.setBrush(QColor("#57b98a"))
    for dx, dy, rx, ry in ((30, -18, 34, 26), (92, -30, 40, 30),
                           (158, -16, 32, 24), (222, -28, 38, 28),
                           (288, -18, 34, 25), (342, -26, 30, 22)):
        p.drawEllipse(QPointF(440 + dx, 596 + dy), rx, ry)
    pen("#2f7f5e", 3)
    for dx in (30, 92, 158, 222, 288, 342):
        p.drawLine(440 + dx, 596, 440 + dx, 560)

    # 右侧墙柱（电视挂柱）
    p.fillRect(1176, 56, 104, 584, QColor("#dcefe6"))
    pen("#a5c9ba", 2)
    p.drawLine(1176, 56, 1176, 640)
    p.setBrush(QColor("#cfe8dc"))
    p.drawRect(QRectF(1196, 96, 64, 300))

    p.end()
    img.save(str(path), "PNG")


def build_tv_bezel() -> str:
    return svg_doc(260, 150,
        f'<rect x="2" y="2" width="256" height="146" rx="12" '
        f'fill="#3c4a63" stroke="#2b364c" stroke-width="4"/>' +
        f'<rect x="12" y="9" width="236" height="132" rx="6" '
        f'fill="#05080f"/>')


def build_tv_screen(hot: bool = False) -> str:
    """行情电视内容（帧裁剪）：莱茵系行情列表 + 大帝系联动彩蛋。

    hot=True 为耳语交底瞬间的高亮版：莱茵生态行放大加琥珀底，
    其余行压暗——观众视线被钉在「内幕票」上。
    """
    rows = [("莱茵航天", "+1.20%", False), ("莱茵能源", "+0.87%", False),
            ("莱茵生态", "+0.35%", True), ("莱茵科技", "-0.14%", False),
            ("塞壬唱片", "+5.20%", False), ("企鹅物流", "+5.20%", False)]
    b = [f'<rect width="{TVW}" height="{TVH}" fill="#0c1420"/>']
    b.append(A1.txt(TVW / 2, 15, "RHINE 行情", 10, "#9fb6d8", "middle",
                    "bold"))
    for i, (name, pct, star) in enumerate(rows):
        y = 26 + i * 17.5
        up = pct.startswith("+")
        color = A1.RED if up else A1.GREEN
        arrow = "▲" if up else "▼"
        dim = hot and not star
        op = ' opacity="0.45"' if dim else ""
        if hot and star:
            b.append(f'<rect x="6" y="{y - 12}" width="{TVW - 12}" '
                     f'height="18" rx="4" fill="{A1.AMBER}"/>')
            b.append(A1.txt(14, y + 2, name, 12, "#33415c", weight="bold"))
            b.append(A1.txt(TVW - 14, y + 2, "▲ 必涨", 12, "#b02020",
                            "end", "bold"))
            continue
        if star:
            b.append(f'<rect x="8" y="{y - 11}" width="{TVW - 16}" '
                     f'height="16" rx="4" fill="rgba(53,184,160,0.18)"/>')
        b.append(f'<g{op}>' +
                 A1.txt(14, y + 1, name, 10.5, A1.PAPER, weight="bold") +
                 A1.txt(TVW - 14, y + 1, arrow + pct, 10.5, color, "end",
                        "bold") + '</g>')
    b.append(f'<line x1="8" y1="22" x2="{TVW - 8}" y2="22" '
             f'stroke="#223049" stroke-width="1"/>')
    return svg_doc(TVW, TVH, "".join(b))


def build_envelope() -> str:
    """红包：红封套 + 金币圆章（无字）。"""
    return svg_doc(64, 84,
        f'<rect x="3" y="3" width="58" height="78" rx="8" '
        f'fill="#e03131" stroke="#b02020" stroke-width="3"/>' +
        f'<path d="M 3 3 L 32 30 L 61 3" fill="none" stroke="#b02020" '
        f'stroke-width="3"/>' +
        f'<circle cx="32" cy="52" r="13" fill="#ffd166" '
        f'stroke="#e0a370" stroke-width="2.5"/>' +
        f'<circle cx="32" cy="52" r="7" fill="none" stroke="#e0a370" '
        f'stroke-width="2"/>')


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
        ("第二幕 · 套消息", 30, 302, "#9aa3b2", 2),
        ("只有内幕才是钱", 108, 432, "#ffffff", 10)]))
    put("concl.svg", A1.build_card([
        ("莱茵生态，明天必涨。", 92, 380, "#ffffff", 6)]))
    put("tv_bezel.svg", build_tv_bezel())
    put("tv_screen.svg", build_tv_screen(False))
    put("tv_hot.svg", build_tv_screen(True))
    put("envelope.svg", build_envelope())
    put("flash.svg", A1.build_flash())
    # 台词气泡（同第一幕样式：白底彩边，尾巴垂向说话人头顶）
    speech = [
        ("bub0.svg", "莱茵的股票……最近有内幕吗？", "#ff6b6b"),
        ("bub1.svg", "诶？听不懂哦～", "#2ec4b6"),
        ("bub2.svg", "莱茵生态，明天，必涨。", "#2ec4b6"),
        ("bub3.svg", "嘿嘿……内幕。", "#ff6b6b"),
    ]
    for fn, text, color in speech:
        put(fn, A1.build_speech(text, color))
    put("emo0.svg", A1.W.build_emotion("💧", "#4cc9f0"))

    def mk(cid, asset, name, layer, start, end, x, y, moves=(),
           rotation=0.0, scale=1.0, kind="svg"):
        return Clip(id=cid, type=kind, asset=asset, name=name, layer=layer,
                    start=round(start, 2), end=round(end, 2), x=x, y=y,
                    scale=scale, rotation=rotation, moves=list(moves))

    clips = [
        mk("scene_bg", "scene_bg.png", "场景", 6, 0, T_END, 640, 360,
           kind="png"),
        mk("tv_bezel", "tv_bezel.svg", "电视壳", 5, 0, T_END, TV[0], TV[1]),
        mk("tv_screen", "tv_screen.svg", "电视行情", 4, 0, T_WHIS,
           TV[0], TV[1]),
        # 耳语交底瞬间：电视切高亮版（莱茵生态 → 必涨）
        mk("tv_hot", "tv_hot.svg", "电视高亮", 4, T_WHIS, T_END,
           TV[0], TV[1]),
    ]
    # 收红包得手：闪白一帧硬切
    clips.append(mk("flash1", "flash.svg", "闪白·得手", 0,
                    round(T_GIFT1 - 0.1, 2), round(T_GIFT1 - 0.02, 2),
                    640, 360))
    # 红包：抛物线两段 + 在手里停留到被收下
    clips.append(mk("envelope", "envelope.svg", "红包", -2,
                    T_GIFT0, T_GIFT1, 905, 505,
                    moves=[MoveEntry(T_GIFT0, round(T_GIFT0 + 0.5, 2),
                                     905, 505, 762, 428, -10.0, 6.0),
                           MoveEntry(round(T_GIFT0 + 0.5, 2),
                                     round(T_GIFT1 - 0.6, 2),
                                     762, 428, 618, 492, 6.0, -6.0),
                           MoveEntry(round(T_GIFT1 - 0.6, 2), T_GIFT1,
                                     618, 492, 618, 492, -6.0, -6.0)]))
    # 台词气泡（尾巴垂到说话人头顶：cx = 头x + 0.15×宽）
    bubbles = [
        ("bub0", T_ASK0, T_ASK1, C_X, "#ff6b6b"),
        ("bub1", 11.0, 14.2, M_X, "#2ec4b6"),
        ("bub2", 19.0, 22.8, M_X, "#2ec4b6"),
        ("bub3", 24.2, 26.8, C_X, "#ff6b6b"),
    ]
    for cid, s, e, hx, _c in bubbles:
        text = next(t for fn, t, _c in speech if fn == f"{cid}.svg")
        w = max(130, 44 + int(len(text) * 17.2))
        cx = round(hx + 0.15 * w, 1)
        clips.append(mk(cid, f"{cid}.svg", f"台词{cid}", -2, s, e, cx, 262,
                        rotation=-1.5,
                        moves=[MoveEntry(s, s + 0.35, cx, 242, cx, 262,
                                         5.0, -1.5)]))
    clips.append(mk("emo0", "emo0.svg", "表情汗", -2, 11.2, 13.8, 990, 300,
                    rotation=-2.0,
                    moves=[MoveEntry(11.2, 11.6, 990, 274, 990, 300,
                                     8.0, -2.0)]))

    # ---- 缪缪2号：走入 → 装傻 → 收红包 → 耳语 → 转身离场 ----
    mlyu = Clip(id="mlyu", type="spine", asset="缪缪2号", name="缪缪",
                layer=-1, start=M_WALK0, end=M_EXIT1, x=180, y=FEET_Y,
                scale=SCALE)
    mlyu.moves = [
        MoveEntry(M_WALK0, M_ARRIVE, 180, FEET_Y, M_X, FEET_Y),
        MoveEntry(M_EXIT0, M_EXIT1, M_X, FEET_Y, -180, FEET_Y),
    ]
    mlyu.anims = [
        AnimEntry(M_WALK0, M_ARRIVE, "Move", 1.0, True, False),
        AnimEntry(M_ARRIVE, T_ACT_SILLY, "Default", 1.0, True, False),
        AnimEntry(T_ACT_SILLY, 16.2, "装傻", 1.0, True, False),
        # 收红包对齐红包到手瞬间（前 0.7s 抢夹，之后反剪背后得意）
        AnimEntry(16.2, T_WHIS, "收红包", 1.0, True, False),
        AnimEntry(T_WHIS, T_WHIS_END, "耳语", 1.0, True, False),
        AnimEntry(M_EXIT0, M_EXIT1, "Move", 0.8, True, True),
    ]
    clips.append(mlyu)

    # ---- 可露希尔：潜行入场 → 开口 → 递红包 → 侧耳 → 决意定格 ----
    click = Clip(id="click", type="spine", asset="可露希尔", name="可露希尔",
                 layer=-1, start=C_WALK0, end=T_EXIT, x=1340, y=FEET_Y,
                 scale=SCALE)
    click.moves = [
        MoveEntry(C_WALK0, C_ARRIVE, 1340, FEET_Y, C_X, FEET_Y),
    ]
    click.anims = [
        AnimEntry(C_WALK0, C_ARRIVE, "潜行", 0.6, True, True),
        AnimEntry(C_ARRIVE, T_WHIS, "Default", 1.0, True, True),
        AnimEntry(T_WHIS, T_WHIS_END, "侧耳", 1.0, True, True),
        AnimEntry(M_EXIT0, T_EXIT, "决意", 1.0, True, True),
    ]
    clips.append(click)

    clips += [
        mk("title", "title.svg", "标题卡", 0, 0, T_TITLE_END, 640, 360),
        mk("concl", "concl.svg", "结论卡", 0, T_EXIT, T_END, 640, 360),
    ]

    proj.canvas = {"w": 1280, "h": 720, "fps": 30, "bg": "#d2ecdf"}
    proj.duration = T_END
    proj.layers = 8
    proj.clips = clips
    store.save(proj)
    print(f"项目「{SCENE}」：总时长 {T_END}s，{len(clips)} 片段")
    print(f"  缪缪入场 {M_WALK0}-{M_ARRIVE}s，潜行 {C_WALK0}-{C_ARRIVE}s，"
          f"红包 {T_GIFT0}-{T_GIFT1}s，耳语 {T_WHIS}-{T_WHIS_END}s，"
          f"离场 {M_EXIT0}s，结论卡 {T_EXIT}s")


if __name__ == "__main__":
    build()
