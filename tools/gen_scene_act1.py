"""生成工作区动画项目「韭菜的诞生第一幕」：可露希尔入市教育课。

第一幕（≈67s / 30fps），交代她怎么入市、为何形成「公开消息都是坑，
只有内幕才是钱」的信念，为第二幕找缪缪套消息铺路：
- 0-2.0    黑场硬切标题卡「韭菜的诞生」
- 2.0-5.4  可露希尔走入坐下；曲面屏 2.4-3.0 降下
- 3.0-9.5  新闻一：维什戴尔议长「卡兹戴尔发展前景非常好」（泰拉财经）
- 9.5-24.5 案例一「卡兹发展」分时按剧情时间分段揭示：拉升→+8% 高位横盘
- 14.2     追高进场（开心 + 委托成功），随后自信观望
- 24.6     尾盘闪崩：徽章 +8.00%→-8.00% 瞬间翻绿 + 💥 + 弹幕刷屏；
           曲线在曲面边缘「消失」（闪崩段始终不揭示）
- 26.5-33.5 曲面屏梗：前倾找线（找线）→ 抓住屏幕左右掰（掰屏幕，
           全部屏幕片段绕屏幕中心同步旋转）→ 转到 -26° 诡异角度时
           带闪崩尾段的曲线整段换入，人屏一起沉默
- 34.0-37.5 新闻二：多索雷斯啤酒「研发出猎犬病特效药」
- 37.5-49.0 案例二：高开 +5% 后温水煮青蛙阴跌，徽章台阶下翻
           （+7.2→+4.3→+1.2→-2.2→-6.4→-10.00 跌停），情绪懵→怒
- 49.2-54  暴怒拍桌 + 第二波弹幕
- 56.8-60.5 复盘：两张亏损单浮入；决意（💡→😏）
- 60.5-63.2 起身左行出画；63.2 硬切结论大字「公开消息全是坑 /
           必须搞到内幕消息。」（黑体白字，无过渡）

实现要点：
- 屏幕内容直接按舞台像素作画（576x324 帧居中锚在屏幕中心），掰屏幕
  = 所有屏幕片段由 orbit() 统一补绕屏幕中心的同步旋转条目
- 曲线揭示走分段 moves（遮罩位移 ↔ 剧情时间分段映射），弹幕/跑马灯/
  徽章全走 moves 确定性插值，可拖播放头逐帧回看
- 弹幕文本条是独立片段横移（不用 CSS 动画——那不是确定性的）
- 屏幕内跑马灯滚动一整排泰拉股票（莱茵系四只/梅什科/雷神/塞壬/企鹅/
  朝陇山；塞壬唱片与企鹅物流为「大帝系」两只联动涨跌），供暂停找梗
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
import gen_scene_watch as W  # noqa: E402  （复用房间 PNG 与人物几何常量）

SCENE = "韭菜的诞生第一幕"

# ---- 时间轴（秒） ----
T_TITLE_END = 2.0
T_WALK0, T_ARRIVE = 2.0, 5.4
T_DESC = 2.4                      # 屏幕降下 2.4-3.0
T_NEWS1, T_MKT1 = 3.0, 9.5        # 新闻一 / 案例一开盘揭示
T_CRASH = 24.6                    # 尾盘闪崩：徽章翻绿 + 💥 + 弹幕
T_TILT0 = 26.5                    # 掰屏幕开始
T_FOUND = 29.6                    # 诡异角度：带闪崩尾段的曲线换入
T_NEWS2, T_MKT2 = 34.0, 37.5      # 新闻二 / 案例二揭示（线性 11.5s）
T_LIMIT = 49.0                    # 跌停封死
T_RECV, T_STAND, T_EXIT = 56.8, 60.5, 63.2
T_CONCL_END = 66.8                # 总时长

# ---- 屏幕几何（舞台像素；帧 576x324 居中锚在屏幕中心） ----
C = (717.0, 297.0)                # 屏幕中心（显示器内容窗中心）
SW, SH = 576, 324
PLOT_X0, PLOT_Y0, PLOT_X1, PLOT_Y1 = 14, 52, 500, 244
PLOT_W, PLOT_H = PLOT_X1 - PLOT_X0, PLOT_Y1 - PLOT_Y0
MID_Y = (PLOT_Y0 + PLOT_Y1) / 2
TICK_Y = 304                      # 跑马灯中心（局部 y）

# ---- 配色（沿用看板糖果卡通风） ----
SCREEN_BG, BAR_LINE = "#0c1420", "#223049"
PLOT_BG, GRID, MIDLINE = "#f4faff", "#d8ebfb", "#ff8fa3"
INK, SUB_INK, PAPER = "#33415c", "#7fa8c9", "#eef4ff"
RED, GREEN, BLUE, AMBER = "#ff5a5f", "#2ec4b6", "#2f6fed", "#ffd166"
NEWS_RED = "#e03131"

F_TXT = "Microsoft YaHei UI, Microsoft YaHei, Segoe UI Emoji"
F_HEI = "SimHei, Microsoft YaHei"


def svg_doc(w, h, body, frame=False):
    """frame=True 时根节点声明 data-frame-clip（舞台按帧裁剪片段处理）。"""
    fc = ' data-frame-clip="1"' if frame else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
            f'height="{h}" viewBox="0 0 {w} {h}"{fc}>{body}</svg>')


def txt(x, y, s, size, fill, anchor="start", weight="normal", family=F_TXT,
        spacing=""):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}"'
            f' fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"'
            f'{sp}>{s}</text>')


# ================= 行情数据（编造的分时点：frac, 涨跌幅%） =================
# 案例一 卡兹发展（捏他平潭发展）：官宣拉升 → +8% 高位横盘 → 尾盘闪崩
CASE1 = [(0.00, 0.2), (0.06, 1.8), (0.12, 3.4), (0.18, 4.9), (0.24, 6.1),
         (0.30, 6.9), (0.36, 7.4), (0.42, 7.7), (0.48, 7.9), (0.52, 8.0),
         (0.58, 7.7), (0.64, 7.9), (0.70, 8.1), (0.76, 7.8), (0.82, 7.9),
         (0.88, 7.8), (0.92, 8.0)]
TAIL1 = [(0.92, 8.0), (0.935, -4.0), (0.95, -8.0), (0.97, -8.2), (1.00, -8.0)]
R1 = 9.0
# 案例二 多索雷斯啤酒（捏他重庆啤酒）：高开 → 温水煮青蛙阴跌 → 跌停
CASE2 = [(0.00, 5.0), (0.04, 6.3), (0.08, 7.2), (0.13, 6.9), (0.18, 6.1),
         (0.24, 5.2), (0.30, 4.3), (0.36, 3.5), (0.42, 2.7), (0.48, 1.9),
         (0.54, 1.2), (0.60, 0.4), (0.66, -0.9), (0.72, -2.2), (0.77, -3.6),
         (0.82, -5.0), (0.87, -6.4), (0.92, -7.8), (0.96, -9.1), (1.00, -10.0)]
R2 = 10.5

# 遮罩揭示 ↔ 剧情时间分段（案例一）
SEG1 = [(T_MKT1, 12.5, 0.0, 0.35), (12.5, 14.5, 0.35, 0.5),
        (14.5, 21.5, 0.5, 0.90), (21.5, 24.5, 0.90, 1.0)]


def frac_time1(f: float) -> float:
    for t0, t1, f0, f1 in SEG1:
        if f <= f1 + 1e-9:
            return t0 + (f - f0) / (f1 - f0) * (t1 - t0)
    return SEG1[-1][1]


def frac_time2(f: float) -> float:
    return T_MKT2 + f * (T_LIMIT - T_MKT2)


# 徽章序列（涨幅%, 价格, 窗口）——与揭示进度精确同步
BADGES1 = [(+0.40, "10.04", T_MKT1, frac_time1(0.24)),
           (+6.10, "10.61", frac_time1(0.24), frac_time1(0.52)),
           (+8.00, "10.80", frac_time1(0.52), T_CRASH),
           (-8.00, "9.20", T_CRASH, T_NEWS2)]
BADGES2 = [(+5.00, "21.00", T_MKT2, frac_time2(0.08)),
           (+7.20, "21.44", frac_time2(0.08), frac_time2(0.30)),
           (+4.30, "20.86", frac_time2(0.30), frac_time2(0.54)),
           (+1.20, "20.24", frac_time2(0.54), frac_time2(0.72)),
           (-2.20, "19.56", frac_time2(0.72), frac_time2(0.87)),
           (-6.40, "18.72", frac_time2(0.87), T_LIMIT),
           (-10.00, "18.00", T_LIMIT, T_EXIT)]

# 泰拉股票跑马灯（彩蛋池：塞壬唱片/企鹅物流 = 大帝系两只联动涨跌）
TICKER1 = [("卡兹发展", "+8.00%", True), ("莱茵航天", "+2.33%", False),
           ("莱茵能源", "+1.86%", False), ("莱茵生态", "-0.52%", False),
           ("莱茵科技", "+3.08%", False), ("梅什科集团", "+0.94%", False),
           ("雷神工业", "+1.27%", False), ("塞壬唱片", "+5.20%", False),
           ("企鹅物流", "+5.20%", False), ("朝陇山", "-1.11%", False)]
TICKER2 = [("多索雷斯啤酒", "-10.00%", True), ("莱茵航天", "-1.20%", False),
           ("莱茵能源", "-0.87%", False), ("莱茵生态", "+0.35%", False),
           ("莱茵科技", "-2.14%", False), ("梅什科集团", "-0.58%", False),
           ("雷神工业", "-1.66%", False), ("塞壬唱片", "-4.44%", False),
           ("企鹅物流", "-4.44%", False), ("朝陇山", "+0.72%", False),
           ("快讯：特效药研发取得重大突破", None, False)]

# 弹幕（崩盘时刷屏，用户点名的两条风味）
DM_A, DM_B = "丰蹄市变佩洛市", "建议商业联合会介入调查"
DANMAKU1 = [(DM_A, 96, T_CRASH, 26.2), (DM_B, 148, 24.8, 26.3),
            (DM_A, 196, 25.0, 26.4), (DM_B, 96, 24.95, 26.25),
            (DM_A, 148, 25.15, 26.35), (DM_B, 196, 25.3, 26.45)]
DANMAKU2 = [(DM_A, 96, 49.2, 51.4), (DM_B, 148, 49.45, 51.9),
            (DM_A, 196, 49.7, 52.4), (DM_B, 96, 49.95, 51.6),
            (DM_A, 148, 50.2, 52.1), (DM_B, 196, 50.45, 52.65)]

# 台词气泡（文本, 描边色, 窗口, 中心位）——悬在她右上方，避开屏幕内容
SPEECH = [
    ("议长亲自喊话，官宣稳了！", "#4cc9f0", 6.5, 9.0, 1120, 322),
    ("妖股气质！满仓追！", "#ff6b6b", 14.2, 16.5, 1120, 322),
    ("稳了稳了。", "#ff9f1c", 17.6, 19.6, 1120, 322),
    ("线呢？？我的线呢？！", "#4cc9f0", 25.8, 28.5, 1120, 322),
    ("啤酒厂造药？跨界之王啊……", "#b28dff", 35.0, 37.3, 1120, 322),
    ("咦，怎么还绿了……", "#2ec4b6", 46.0, 48.2, 1120, 322),
    ("别跌了别跌了！", "#ff9f1c", 48.1, 49.0, 1120, 322),
    ("公告也能坑我？！！", "#ff5a5f", 49.5, 52.0, 1120, 322),
    ("公开的全是坑……只有内幕才是钱。", "#b28dff", 58.2, 60.6, 1120, 365),
]
# 表情气泡（只留 emoji；与台词同屏时叠在台词上方，都不压人物脸）
EMOJI = [
    ("💡", "#ffd166", 6.3, 8.8, 1112, 232),
    ("🤑", "#ff9f1c", 14.3, 16.4, 1112, 232),
    ("😎", "#4cc9f0", 17.8, 19.8, 1112, 232),
    ("🫥", "#adb5bd", 30.4, 33.2, 1112, 232),
    ("🤔", "#b28dff", 34.9, 37.2, 1112, 232),
    ("😨", "#4cc9f0", 45.9, 48.0, 1112, 232),
    ("💢", "#ff5a5f", 49.4, 51.8, 1112, 232),
]

NOISE = [0.9, -0.5, 0.3, -1.1, 0.7, 1.2, -0.8, 0.4, -0.3, 1.0, -0.6, 0.2,
         1.1, -0.9, 0.5, -0.2, 0.8, -1.0, 0.6, 0.1]


# ================= SVG 构建 =================
def densify(waypoints: list, jitter: float = 0.12) -> list:
    """分位段线性插值 + 微噪声，走成一段像被交易过的分时线。"""
    out = []
    n = 150
    for i in range(n + 1):
        f = i / n
        for k in range(len(waypoints) - 1):
            f0, p0 = waypoints[k]
            f1, p1 = waypoints[k + 1]
            if f0 <= f <= f1:
                p = p0 + (p1 - p0) * (f - f0) / max(1e-9, f1 - f0)
                break
        out.append((f, p + NOISE[i % len(NOISE)] * jitter))
    out[0] = (0.0, waypoints[0][1])
    out[-1] = (1.0, waypoints[-1][1])
    return out


def build_curve(pts: list, R: float, tail: tuple | None = None) -> str:
    """整帧分时曲线：蓝线 + 面积 + 端点圆点。

    tail=(切断位, 尾段点列)：案例一「她看到的版本」曲线平淡延伸到
    曲面边缘；「诡异角度版本」从切断位起接闪崩尾段直线砸下。
    """
    full = densify(pts)
    if tail:
        cut, tpts = tail
        full = [p for p in full if p[0] <= cut] + list(tpts)

    def x(f):
        return round(PLOT_X0 + f * PLOT_W, 1)

    def y(p):
        return round(max(PLOT_Y0 + 2, min(PLOT_Y1 - 2,
                   PLOT_Y1 - (p + R) / (2 * R) * PLOT_H)), 1)

    pline = " ".join(f"{x(f)},{y(p)}" for f, p in full)
    mid = round(MID_Y, 1)
    area = (f'<path d="M{x(full[0][0])},{mid} L' +
            " L".join(f"{x(f)},{y(p)}" for f, p in full) +
            f' L{x(full[-1][0])},{mid} Z" fill="rgba(47,111,237,0.10)"/>')
    last = full[-1]
    dot_c = RED if last[1] >= 0 else GREEN
    dot = (f'<circle cx="{x(last[0])}" cy="{y(last[1])}" r="3.4" '
           f'fill="{dot_c}" stroke="#ffffff" stroke-width="1.6"/>')
    return svg_doc(SW, SH, area +
                   f'<polyline points="{pline}" fill="none" stroke="{BLUE}" '
                   f'stroke-width="2.6" stroke-linejoin="round" '
                   f'stroke-linecap="round"/>' + dot, frame=True)


def build_mask() -> str:
    """与图底同色的揭示遮罩（盖住图区，右滑露出曲线）。"""
    return svg_doc(SW, SH,
                   f'<rect x="{PLOT_X0}" y="{PLOT_Y0 - 6}" width="{PLOT_W}" '
                   f'height="{PLOT_H + 12}" rx="10" fill="{PLOT_BG}"/>', frame=True)


def build_screen(name: str, R: float) -> str:
    """屏幕静态底：顶栏（股票名）+ 图底网格 + 轴标 + 跑马灯槽。"""
    b = [f'<rect width="{SW}" height="{SH}" rx="14" fill="{SCREEN_BG}"/>']
    b.append(txt(18, 30, name, 17, PAPER, weight="bold"))
    b.append(f'<line x1="12" y1="44" x2="{SW - 12}" y2="44" '
             f'stroke="{BAR_LINE}" stroke-width="1.6"/>')
    b.append(f'<rect x="{PLOT_X0}" y="{PLOT_Y0}" width="{PLOT_W}" '
             f'height="{PLOT_H}" rx="8" fill="{PLOT_BG}"/>')
    for k in range(5):
        gy = round(PLOT_Y0 + k * PLOT_H / 4, 1)
        b.append(f'<line x1="{PLOT_X0}" y1="{gy}" x2="{PLOT_X1}" y2="{gy}" '
                 f'stroke="{GRID}" stroke-width="1.2"/>')
    for f in (0.25, 0.5, 0.75):
        gx = round(PLOT_X0 + f * PLOT_W, 1)
        b.append(f'<line x1="{gx}" y1="{PLOT_Y0}" x2="{gx}" y2="{PLOT_Y1}" '
                 f'stroke="#e2f0fa" stroke-width="1.2"/>')
    b.append(f'<line x1="{PLOT_X0}" y1="{MID_Y}" x2="{PLOT_X1}" y2="{MID_Y}" '
             f'stroke="{MIDLINE}" stroke-width="1.6" '
             f'stroke-dasharray="6 5"/>')
    for p, s in ((R, f"+{R:.1f}%"), (0.0, "0.0%"), (-R, f"-{R:.1f}%")):
        gy = round(PLOT_Y1 - (p + R) / (2 * R) * PLOT_H, 1)
        b.append(txt(PLOT_X0 + 5, gy - 4, s, 9, SUB_INK, family=F_TXT))
    b.append(txt(PLOT_X0 + 2, PLOT_Y1 + 14, "9:30", 9, SUB_INK))
    b.append(txt(PLOT_X1 - 2, PLOT_Y1 + 14, "15:00", 9, SUB_INK, "end"))
    b.append(f'<rect x="0" y="288" width="{SW}" height="36" '
             f'fill="#0a101c"/>')
    b.append(f'<line x1="0" y1="288" x2="{SW}" y2="288" '
             f'stroke="{BAR_LINE}" stroke-width="1.4"/>')
    return svg_doc(SW, SH, "".join(b), frame=True)


def build_shade() -> str:
    """曲面屏边缘暗角：盖在曲线上层，闪崩尾段「藏」在右缘之下。"""
    return svg_doc(SW, SH,
        f'<defs><linearGradient id="sr" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="#080c14" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#080c14" stop-opacity="0.32"/>'
        f'</linearGradient>'
        f'<linearGradient id="sl" x1="1" y1="0" x2="0" y2="0">'
        f'<stop offset="0" stop-color="#080c14" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#080c14" stop-opacity="0.20"/>'
        f'</linearGradient></defs>'
        f'<rect x="440" y="{PLOT_Y0}" width="60" height="{PLOT_H}" '
        f'fill="url(#sr)"/>'
        f'<rect x="{PLOT_X0}" y="{PLOT_Y0}" width="36" height="{PLOT_H}" '
        f'fill="url(#sl)"/>', frame=True)


def build_news(headline: str, sub: str) -> str:
    """泰拉财经新闻版式：红头横幅 + 大标题 + 副题（跑马灯另层滚动）。"""
    b = [f'<rect width="{SW}" height="{SH}" rx="14" fill="{SCREEN_BG}"/>']
    b.append(f'<rect x="{PLOT_X0}" y="{PLOT_Y0}" width="{PLOT_W}" '
             f'height="40" fill="{NEWS_RED}"/>')
    b.append(txt(24, 79, "泰拉财经", 18, "#ffffff", weight="bold", family=F_HEI))
    b.append(f'<rect x="118" y="62" width="44" height="20" rx="10" '
             f'fill="none" stroke="#ffffff" stroke-width="1.6"/>')
    b.append(txt(140, 76, "LIVE", 10.5, "#ffffff", "middle", "bold"))
    b.append(txt(SW / 2, 165, headline, 20, "#f4f8ff", "middle", "bold",
                 family=F_HEI))
    b.append(f'<line x1="150" y1="190" x2="{SW - 150}" y2="190" '
             f'stroke="{BAR_LINE}" stroke-width="1.6"/>')
    b.append(txt(SW / 2, 216, sub, 13, "#9fb6d8", "middle"))
    return svg_doc(SW, SH, "".join(b), frame=True)


def build_cover() -> str:
    """屏幕压边框（evenodd 三开孔：顶栏/图区/跑马灯槽）。

    压在遮罩、跑马灯、弹幕之上：滑出屏幕的一切（揭示遮罩车尾、跑马灯
    长条两端、弹幕进出场）都被裁在屏幕矩形内。填色与屏幕底同色无缝。
    """
    return svg_doc(SW, SH,
        f'<path fill-rule="evenodd" fill="{SCREEN_BG}" d="M 0 0 L {SW} 0 '
        f'L {SW} {SH} L 0 {SH} Z '
        f'M 0 0 L {SW} 0 L {SW} 46 L 0 46 Z '
        f'M {PLOT_X0} {PLOT_Y0} L {PLOT_X1} {PLOT_Y0} L {PLOT_X1} {PLOT_Y1} '
        f'L {PLOT_X0} {PLOT_Y1} Z '
        f'M 0 284 L {SW} 284 L {SW} 324 L 0 324 Z"/>', frame=True)


def build_badge(pct: float, price: str) -> str:
    """顶栏右侧现价徽章（整帧素材，随屏幕一起旋转）。"""
    up = pct >= 0
    color = RED if up else GREEN
    arrow = "▲" if up else "▼"
    big = 21 if abs(pct) < 9.9 else 19
    return svg_doc(SW, SH,
        txt(496, 31, f"{arrow}{abs(pct):.2f}%", big, color, "end", "bold") +
        txt(496, 45, price, 11, SUB_INK, "end", "bold"), frame=True)


def build_toast() -> str:
    """委托成功小卡（左上角，1.2s 硬切进出）。"""
    return svg_doc(SW, SH,
        f'<rect x="46" y="54" width="152" height="46" rx="12" '
        f'fill="#ffffff" stroke="#2eb872" stroke-width="3"/>' +
        txt(122, 84, "✓ 委托成功", 15, "#2eb872", "middle", "bold"),
        frame=True)


def build_ticker(items: list) -> tuple[str, float]:
    """全帧跑马灯：内容画在跑马灯槽（y 287-321），横移由 moves 落在内层。

    内容周期重复两份以便无缝横滚；超出画框的部分由帧裁剪裁掉。
    返回 (svg, 内容周期px)。
    """
    def one() -> tuple[str, float]:
        parts, x = [], 8.0
        for name, pct, hot in items:
            if pct is None:
                w = int(len(name) * 12.6) + 22
                parts.append(f'<rect x="{x:.0f}" y="290" width="{w}" '
                             f'height="24" rx="12" fill="rgba(255,209,102,0.16)"/>')
                parts.append(txt(x + w / 2, 307, name, 12.5, AMBER,
                                 "middle", "bold"))
                x += w + 20
                continue
            nw = int(len(name) * 12.6)
            w = nw + 62
            up = pct.startswith("+")
            arrow = "▲" if up else "▼"
            if hot:
                color = RED if up else GREEN
                parts.append(f'<rect x="{x:.0f}" y="289" width="{w}" '
                             f'height="26" rx="13" fill="{color}"/>')
                parts.append(txt(x + 9, 307, name, 12.5, "#ffffff",
                                 "start", "bold"))
                parts.append(txt(x + nw + 16, 307, arrow + pct, 12.5,
                                 "#ffffff", "start", "bold"))
            else:
                parts.append(txt(x + 9, 307, name, 12.5, PAPER,
                                 "start", "bold"))
                parts.append(txt(x + nw + 16, 307, arrow + pct, 12.5,
                                 RED if up else GREEN, "start", "bold"))
            x += w + 24
        return "".join(parts), x
    body, period = one()
    return svg_doc(SW, SH,
                   body + f'<g transform="translate({period:.0f},0)">'
                          f'{body}</g>', frame=True), period


def build_danmaku(text: str, rowy: int) -> str:
    """全帧弹幕条：药丸画在 (30, rowy) 起，横移由 moves 落在内层。"""
    w = int(len(text) * 15.5) + 30
    return svg_doc(SW, SH,
        f'<rect x="30" y="{rowy - 17}" width="{w}" height="34" rx="17" '
        f'fill="rgba(8,12,20,0.55)"/>' +
        txt(30 + w // 2, rowy + 6, text, 15, "#ffffff", "middle", "bold"),
        frame=True)


def build_speech(text: str, color: str) -> str:
    """台词气泡：白底彩边，尾巴垂向可露希尔头部（气泡悬在她右上方）。"""
    w = max(130, 44 + int(len(text) * 17.2))
    tx = int(w * 0.35)
    return svg_doc(w, 72,
        f'<rect x="2" y="2" width="{w - 4}" height="50" rx="16" '
        f'fill="#ffffff" stroke="{color}" stroke-width="3"/>' +
        f'<path d="M {tx - 20} 50 L {tx + 6} 50 L {tx - 8} 68 Z" '
        f'fill="#ffffff" stroke="{color}" stroke-width="3" '
        f'stroke-linejoin="round"/>' +
        f'<rect x="{tx - 22}" y="46" width="28" height="8" fill="#ffffff"/>' +
        txt(w / 2 - 8, 34, text, 16.5, "#4a4e69", "middle", "bold"))


def build_receipt(name: str, pct: str) -> str:
    """复盘亏损单：白卡红边 + 大幅绿色亏损数字。"""
    return svg_doc(230, 104,
        f'<rect x="3" y="3" width="224" height="98" rx="14" '
        f'fill="#ffffff" stroke="{RED}" stroke-width="3"/>' +
        txt(20, 32, name, 15, INK, weight="bold") +
        txt(210, 74, pct, 30, GREEN, "end", "bold") +
        txt(206, 34, "📉", 19, INK, "end"))


def build_card(lines: list) -> str:
    """黑场大字卡（标题/结论）：硬切进出，黑体白字无描边无渐入。"""
    body = []
    n = len(lines)
    for i, (s, size, y, color, sp) in enumerate(lines):
        body.append(txt(640, y, s, size, color, "middle", "bold", F_HEI, sp))
    return svg_doc(1280, 720,
                   f'<rect width="1280" height="720" fill="#08080e"/>' +
                   "".join(body))


def build_bezel() -> str:
    """曲面显示器外壳：粗圆角 + 内屏开孔 + 上下弧形反光暗示曲率。"""
    return svg_doc(604, 426,
        f'<rect x="2" y="2" width="600" height="422" rx="34" '
        f'fill="#3c4a63" stroke="#2b364c" stroke-width="5"/>' +
        f'<rect x="14" y="14" width="576" height="398" rx="24" '
        f'fill="#10192a"/>' +
        f'<rect x="14" y="51" width="576" height="324" rx="14" '
        f'fill="#05080f"/>' +
        f'<path d="M 60 44 Q 302 20 544 44" fill="none" '
        f'stroke="rgba(255,255,255,0.07)" stroke-width="10" '
        f'stroke-linecap="round"/>' +
        f'<path d="M 90 384 Q 302 406 514 384" fill="none" '
        f'stroke="rgba(255,255,255,0.05)" stroke-width="8" '
        f'stroke-linecap="round"/>' +
        txt(302, 418, "", 8, "#000"))


def build_giant() -> str:
    return svg_doc(170, 170, txt(85, 128, "💥", 96, INK, "middle"))


# ================= 装配 =================
def orbit(clips: list, phases: list, cx: float, cy: float,
          frame: list | None = None):
    """给屏幕片段补「绕屏幕中心同步旋转」的条目（掰屏幕）。

    phases: [(t0,t1,角度0,角度1), ...]；每段按 ≤6° 细分保证位置走弧线。
    片段既有 moves 须在首个 phase 前结束（冻结位姿作为旋转基点）。
    frame: 片段 id 集合——帧裁剪片段平移落在内层，旋转时只加 rot、
    位置（内层偏移）保持冻结。
    """
    frame = frame or set()
    for c in clips:
        px_, py_, r_prev = c.x, c.y, c.rotation
        prev = [m for m in c.moves if m.end <= phases[0][0] + 1e-6]
        if prev:
            last = max(prev, key=lambda m: m.end)
            px_, py_, r_prev = last.x1, last.y1, last.rot1
        dx, dy = px_ - cx, py_ - cy
        for t0, t1, a0, a1 in phases:
            steps = max(1, int(abs(a1 - a0) // 6) + 1)
            prev = None
            for k in range(steps + 1):
                a = a0 + (a1 - a0) * k / steps
                rad = math.radians(a)
                if c.id in frame:
                    xk, yk = px_, py_
                else:
                    xk = cx + dx * math.cos(rad) - dy * math.sin(rad)
                    yk = cy + dx * math.sin(rad) + dy * math.cos(rad)
                tk = t0 + (t1 - t0) * k / steps
                if prev is not None:
                    c.moves.append(MoveEntry(
                        round(prev[0], 2), round(tk, 2),
                        round(prev[1], 1), round(prev[2], 1),
                        round(xk, 1), round(yk, 1),
                        round(r_prev + prev[3], 1), round(r_prev + a, 1)))
                prev = (tk, xk, yk, a)


def shake(clips: list, t0: float, t1: float, amp: float, hz: float,
          frame: set, cx: float, cy: float):
    """撞击抖屏：绕屏幕中心高频小幅摆动，幅度线性衰减到 0。

    frame 集合内的片段（帧裁剪）只摆 rot；其余绕中心摆位置。
    既有 moves 须在 t0 前结束，摆完 rot 恰好归零、位置还原。
    """
    n = max(4, int((t1 - t0) * hz * 2))
    for c in clips:
        px_, py_, r_prev = c.x, c.y, c.rotation
        prev = [m for m in c.moves if m.end <= t0 + 1e-6]
        if prev:
            last = max(prev, key=lambda m: m.end)
            px_, py_, r_prev = last.x1, last.y1, last.rot1
        dx, dy = px_ - cx, py_ - cy
        for k in range(n):
            ta = round(t0 + (t1 - t0) * k / n, 3)
            tb = round(t0 + (t1 - t0) * (k + 1) / n, 3)
            aa = amp * (1 - k / n) * (1 if k % 2 == 0 else -1)
            ab = amp * (1 - (k + 1) / n) * (1 if (k + 1) % 2 == 0 else -1)
            if c.id in frame:
                x0, y0, x1, y1 = px_, py_, px_, py_
            else:
                ra, rb = math.radians(aa), math.radians(ab)
                x0 = cx + dx * math.cos(ra) - dy * math.sin(ra)
                y0 = cy + dx * math.sin(ra) + dy * math.cos(ra)
                x1 = cx + dx * math.cos(rb) - dy * math.sin(rb)
                y1 = cy + dx * math.sin(rb) + dy * math.cos(rb)
            c.moves.append(MoveEntry(
                ta, tb, round(x0, 1), round(y0, 1), round(x1, 1),
                round(y1, 1), round(r_prev + aa, 2), round(r_prev + ab, 2)))


def build_flash() -> str:
    """撞击闪白帧（硬切 2-3 帧，非渐入）。"""
    return svg_doc(1280, 720,
                   '<rect width="1280" height="720" fill="#ffffff" '
                   'fill-opacity="0.9"/>')


def build():
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        QGuiApplication([])              # QImage/QPainter 需要实例（无窗口）
    store = WorkspaceStore()
    shutil.rmtree(store.root / SCENE, ignore_errors=True)
    proj = store.create(SCENE)
    assets = store.assets_dir(SCENE)
    W.make_scene_png(assets / "scene_bg.png")
    (assets / "stool.svg").write_text(W.build_stool(), encoding="utf-8")

    def put(name: str, body: str):
        (assets / name).write_text(body, encoding="utf-8")

    put("title.svg", build_card([
        ("第一幕 · 可露希尔入市教育课", 30, 302, "#9aa3b2", 2),
        ("韭菜的诞生", 116, 432, "#ffffff", 10)]))
    put("concl.svg", build_card([
        ("公开消息全是坑", 88, 330, "#ffffff", 6),
        ("必须搞到内幕消息。", 88, 470, "#ffffff", 6)]))
    put("bezel.svg", build_bezel())
    put("flash.svg", build_flash())
    put("screen1.svg", build_screen("卡兹发展", R1))
    put("screen2.svg", build_screen("多索雷斯啤酒", R2))
    put("shade.svg", build_shade())
    put("curve1a.svg", build_curve(CASE1, R1))
    put("curve1b.svg", build_curve(CASE1, R1, (0.92, TAIL1)))
    put("curve2.svg", build_curve(CASE2, R2))
    put("mask.svg", build_mask())
    put("news1.svg", build_news("维什戴尔议长：卡兹戴尔发展前景非常好",
                                "议长公开喊话 · 卡兹发展应声大涨 · 市场情绪高涨"))
    put("news2.svg", build_news("多索雷斯啤酒：研发出猎犬病特效药",
                                "啤酒企业跨界制药 · 多索雷斯啤酒高开大涨"))
    put("cover.svg", build_cover())
    for i, (p, pr, _s, _e) in enumerate(BADGES1):
        put(f"badge1{i}.svg", build_badge(p, pr))
    for i, (p, pr, _s, _e) in enumerate(BADGES2):
        put(f"badge2{i}.svg", build_badge(p, pr))
    put("toast.svg", build_toast())
    tick1_body, tick1_period = build_ticker(TICKER1)
    tick2_body, tick2_period = build_ticker(TICKER2)
    put("tick1.svg", tick1_body)
    put("tick2.svg", tick2_body)
    put("dma96.svg", build_danmaku(DM_A, 96))
    put("dmb148.svg", build_danmaku(DM_B, 148))
    put("dma196.svg", build_danmaku(DM_A, 196))
    put("dmb96.svg", build_danmaku(DM_B, 96))
    put("dma148.svg", build_danmaku(DM_A, 148))
    put("dmb196.svg", build_danmaku(DM_B, 196))
    for i, (s, color, *_rest) in enumerate(SPEECH):
        put(f"bub{i}.svg", build_speech(s, color))
    for i, (emoji, color, *_rest) in enumerate(EMOJI):
        put(f"emo{i}.svg", W.build_emotion(emoji, color))
    put("giant.svg", build_giant())
    put("rec1.svg", build_receipt("卡兹发展", "-16.0%"))
    put("rec2.svg", build_receipt("多索雷斯啤酒", "-10.0%"))

    def mk(cid, asset, name, layer, start, end, x, y, moves=(),
           rotation=0.0, scale=1.0, kind="svg"):
        return Clip(id=cid, type=kind, asset=asset, name=name, layer=layer,
                    start=round(start, 2), end=round(end, 2), x=x, y=y,
                    scale=scale, rotation=rotation, moves=list(moves))

    # 遮罩揭示条目：位移边界 ↔ 剧情时间分段映射（位移 = 边界frac × 图宽）
    def reveal_moves(segs):
        return [MoveEntry(t0, t1, C[0] + f0 * PLOT_W, C[1],
                          C[0] + f1 * PLOT_W, C[1])
                for t0, t1, f0, f1 in segs]

    clips = [
        mk("scene_bg", "scene_bg.png", "场景", 6, 0, T_CONCL_END, 640, 360,
           kind="png"),
        mk("stool", "stool.svg", "凳子", 12, 0, T_EXIT, W.CH_X, 591),
        # ---- 屏幕（外壳/内容都锚在屏幕中心，掰屏幕统一旋转） ----
        mk("bezel", "bezel.svg", "显示器", 10, T_DESC, T_EXIT, C[0], C[1],
           moves=[MoveEntry(T_DESC, 3.0, C[0], -300, C[0], C[1])]),
        mk("screen1", "screen1.svg", "屏幕一", 9, T_DESC, T_NEWS2, C[0], C[1],
           moves=[MoveEntry(T_DESC, 3.0, C[0], -300, C[0], C[1])]),
        mk("screen2", "screen2.svg", "屏幕二", 9, T_MKT2, T_EXIT, C[0], C[1]),
        mk("shade", "shade.svg", "曲面暗角", 7, T_DESC, T_EXIT, C[0], C[1],
           moves=[MoveEntry(T_DESC, 3.0, C[0], -300, C[0], C[1])]),
        mk("curve1a", "curve1a.svg", "分时一(无尾)", 8, T_MKT1, T_FOUND,
           C[0], C[1]),
        mk("curve1b", "curve1b.svg", "分时一(带尾)", 8, T_FOUND, T_NEWS2,
           C[0], C[1]),
        mk("curve2", "curve2.svg", "分时二", 8, T_MKT2, T_EXIT, C[0], C[1]),
        mk("mask1", "mask.svg", "揭示一", 6, T_MKT1, 24.6, C[0], C[1],
           moves=reveal_moves(SEG1)),
        mk("mask2", "mask.svg", "揭示二", 6, T_MKT2, 49.2, C[0], C[1],
           moves=[MoveEntry(T_MKT2, T_LIMIT, C[0], C[1],
                            C[0] + PLOT_W, C[1])]),
        mk("news1", "news1.svg", "新闻一", 4, T_NEWS1, T_MKT1, C[0], C[1]),
        mk("news2", "news2.svg", "新闻二", 4, T_NEWS2, T_MKT2, C[0], C[1]),
        # 压边框：裁掉遮罩车尾/跑马灯长条/弹幕滑出屏幕的部分
        mk("cover", "cover.svg", "屏幕压边", 5, T_DESC, T_EXIT, C[0], C[1],
           moves=[MoveEntry(T_DESC, 3.0, C[0], -300, C[0], C[1])]),
    ]
    for i, (_p, _pr, s, e) in enumerate(BADGES1):
        clips.append(mk(f"badge1{i}", f"badge1{i}.svg", f"徽章一{i}", 4, s, e,
                        C[0], C[1]))
    for i, (_p, _pr, s, e) in enumerate(BADGES2):
        clips.append(mk(f"badge2{i}", f"badge2{i}.svg", f"徽章二{i}", 4, s, e,
                        C[0], C[1]))
    clips += [
        mk("toast1", "toast.svg", "委托一", 4, 15.0, 16.3, C[0], C[1]),
        mk("toast2", "toast.svg", "委托二", 4, 38.6, 39.9, C[0], C[1]),
        # 跑马灯：横滚一条泰拉股票街；闪崩/跌停时刻冻结
        mk("tick1", "tick1.svg", "跑马灯一", 3, T_NEWS1, T_NEWS2,
           C[0], C[1],
           moves=[MoveEntry(T_DESC + 0.6, 24.0, C[0], C[1],
                            C[0] - tick1_period * 0.75, C[1])]),
        mk("tick2", "tick2.svg", "跑马灯二", 3, T_NEWS2, T_EXIT,
           C[0], C[1],
           moves=[MoveEntry(T_NEWS2 + 0.4, T_LIMIT, C[0], C[1],
                            C[0] - (T_LIMIT - T_NEWS2 - 0.4) * 78,
                            C[1])]),
    ]
    for i, (text, lyy, s, e) in enumerate(DANMAKU1 + DANMAKU2):
        asset = {(DM_A, 96): "dma96.svg", (DM_B, 148): "dmb148.svg",
                 (DM_A, 196): "dma196.svg", (DM_B, 96): "dmb96.svg",
                 (DM_A, 148): "dma148.svg", (DM_B, 196): "dmb196.svg",
                 }[(text, lyy)]
        w = int(len(text) * 15.5) + 30
        # 帧裁剪片段：基准=帧中心，moves 即内层偏移（药丸从右缘滑进、
        # 左缘滑出，出框部分被裁）
        clips.append(mk(f"dm{i}", asset, f"弹幕{i}", 2, s, e, C[0], C[1],
                        moves=[MoveEntry(s, e, C[0] + (SW - 30), C[1],
                                         C[0] - (30 + w), C[1])]))
    for i, (_s, _c, s, e, cx, cy) in enumerate(SPEECH):
        clips.append(mk(f"bub{i}", f"bub{i}.svg", f"台词{i}", -2, s, e, cx, cy,
                        rotation=-1.5,
                        moves=[MoveEntry(s, s + 0.35, cx, cy - 20, cx, cy,
                                         5.0, -1.5)]))
    for i, (_e, _c, s, e, ex, ey) in enumerate(EMOJI):
        clips.append(mk(f"emo{i}", f"emo{i}.svg", f"表情{i}", -2, s, e, ex, ey,
                        rotation=-2.0,
                        moves=[MoveEntry(s, s + 0.4, ex, ey - 26, ex, ey,
                                         8.0, -2.0)]))
    clips += [
        mk("giant", "giant.svg", "闪崩💥", -2, T_CRASH, 25.5, C[0], C[1],
           moves=[MoveEntry(T_CRASH, T_CRASH + 0.18, C[0], C[1] - 34,
                            C[0], C[1], -14.0, 0.0)]),
        mk("rec1", "rec1.svg", "亏损单一", 1, T_RECV, T_EXIT, 920, 205,
           moves=[MoveEntry(T_RECV, T_RECV + 0.45, 920, 233, 920, 205,
                            -13.0, -5.0)]),
        mk("rec2", "rec2.svg", "亏损单二", 1, 57.3, T_EXIT, 1150, 262,
           moves=[MoveEntry(57.3, 57.75, 1150, 290, 1150, 262, 11.0, 4.0)]),
        mk("title", "title.svg", "标题卡", 0, 0, T_TITLE_END, 640, 360),
        mk("concl", "concl.svg", "结论卡", 0, T_EXIT, T_CONCL_END, 640, 360),
        # 撞击闪白帧（闪崩 / 跌停，各 2-3 帧硬切）
        mk("flash1", "flash.svg", "闪白·闪崩", 0, T_CRASH,
           round(T_CRASH + 0.08, 2), 640, 360),
        mk("flash2", "flash.svg", "闪白·跌停", 0, T_LIMIT,
           round(T_LIMIT + 0.08, 2), 640, 360),
    ]

    # ---- 掰屏幕：全部在屏片段绕屏幕中心同步旋转（含正反掰与诡异角） ----
    PHASES = [(T_TILT0, 27.6, 0.0, 18.0), (27.6, 28.8, 18.0, -18.0),
              (28.8, T_FOUND, -18.0, -26.0), (T_FOUND, 33.5, -26.0, -27.0),
              (33.5, T_NEWS2, -27.0, 0.0)]
    FRAME_IDS = {"screen1", "shade", "curve1a", "curve1b", "cover",
                 "badge13", "tick1", "screen2", "curve2", "badge26", "tick2"}
    orbit([c for c in clips if c.id in
           ("bezel", "screen1", "shade", "curve1a", "curve1b", "cover",
            "badge13", "tick1")], PHASES, C[0], C[1], frame=FRAME_IDS)
    # ---- 撞击抖屏：闪崩瞬间 / 跌停封死瞬间 ----
    shake([c for c in clips if c.id in
           ("bezel", "screen1", "shade", "curve1a", "cover", "badge13",
            "tick1")], T_CRASH, 25.05, 2.2, 14, FRAME_IDS, C[0], C[1])
    shake([c for c in clips if c.id in
           ("bezel", "screen2", "shade", "curve2", "cover", "badge26",
            "tick2")], T_LIMIT, 49.45, 2.0, 14, FRAME_IDS, C[0], C[1])

    # ---- 可露希尔：走入 → 坐 → 情绪过山车 → 起身出画 ----
    click = Clip(id="click", type="spine", asset="可露希尔", name="可露希尔",
                 layer=-1, start=0, end=T_EXIT, x=1340, y=W.FEET_Y,
                 scale=W.CLICK_SCALE)
    click.moves = [
        MoveEntry(T_WALK0, T_ARRIVE, 1340, W.FEET_Y, W.CH_X, W.FEET_Y),
        MoveEntry(T_ARRIVE, round(T_ARRIVE + 0.01, 2),
                  W.CH_X, W.FEET_Y, W.CH_X, W.SIT_Y),
        # 前倾抓屏（掰屏幕时整个人凑上去）
        MoveEntry(T_TILT0, 27.6, W.CH_X, W.SIT_Y, 1012, 560),
        MoveEntry(33.5, 34.2, 1012, 560, W.CH_X, W.SIT_Y),
        # 起身出画（接第二幕：去找内幕）
        MoveEntry(T_STAND, 60.9, W.CH_X, W.SIT_Y, 1045, 655),
        MoveEntry(60.9, T_EXIT, 1045, 655, -170, 655),
    ]
    click.anims = [
        AnimEntry(T_WALK0, T_ARRIVE, "Move", 1.0, True, True),
        AnimEntry(T_ARRIVE, 14.2, "Sit", 1.0, True, True),
        AnimEntry(14.2, 16.5, "开心", 1.0, True, True),
        AnimEntry(16.5, 24.7, "Sit", 1.0, True, True),
        AnimEntry(24.7, 25.8, "惊讶", 1.0, True, True),
        AnimEntry(25.8, T_TILT0, "找线", 1.0, True, True),
        AnimEntry(T_TILT0, T_FOUND, "掰屏幕", 1.0, True, True),
        AnimEntry(T_FOUND, 33.5, "沉默", 1.0, True, True),
        AnimEntry(33.5, 48.0, "Sit", 1.0, True, True),
        AnimEntry(48.0, 49.0, "Interact", 1.0, True, True),
        AnimEntry(49.0, 49.2, "Sit", 1.0, True, True),
        AnimEntry(49.2, 54.0, "暴怒", 1.0, True, True),
        AnimEntry(54.0, 58.0, "Sit", 1.0, True, True),
        AnimEntry(58.0, T_STAND, "决意", 1.0, True, True),
        AnimEntry(T_STAND, T_EXIT, "Move", 0.9, True, True),
    ]
    clips.append(click)

    proj.canvas = {"w": 1280, "h": 720, "fps": 30, "bg": W.WALL}
    proj.duration = T_CONCL_END
    proj.layers = 13
    proj.clips = clips
    store.save(proj)
    print(f"项目「{SCENE}」：总时长 {T_CONCL_END}s，{len(clips)} 片段")
    print(f"  案例一揭示 {T_MKT1}-24.5s（闪崩徽章 {T_CRASH}s，诡异角度 "
          f"{T_FOUND}s）")
    print(f"  案例二揭示 {T_MKT2}-{T_LIMIT}s（跌停封死），结论卡 {T_EXIT}s")


if __name__ == "__main__":
    build()
