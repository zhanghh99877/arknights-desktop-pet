"""生成工作区动画项目「明晚必涨第三幕」：可露希尔 × 缪缪（≈180s / 30fps）。

承接第二幕「莱茵生态，明天，必涨。」——内幕的兑付日：
- 0-6.0    黑场硬切标题卡「明晚必涨」
- 6.0-24.0 深夜作战室（房间烘焙成夜景，仅屏幕亮）：可露希尔根本没走，
           查 F10 档案（横盘47天/庄家装死）→ 作战计划（全仓满融梭哈）→
           「决意」搓手 + 回忆气泡（🤫“明天，必涨。”）
- 24.0-26.5 黑卡硬切「明天 09:25」（顶层 SVG，压住人物）
- 26.5-64  「明天」开盘：全仓买入 → 高开冲高 +7.9%（开心 + 弹幕造神）
           → 温水阴跌（「洗盘而已，稳住。」）
- 64.0     尾盘闪崩 -8.02%：闪白 + 抖屏 + 💥 + 恐慌弹幕（含点名风味两条）
- 64.2-76  暴怒 → 大哭打滚 → 「已清仓」（割在地板上）；缪缪 66.5 走入旁观
- 78-100   对峙戏：说好的明天必涨？！→「急什么，还没收盘呢～」→
           「拿稳，尾盘必拉。」→ 15:00 已收盘（-8.02 定格）→「红包退我！！」
           缪缪吹着口哨离场
- 104-106.5 黑卡硬切「后天 09:30」
- 106.5-158 「后天」：低开阴跌她不敢看（「不看，不看就不亏。」）→ 悄悄瞟
           → 分时一路爬升 → 132.0 涨停 +10.01%（闪白+抖屏+🚀）
           → 大哭打滚第二回 + 两日战绩单 -29.50%（含融资杠杆）
           → 缪缪再度入场「诶嘿，我说什么来着？」→ 仰望跪求再带一次
           →「红包拿来，下次教你。」→ 缪缪离场，可露希尔「决意」
           （学费交出了新心得）
- 158-180  硬切结论三连大字卡：「内幕是真的，也救不了韭菜。」/
           「拿不住的筹码，涨到天上去也与你无关。」/「第三幕 · 完」

实现要点：
- 全套屏幕机械（屏幕底/揭示遮罩/徽章/跑马灯/弹幕/闪白/抖屏）复用第一幕
  生成器；日一、日二各一条分时曲线，揭示分段与徽章窗口精确同步
- 时间黑卡用负图层 SVG（overlayTop 在顶层人物之上），中途黑场不穿帮
- 深夜房间 = 白天房间 PNG 烘焙压暗 + 屏幕冷光径向溢出（人物不沾纱）
- 新自创动作：可露希尔「仰望」（仰头合十跪求 🥺✨）、缪缪2号「得意」
  （叉腰比划 😏✌️）
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PRTS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRTS_ROOT))
sys.path.insert(0, str(PRTS_ROOT / "tools"))

from core.workspace import AnimEntry, Clip, MoveEntry, Project, WorkspaceStore  # noqa: E402
import gen_scene_act1 as A1  # noqa: E402  （屏幕全套机械/气泡/大字卡/抖屏）
import gen_scene_watch as W  # noqa: E402  （房间 PNG、凳子、表情气泡、人物常量）

SCENE = "明晚必涨第三幕"

# ---- 时间轴（秒） ----
T_TITLE_END = 6.0
T_NIGHT_END = 24.0                # 深夜段结束（黑卡起）
T_CARD1_0, T_CARD1_1 = 24.0, 26.5
T_DAY = 26.5                      # 「明天」开盘
T_BUY = 27.0                      # 全仓委托成功
T_PEAK0, T_PEAK1 = 36.5, 46.3     # +7.90% 徽章窗口
T_SLIDE0 = 58.0                   # 阴跌加速（惊讶）
T_CRASH = 64.0                    # 尾盘闪崩 -8.02%
M_IN0, M_IN1 = 66.5, 71.5         # 缪缪入场旁观
T_ROLL0, T_ROLL1 = 70.0, 76.0     # 大哭打滚（第一回）
T_SELL = 71.0                     # 已清仓（割在地板）
T_ASK0 = 78.0                     # 对峙开始
T_STAMP = 97.2                    # 15:00 已收盘
M_OUT0, M_OUT1 = 100.5, 104.0     # 缪缪离场
T_CARD2_0, T_CARD2_1 = 104.0, 106.5
T_DAY2 = 106.5                    # 「后天」开盘
T_LIMIT = 132.0                   # 涨停 +10.01%
T_ROLL2_0, T_ROLL2_1 = 132.4, 139.0
M2_IN0, M2_IN1 = 140.2, 145.5     # 缪缪二度入场
T_BEG0, T_BEG1 = 146.0, 152.0     # 仰望跪求
M2_OUT0, M2_OUT1 = 154.5, 157.8
T_EXIT = 158.0                    # 可露希尔定格退场 & 结论卡
T_END = 180.0

# ---- 屏幕几何（沿用第一幕） ----
C = A1.C
SW, SH = A1.SW, A1.SH
PLOT_W = A1.PLOT_W
R = 10.0                          # 日内振幅轴 ±10%

# ---- 台词气泡（文本, 描边色, 窗口, 中心位；teal=缪缪口吻） ----
SPEECH = [
    ("🤫“明天，必涨。”", "#2ec4b6", 18.4, 22.8, 1120, 322),
    ("洗盘而已，稳住。", "#ff9f1c", 48.0, 52.0, 1120, 322),
    ("说好的明天必涨呢？！", "#ff5a5f", 78.0, 82.5, 1120, 322),
    ("急什么，还没收盘呢～", "#2ec4b6", 83.5, 87.5, None, 266),
    ("现在是洗盘，拿稳——尾盘必拉。", "#2ec4b6", 88.0, 92.5, None, 266),
    ("骗子！！红包退我！！", "#ff5a5f", 97.5, 100.5, 1120, 322),
    ("不看，不看就不亏。", "#4cc9f0", 108.0, 112.0, 1120, 322),
    ("诶嘿，我说什么来着？", "#2ec4b6", 145.8, 150.0, None, 266),
    ("再给一次内幕！这把我拿得住！", "#ff6b6b", 147.0, 151.5, 1120, 322),
    ("红包拿来，下次教你。", "#2ec4b6", 151.5, 155.0, None, 266),
]
M_HEAD_X = 380.0                  # 缪缪站位（屏幕左侧空地）

# 表情气泡（只留 emoji）
EMOJI = [
    ("😎", "#4cc9f0", 29.0, 33.0),
    ("😅", "#ff9f1c", 48.2, 52.0),
    ("😨", "#4cc9f0", 57.0, 61.5),
    ("🫥", "#adb5bd", 76.5, 80.0),
    ("🌧️", "#4cc9f0", 108.0, 112.0),
    ("😨", "#b28dff", 118.5, 122.5),
    ("😭", "#4cc9f0", 133.0, 137.0),
    ("🤑", "#ff9f1c", 147.0, 150.5),
]

# ---- 分时数据（编造；日一=冲高闪崩洗盘，日二=爬升涨停） ----
CASE_D1 = [(0.00, 0.2), (0.05, 2.8), (0.11, 3.9), (0.17, 4.6), (0.22, 5.2),
           (0.27, 6.4), (0.33, 7.1), (0.42, 7.9), (0.47, 6.9), (0.53, 5.5),
           (0.60, 4.1), (0.66, 2.4), (0.72, 1.2), (0.77, -0.6), (0.82, -1.8),
           (0.86, -3.4), (0.88, -5.6), (0.93, -8.02), (1.00, -8.02)]
SEG_D1 = [(T_DAY, 34.0, 0.0, 0.22), (34.0, 44.0, 0.22, 0.42),
          (44.0, 58.0, 0.42, 0.72), (58.0, 63.5, 0.72, 0.88),
          (64.0, 64.9, 0.88, 1.0)]
CASE_D2 = [(0.00, 0.0), (0.04, -1.2), (0.10, -0.5), (0.18, 1.1), (0.26, 2.1),
           (0.36, 3.4), (0.46, 4.5), (0.56, 5.9), (0.66, 7.2), (0.76, 8.6),
           (0.80, 9.4), (0.90, 9.7), (0.95, 9.9), (1.00, 10.01)]
SEG_D2 = [(T_DAY2, 115.0, 0.0, 0.18), (115.0, 125.0, 0.18, 0.46),
          (125.0, 131.0, 0.46, 0.80), (132.0, 133.2, 0.80, 1.0)]

# 徽章（涨幅%, 价格, 窗口）——揭示分段同步，前收 24.00 / 22.08
BADGES_D1 = [(+2.80, "24.67", T_DAY, 28.2), (+5.20, "25.25", 28.2, 36.5),
             (+7.90, "25.90", 36.5, 46.3), (+4.10, "24.98", 46.3, 58.0),
             (-1.80, "23.57", 58.0, 63.5), (-8.02, "22.08", 64.0, 104.0)]
BADGES_D2 = [(-1.20, "21.82", T_DAY2, 110.0), (+1.10, "22.32", 110.0, 117.9),
             (+2.10, "22.54", 117.9, 125.0), (+4.50, "23.07", 125.0, 128.5),
             (+7.20, "23.67", 128.5, 131.0), (+9.70, "24.22", 131.0, 132.0),
             (+10.01, "24.29", 132.0, T_EXIT)]

# 泰拉股票跑马灯（大帝系塞壬/企鹅继续同涨同跌）
TICKER_N = [("莱茵生态", "-0.52%", True), ("莱茵航天", "+0.31%", False),
            ("莱茵能源", "-0.20%", False), ("莱茵科技", "+0.15%", False),
            ("塞壬唱片", "+0.05%", False), ("企鹅物流", "+0.05%", False),
            ("朝陇山", "-0.11%", False),
            ("晚间快讯：莱茵生态连续 47 日横盘", None, False)]
TICKER_D1 = [("莱茵生态", "+5.90%", True), ("莱茵航天", "+1.20%", False),
             ("莱茵能源", "+0.87%", False), ("莱茵科技", "+2.14%", False),
             ("梅什科集团", "+0.51%", False), ("雷神工业", "-0.83%", False),
             ("塞壬唱片", "+2.20%", False), ("企鹅物流", "+2.20%", False),
             ("朝陇山", "+0.42%", False),
             ("快讯：缪缪主任：生态舱量产进展顺利", None, False)]
TICKER_D2 = [("莱茵生态", "+10.01%", True), ("莱茵航天", "+0.80%", False),
             ("莱茵能源", "+1.10%", False), ("莱茵科技", "+0.64%", False),
             ("梅什科集团", "+0.33%", False), ("雷神工业", "+0.91%", False),
             ("塞壬唱片", "+10.01%", False), ("企鹅物流", "+10.01%", False),
             ("朝陇山", "-0.58%", False),
             ("快讯：大帝亲自喊单：全仓！满上！", None, False)]

# 弹幕四波（文本池, 起始, 条间隔, 单条时长, 行高轮换）
DM_WAVES = [
    (["缪姐yyds", "跟着缪缪有肉吃", "满仓满融冲冲冲", "莱茵生态起飞",
      "信缪姐得永生", "这波稳了"], 34.0, 0.5, 3.2),
    (["慌不慌？", "主力洗盘而已", "拿稳千万别割", "割了就真成韭菜了",
      "稳住能赢", "绿是暂时的"], 50.0, 0.5, 3.2),
    (["跳水了！！", "缪姐救命", "说好的内幕呢", "丰蹄市变佩洛市",
      "建议商业联合会介入调查", "跑！快跑！"], T_CRASH, 0.22, 1.8),
    (["涨停了", "一卖就涨", "刚割就起飞", "天台排队叫号",
      "建议可露希尔退市", "杠杆双倍痛"], T_LIMIT, 0.45, 2.8),
]
DM_ROWS = [96, 148, 196, 96, 148, 196]


# ================= 局部构建 =================
def frac_time_d1(f: float) -> float:
    for t0, t1, f0, f1 in SEG_D1:
        if f <= f1 + 1e-9:
            return t0 + (f - f0) / (f1 - f0) * (t1 - t0)
    return SEG_D1[-1][1]


def frac_time_d2(f: float) -> float:
    for t0, t1, f0, f1 in SEG_D2:
        if f <= f1 + 1e-9:
            return t0 + (f - f0) / (f1 - f0) * (t1 - t0)
    return SEG_D2[-1][1]


def reveal_moves(segs):
    return [MoveEntry(t0, t1, C[0] + f0 * PLOT_W, C[1],
                      C[0] + f1 * PLOT_W, C[1])
            for t0, t1, f0, f1 in segs]


def build_toast_t(text: str, color: str) -> str:
    """委托/成交小卡（左上角，硬切进出）。"""
    w = 46 + int(len(text) * 15.5)
    return A1.svg_doc(SW, SH,
        f'<rect x="46" y="54" width="{w}" height="46" rx="12" '
        f'fill="#ffffff" stroke="{color}" stroke-width="3"/>' +
        A1.txt(46 + w / 2, 84, text, 15, color, "middle", "bold"),
        frame=True)


def build_giant_e(emoji: str) -> str:
    return A1.svg_doc(170, 170, A1.txt(85, 128, emoji, 96, A1.INK, "middle"))


def build_chip() -> str:
    """深夜角落时间牌：23:47 · 泰拉标准时。"""
    return A1.svg_doc(210, 40,
        f'<rect x="2" y="2" width="206" height="36" rx="12" '
        f'fill="rgba(4,8,18,0.66)"/>' +
        A1.txt(105, 26, "23:47 · 泰拉标准时", 14.5, "#cfe0ff",
               "middle", "bold"))


def build_stamp() -> str:
    """15:00 已收盘 小牌（图区右上角）。"""
    return A1.svg_doc(SW, SH,
        f'<rect x="356" y="56" width="140" height="32" rx="10" '
        f'fill="{A1.AMBER}"/>' +
        A1.txt(426, 78, "15:00 已收盘", 14, "#33415c", "middle", "bold"),
        frame=True)


def build_info1() -> str:
    """深夜 F10 档案页：全帧暗底 + 资料行 + 横盘微线。"""
    rows = [("▍主业：新一代生态舱（即将量产*）", A1.PAPER),
            ("▍近 47 日振幅 2.1%——庄家装死中", A1.PAPER),
            ("▍流通盘：极小。好拉。", A1.PAPER),
            ("▍龙虎榜：无机构，全是散户", A1.PAPER),
            ("▍概念：莱茵系 + 大帝系 + 万能蹭", A1.AMBER)]
    b = [f'<rect width="{SW}" height="{SH}" rx="14" fill="{A1.SCREEN_BG}"/>']
    b.append(A1.txt(20, 34, "莱茵生态 · F10 档案", 18, "#7fd4e8",
                    weight="bold", family=A1.F_HEI))
    b.append(f'<line x1="14" y1="48" x2="{SW - 14}" y2="48" '
             f'stroke="{A1.BAR_LINE}" stroke-width="1.6"/>')
    for i, (s, c) in enumerate(rows):
        b.append(A1.txt(22, 80 + i * 30, s, 14, c))
    # 横盘微线（资料行下方，避开文字与底部跑马灯槽）
    pts = " ".join(f"{14 + i * 4.6:.0f},{224 + (i % 3) * 3 - 4}"
                   for i in range(100))
    b.append(f'<polyline points="{pts}" fill="none" stroke="{A1.BLUE}" '
             f'stroke-width="2"/>')
    b.append(A1.txt(22, 252, "横盘 47 天", 12, A1.SUB_INK))
    b.append(A1.txt(22, 278, "*来源：股吧小作文。不构成投资建议（真的）。",
                    10.5, A1.SUB_INK))
    return A1.svg_doc(SW, SH, "".join(b), frame=True)


def build_info2() -> str:
    """深夜作战计划页：资金清单 + 梭哈大按钮。"""
    b = [f'<rect width="{SW}" height="{SH}" rx="14" fill="{A1.SCREEN_BG}"/>']
    b.append(A1.txt(20, 34, "作战计划 · 终极版", 18, A1.NEWS_RED,
                    weight="bold", family=A1.F_HEI))
    b.append(f'<line x1="14" y1="48" x2="{SW - 14}" y2="48" '
             f'stroke="{A1.BAR_LINE}" stroke-width="1.6"/>')
    for i, s in enumerate(("可用资金　¥1,024,473",
                           "红包支出　-¥666（肉痛）",
                           "融资额度　×5（不用白不用）",
                           "目标收益　翻！倍！")):
        b.append(A1.txt(22, 82 + i * 30, s, 14.5, A1.PAPER))
    b.append(f'<rect x="128" y="216" width="320" height="52" rx="26" '
             f'fill="{A1.NEWS_RED}"/>')
    b.append(A1.txt(288, 250, "全仓！满融！梭哈！", 22, "#ffffff",
                    "middle", "bold", A1.F_HEI))
    b.append(A1.txt(22, 278, "风险提示：无（本人拒绝查看）", 10.5,
                    A1.SUB_INK))
    return A1.svg_doc(SW, SH, "".join(b), frame=True)


def make_night_png(path: Path, day_path: Path):
    """深夜房间：白天房间压暗烘焙 + 屏幕冷光径向溢出（人物不沾纱）。"""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QRadialGradient

    img = QImage(str(day_path))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(0, 0, 1280, 720, QColor(8, 14, 32, 152))
    grad = QRadialGradient(QPointF(717, 310), 430)
    grad.setColorAt(0.0, QColor(130, 170, 255, 72))
    grad.setColorAt(1.0, QColor(130, 170, 255, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawEllipse(QPointF(717, 310), 430, 330)
    p.end()
    img.save(str(path), "PNG")


# ================= 装配 =================
def build():
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        QGuiApplication([])              # QImage/QPainter 需要实例（无窗口）
    store = WorkspaceStore()
    shutil.rmtree(store.root / SCENE, ignore_errors=True)
    proj = store.create(SCENE)
    assets = store.assets_dir(SCENE)
    W.make_scene_png(assets / "scene_bg_day.png")
    make_night_png(assets / "scene_bg_night.png", assets / "scene_bg_day.png")
    (assets / "stool.svg").write_text(W.build_stool(), encoding="utf-8")

    def put(name: str, body: str):
        (assets / name).write_text(body, encoding="utf-8")

    put("title.svg", A1.build_card([
        ("第三幕 · 内幕的代价", 30, 302, "#9aa3b2", 2),
        ("明晚必涨", 116, 432, "#ffffff", 10)]))
    put("card1.svg", A1.build_card([("明天 09:25", 64, 380, "#ffffff", 6)]))
    put("card2.svg", A1.build_card([("后天 09:30", 64, 380, "#ffffff", 6)]))
    put("conclA.svg", A1.build_card([
        ("内幕是真的，", 84, 330, "#ffffff", 6),
        ("也救不了韭菜。", 84, 470, "#ffffff", 6)]))
    put("conclB.svg", A1.build_card([
        ("拿不住的筹码，", 84, 330, "#ffffff", 6),
        ("涨到天上去也与你无关。", 72, 470, "#ffffff", 6)]))
    put("conclC.svg", A1.build_card([("第三幕 · 完", 48, 390, "#9aa3b2", 8)]))
    put("bezel.svg", A1.build_bezel())
    put("flash.svg", A1.build_flash())
    put("screen.svg", A1.build_screen("莱茵生态", R))
    put("shade.svg", A1.build_shade())
    put("curve1.svg", A1.build_curve(CASE_D1, R))
    put("curve2.svg", A1.build_curve(CASE_D2, R))
    put("mask.svg", A1.build_mask())
    put("cover.svg", A1.build_cover())
    put("info1.svg", build_info1())
    put("info2.svg", build_info2())
    put("stamp.svg", build_stamp())
    put("chip.svg", build_chip())
    put("toast1.svg", build_toast_t("✓ 全仓买入 · 满融", "#2eb872"))
    put("toast2.svg", build_toast_t("✗ 已清仓 -8.02%", A1.NEWS_RED))
    for i, (p, pr, _s, _e) in enumerate(BADGES_D1):
        put(f"badge1{i}.svg", A1.build_badge(p, pr))
    for i, (p, pr, _s, _e) in enumerate(BADGES_D2):
        put(f"badge2{i}.svg", A1.build_badge(p, pr))
    for tag, items in (("n", TICKER_N), ("1", TICKER_D1), ("2", TICKER_D2)):
        body, _period = A1.build_ticker(items)
        put(f"tick{tag}.svg", body)
    put("giant1.svg", A1.build_giant())
    put("giant2.svg", build_giant_e("🚀"))
    put("rec1.svg", A1.build_receipt("莱茵生态 · 满融", "-29.50%"))
    dm_assets = {}
    k = 0
    for texts, t0, gap, dur in DM_WAVES:
        for i, text in enumerate(texts):
            rowy = DM_ROWS[i]
            key = (text, rowy)
            if key not in dm_assets:
                fn = f"dm{k}.svg"
                dm_assets[key] = fn
                put(fn, A1.build_danmaku(text, rowy))
                k += 1
    for i, (s, color, *_rest) in enumerate(SPEECH):
        put(f"bub{i}.svg", A1.build_speech(s, color))
    for i, (emoji, color, *_rest) in enumerate(EMOJI):
        put(f"emo{i}.svg", W.build_emotion(emoji, color))

    def mk(cid, asset, name, layer, start, end, x, y, moves=(),
           rotation=0.0, scale=1.0, kind="svg"):
        return Clip(id=cid, type=kind, asset=asset, name=name, layer=layer,
                    start=round(start, 2), end=round(end, 2), x=x, y=y,
                    scale=scale, rotation=rotation, moves=list(moves))

    # 屏幕降下（深夜开场 6.0-6.6）：外壳/资料页/夜间跑马灯/暗角一起
    drop = [MoveEntry(T_TITLE_END, 6.6, C[0], -300, C[0], C[1])]
    clips = [
        mk("scene_night", "scene_bg_night.png", "深夜房间", 6, 0, T_CARD1_0,
           640, 360, kind="png"),
        mk("scene_day", "scene_bg_day.png", "白天房间", 6, T_CARD1_0, T_END,
           640, 360, kind="png"),
        mk("stool", "stool.svg", "凳子", 12, T_TITLE_END, T_EXIT,
           W.CH_X, 591),
        mk("chip", "chip.svg", "时间牌", 0, T_TITLE_END, T_NIGHT_END,
           120, 40),
        # ---- 屏幕（外壳整段连续，内容按日夜切换） ----
        mk("bezel", "bezel.svg", "显示器", 10, T_TITLE_END, T_EXIT,
           C[0], C[1], moves=list(drop)),
        mk("info1", "info1.svg", "F10档案", 4, T_TITLE_END, 12.0,
           C[0], C[1], moves=list(drop)),
        mk("info2", "info2.svg", "作战计划", 4, 12.0, T_NIGHT_END,
           C[0], C[1]),
        mk("tickn", "tickn.svg", "跑马灯·夜", 3, 6.6, T_NIGHT_END,
           C[0], C[1],
           moves=[MoveEntry(6.8, 23.5, C[0], C[1],
                            C[0] - (23.5 - 6.8) * 72, C[1])]),
        mk("screen", "screen.svg", "屏幕底", 9, T_DAY, T_EXIT, C[0], C[1]),
        mk("shade", "shade.svg", "曲面暗角", 7, T_TITLE_END, T_EXIT,
           C[0], C[1], moves=list(drop)),
        mk("curve1", "curve1.svg", "分时·明天", 8, T_DAY, T_CARD2_0,
           C[0], C[1]),
        mk("mask1", "mask.svg", "揭示·明天", 6, T_DAY, T_CARD2_0,
           C[0], C[1], moves=reveal_moves(SEG_D1)),
        mk("curve2", "curve2.svg", "分时·后天", 8, T_DAY2, T_EXIT,
           C[0], C[1]),
        mk("mask2", "mask.svg", "揭示·后天", 6, T_DAY2, T_EXIT,
           C[0], C[1], moves=reveal_moves(SEG_D2)),
        mk("cover", "cover.svg", "屏幕压边", 5, T_DAY, T_EXIT, C[0], C[1]),
    ]
    for i, (_p, _pr, s, e) in enumerate(BADGES_D1):
        clips.append(mk(f"b1{i}", f"badge1{i}.svg", f"徽章日一{i}", 4, s, e,
                        C[0], C[1]))
    for i, (_p, _pr, s, e) in enumerate(BADGES_D2):
        clips.append(mk(f"b2{i}", f"badge2{i}.svg", f"徽章日二{i}", 4, s, e,
                        C[0], C[1]))
    clips += [
        mk("toast1", "toast1.svg", "委托卡", 4, T_BUY, 28.4, C[0], C[1]),
        mk("toast2", "toast2.svg", "清仓卡", 4, T_SELL, 74.0, C[0], C[1]),
        mk("stamp", "stamp.svg", "收盘牌", 4, T_STAMP, T_CARD2_0,
           C[0], C[1]),
        mk("tick1", "tick1.svg", "跑马灯·明天", 3, T_DAY, T_CARD2_0,
           C[0], C[1],
           moves=[MoveEntry(27.0, 63.5, C[0], C[1],
                            C[0] - (63.5 - 27.0) * 88, C[1])]),
        mk("tick2", "tick2.svg", "跑马灯·后天", 3, T_DAY2, T_EXIT,
           C[0], C[1],
           moves=[MoveEntry(107.0, 131.5, C[0], C[1],
                            C[0] - (131.5 - 107.0) * 92, C[1])]),
    ]
    # 弹幕四波：帧裁剪片段，基准=帧中心，药丸右进左出
    k = 0
    for texts, t0, gap, dur in DM_WAVES:
        for i, text in enumerate(texts):
            rowy = DM_ROWS[i]
            asset = dm_assets[(text, rowy)]
            w = int(len(text) * 15.5) + 30
            s = round(t0 + i * gap, 2)
            e = round(s + dur, 2)
            clips.append(mk(f"dm{k}", asset, f"弹幕{k}", 2, s, e, C[0], C[1],
                            moves=[MoveEntry(s, e, C[0] + (SW - 30), C[1],
                                             C[0] - (30 + w), C[1])]))
            k += 1
    for i, (_s, _c, s, e, cx, cy) in enumerate(SPEECH):
        if cx is None:                   # 缪缪台词：悬在她右上方
            text = SPEECH[i][0]
            w = max(130, 44 + int(len(text) * 17.2))
            cx = round(M_HEAD_X + 0.15 * w, 1)
        clips.append(mk(f"bub{i}", f"bub{i}.svg", f"台词{i}", -2, s, e, cx, cy,
                        rotation=-1.5,
                        moves=[MoveEntry(s, s + 0.35, cx, cy - 20, cx, cy,
                                         5.0, -1.5)]))
    for i, (_e, _c, s, e) in enumerate(EMOJI):
        clips.append(mk(f"emo{i}", f"emo{i}.svg", f"表情{i}", -2, s, e,
                        1112, 232, rotation=-2.0,
                        moves=[MoveEntry(s, s + 0.4, 1112, 206, 1112, 232,
                                         8.0, -2.0)]))
    clips += [
        mk("giant1", "giant1.svg", "闪崩💥", -2, T_CRASH, 65.4, C[0], C[1],
           moves=[MoveEntry(T_CRASH, T_CRASH + 0.18, C[0], C[1] - 34,
                            C[0], C[1], -14.0, 0.0)]),
        mk("giant2", "giant2.svg", "涨停🚀", -2, T_LIMIT, 133.8, C[0], C[1],
           moves=[MoveEntry(T_LIMIT, T_LIMIT + 0.18, C[0], C[1] - 34,
                            C[0], C[1], -14.0, 0.0)]),
        mk("rec1", "rec1.svg", "战绩单", 1, 136.4, 152.0, 940, 240,
           moves=[MoveEntry(136.4, 136.85, 940, 268, 940, 240, -12.0, -4.0)]),
        mk("title", "title.svg", "标题卡", 0, 0, T_TITLE_END, 640, 360),
        mk("card1", "card1.svg", "时间卡·明天", -2, T_CARD1_0, T_CARD1_1,
           640, 360),
        mk("card2", "card2.svg", "时间卡·后天", -2, T_CARD2_0, T_CARD2_1,
           640, 360),
        mk("conclA", "conclA.svg", "结论卡一", 0, T_EXIT, 166.5, 640, 360),
        mk("conclB", "conclB.svg", "结论卡二", 0, 166.5, 174.5, 640, 360),
        mk("conclC", "conclC.svg", "完", 0, 174.5, T_END, 640, 360),
        mk("flash1", "flash.svg", "闪白·闪崩", 0, T_CRASH,
           round(T_CRASH + 0.08, 2), 640, 360),
        mk("flash2", "flash.svg", "闪白·涨停", 0, T_LIMIT,
           round(T_LIMIT + 0.08, 2), 640, 360),
    ]

    # ---- 停车条目：无 moves 的屏幕片段先钉一段 rot=0 静止位姿， ----
    # ---- 否则 shake 追加的首条目会被钳位成首帧姿态（凭空歪 2.2°） ----
    park1 = MoveEntry(T_DAY, 63.9, C[0], C[1], C[0], C[1], 0.0, 0.0)
    for _cid in ("screen", "cover", "curve1"):
        next(c for c in clips if c.id == _cid).moves.append(park1)
    next(c for c in clips if c.id == "curve2").moves.append(
        MoveEntry(T_DAY2, 131.9, C[0], C[1], C[0], C[1], 0.0, 0.0))

    # ---- 撞击抖屏：闪崩 64.0 / 涨停 132.0（既有 moves 须已结束） ----
    FRAME1 = {"screen", "shade", "curve1", "cover", "b15", "tick1"}
    shake_ids1 = ["bezel", "screen", "shade", "curve1", "cover", "b15",
                  "tick1"]
    A1.shake([c for c in clips if c.id in shake_ids1],
          T_CRASH, 64.45, 2.2, 14, FRAME1, C[0], C[1])
    FRAME2 = {"screen", "shade", "curve2", "cover", "b26", "tick2"}
    shake_ids2 = ["bezel", "screen", "shade", "curve2", "cover", "b26",
                  "tick2"]
    A1.shake([c for c in clips if c.id in shake_ids2],
          T_LIMIT, 132.45, 2.0, 14, FRAME2, C[0], C[1])

    # ---- 可露希尔：熬夜没走 → 情绪过山车两轮 → 决意定格 ----
    click = Clip(id="click", type="spine", asset="可露希尔", name="可露希尔",
                 layer=-1, start=T_TITLE_END, end=T_EXIT,
                 x=W.CH_X, y=W.SIT_Y, scale=W.CLICK_SCALE)
    click.anims = [
        AnimEntry(T_TITLE_END, 18.2, "Sit", 1.0, True, True),
        AnimEntry(18.2, 23.5, "决意", 1.0, True, True),
        AnimEntry(23.5, 27.5, "Sit", 1.0, True, True),
        AnimEntry(27.5, 33.5, "开心", 1.0, True, True),
        AnimEntry(33.5, 48.0, "Sit", 1.0, True, True),
        AnimEntry(48.0, 51.5, "Interact", 1.0, True, True),
        AnimEntry(51.5, 56.0, "Sit", 1.0, True, True),
        AnimEntry(56.0, 63.8, "惊讶", 1.0, True, True),
        AnimEntry(63.8, 70.0, "暴怒", 1.0, True, True),
        AnimEntry(T_ROLL0, T_ROLL1, "大哭打滚", 1.0, True, True),
        AnimEntry(T_ROLL1, T_ASK0, "Sit", 1.0, True, True),
        AnimEntry(T_ASK0, 84.0, "暴怒", 1.0, True, True),
        AnimEntry(84.0, 97.0, "沉默", 1.0, True, True),
        AnimEntry(97.0, 100.5, "暴怒", 1.0, True, True),
        AnimEntry(100.5, 106.5, "沉默", 1.0, True, True),
        AnimEntry(106.5, 118.0, "Sit", 1.0, True, True),
        AnimEntry(118.0, 124.0, "惊讶", 1.0, True, True),
        AnimEntry(124.0, 132.4, "Sit", 1.0, True, True),
        AnimEntry(T_ROLL2_0, T_ROLL2_1, "大哭打滚", 1.0, True, True),
        AnimEntry(T_ROLL2_1, T_BEG0, "Sit", 1.0, True, True),
        AnimEntry(T_BEG0, T_BEG1, "仰望", 1.0, True, True),
        AnimEntry(T_BEG1, T_EXIT, "决意", 1.0, True, True),
    ]
    clips.append(click)

    # ---- 缪缪2号：闪崩后飘入旁观 → 拖字诀 → 吹口哨离场 → 后天再来讨红包 ----
    mlyu = Clip(id="mlyu", type="spine", asset="缪缪2号", name="缪缪",
                layer=-1, start=M_IN0, end=M2_OUT1, x=-80, y=W.FEET_Y,
                scale=W.CLICK_SCALE)
    mlyu.moves = [
        MoveEntry(M_IN0, M_IN1, -80, W.FEET_Y, M_HEAD_X, W.FEET_Y),
        MoveEntry(M_OUT0, M_OUT1, M_HEAD_X, W.FEET_Y, -160, W.FEET_Y),
        MoveEntry(M2_IN0, M2_IN1, -80, W.FEET_Y, M_HEAD_X, W.FEET_Y),
        MoveEntry(M2_OUT0, M2_OUT1, M_HEAD_X, W.FEET_Y, -160, W.FEET_Y),
    ]
    mlyu.anims = [
        AnimEntry(M_IN0, M_IN1, "Move", 1.0, True, False),
        AnimEntry(M_IN1, 84.0, "Default", 1.0, True, False),
        AnimEntry(84.0, 88.0, "装傻", 1.0, True, False),
        AnimEntry(88.0, 93.0, "耳语", 1.0, True, False),
        AnimEntry(93.0, M_OUT0, "Default", 1.0, True, False),
        AnimEntry(M_OUT0, M_OUT1, "Move", 0.85, True, True),
        AnimEntry(M2_IN0, M2_IN1, "Move", 1.0, True, False),
        AnimEntry(M2_IN1, M2_OUT0, "得意", 1.0, True, False),
        AnimEntry(M2_OUT0, M2_OUT1, "Move", 0.85, True, True),
    ]
    clips.append(mlyu)

    proj.canvas = {"w": 1280, "h": 720, "fps": 30, "bg": W.WALL}
    proj.duration = T_END
    proj.layers = 14
    proj.clips = clips
    store.save(proj)
    print(f"项目「{SCENE}」：总时长 {T_END}s，{len(clips)} 片段")
    print(f"  深夜 6-24s → 明天 {T_DAY}s（闪崩 {T_CRASH}s，对峙 {T_ASK0}s，"
          f"收盘 {T_STAMP}s）→ 后天 {T_DAY2}s（涨停 {T_LIMIT}s，仰望 "
          f"{T_BEG0}s）→ 结论卡 {T_EXIT}s")


if __name__ == "__main__":
    build()
