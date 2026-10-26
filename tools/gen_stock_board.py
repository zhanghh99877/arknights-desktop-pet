"""生成工作区看板动画「航天工程分时」：分时图定格动画（卡通风）。

数据：
- 主图分钟线：优先东财 klt=5（48 点/日，历史深；整域易限流），失败退回
  新浪 15 分钟线（16 点/日，datalen 上限约 1600）
- 全部 6 只股票日线（新浪 scale=240）→ 每日收盘/涨跌幅（持仓榜 + 昨收基准）

看板结构（可嵌入场景：board_clips() 支持时间平移 t0 与仿射 k/ox/oy）：
- 每天 1.9s（½ 速）一帧硬切翻页：日期贴纸落下 → 遮罩右滑、曲线从左往右
  画出（1s）→ 现价徽章跳出 + 台词气泡弹出，右侧 5 张数字卡刷成当天数据
- 图层（0 最上）：贴纸/气泡 / 数字卡 / 刻度标签+侧栏底板 / 遮罩 / 曲线 / 底板
- 遮罩停车点：左缘停在图区右缘（796），尾部藏在侧栏底板与加宽图底之下
- 全部动效走 moves 确定性插值：拖播放头可逐帧回看，导出与预览一致
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

PRTS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRTS_ROOT))

from core.workspace import AnimEntry, Clip, MoveEntry, Project, WorkspaceStore  # noqa: E402

PROJECT = "航天工程分时0717"
WEEK = ["2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16",
        "2026-07-17"]
MAIN = ("航天工程", "1.603698")
SIDEBAR = [("德明利", "0.001309"), ("宿迁联盛", "1.603065"),
           ("合肥城建", "0.002208"), ("中际旭创", "0.300308"),
           ("生益科技", "1.600183")]
WEEKDAY = "一二三四五六日"

# 展示用架空名（数据仍按真实名拉取）
RENAME = {"航天工程": "谢拉格航天", "中际旭创": "雷神光电",
          "宿迁联盛": "大兔激光", "生益科技": "莱茵微电",
          "德明利": "百灶烟花", "合肥城建": "卡兹城建"}


def dn(name: str) -> str:
    return RENAME.get(name, name)

# 乐景衬哀情：7/10 涨停大笑 → 一路跌停到大哭麻木 → 强制平仓
CAPTIONS = {
    "2026-07-10": "满仓梭哈！涨停了！ 🤑",
    "2026-07-13": "？？？跌停了？？ 😲",
    "2026-07-14": "别慌，只是技术性调整 🥲",
    "2026-07-15": "呜呜呜……不看了 🥺",
    "2026-07-16": "麻了。随便吧。 🫥",
    "2026-07-17": "又双叒跌停了…… 😱",
}
DAY_COLORS = ["#ff6b6b", "#ff9f1c", "#f9c74f", "#06d6a0", "#4cc9f0",
              "#b28dff"]

# ---- 布局（1280x720 看板坐标） ----
PLOT_L, PLOT_T, PLOT_W, PLOT_H = 56, 120, 560, 400   # 分时区（收窄让位侧栏）
VOL_T, VOL_H = 545, 100                              # 量能区（全局 y）
PANEL_X = 632                                        # 侧栏面板左缘（紧贴图区）
CARD_X = 1157                                        # 侧栏数字卡中心 x
ROW_Y0, ROW_STEP, ROW_H = 100, 121, 108              # 侧栏行
PARK_CX = 640 + PLOT_W // 2                          # 遮罩停车（整车藏进面板下）

# ---- 卡通配色 ----
SKY = "#cdeeff"                       # 画布天空蓝
PANEL, PANEL_EDGE = "#ffffff", "#ff9f1c"
PLOT_BG, GRID, MIDLINE = "#f4faff", "#d8ebfb", "#ff8fa3"
INK, SUB_INK = "#33415c", "#7fa8c9"
RED, GREEN = "#ff5a5f", "#2ec4b6"
LINE_C, AVG_C = "#2f6fed", "#ff9f1c"
ROW_TINTS = ["#fff0f3", "#eef7ff", "#fff9e8", "#f0fff7", "#f6f0ff"]
RANK_COLORS = ["#ffd166", "#ff9f1c", "#e0a370", "#4cc9f0", "#adb5bd"]

F_TITLE = "Microsoft YaHei, PingFang SC, sans-serif"         # 正常字体
F_NUM = "Microsoft YaHei, PingFang SC, sans-serif"           # 正常字体
F_BODY = "Microsoft YaHei UI, Microsoft YaHei, sans-serif"

# 嵌入小屏幕时放大字号保可读（独立看板全屏显示保持 1.0）
FONT_BOOST = 1.0


def fs(x: float) -> float:
    return round(x * FONT_BOOST, 1)

INTRO, FRAME, TAIL = 1.6, 3.8, 1.4   # 开场 / 每天帧长（¼速）/ 收尾定格
REVEAL = 2.0                          # 曲线揭示时长


# ================= 数据 =================
def _sina_symbol(secid: str) -> str:
    mkt, code = secid.split(".")
    return ("sh" if mkt == "1" else "sz") + code


def _http(url: str, headers: dict, tries: int, gap: float) -> bytes:
    for i in range(tries):
        try:
            time.sleep(gap)
            req = urllib.request.Request(url, headers=headers)
            return urllib.request.urlopen(req, timeout=20).read()
        except Exception as e:                      # noqa: BLE001
            print(f"  请求失败({e})，重试 {i + 1}/{tries}")
            time.sleep(6 * (i + 1))
    raise RuntimeError("数据源不可用：" + url)


UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}


def fetch_intraday() -> tuple[dict, str]:
    """分钟线：东财 5 分钟优先（带成交额），退回新浪 15 分钟。

    返回 {日: [[hh:mm,o,c,h,l,vol,vwap], ...]}，vwap=0 表示无（用收盘近似）。
    """
    try:
        url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
               f"?secid={MAIN[1]}&fields1=f1,f2,f3"
               f"&fields2=f51,f52,f53,f54,f55,f56,f57"
               f"&klt=5&fqt=0&end=20500101&lmt=6000")
        raw = _http(url, {**UA, "Referer": "https://quote.eastmoney.com/"},
                    tries=2, gap=2.5)
        d = json.loads(raw)["data"]["klines"]
        out = {}
        for row in d:
            f = row.split(",")
            day = f[0][:10]
            if day not in WEEK:
                continue
            o, c, h, low = (float(f[1]), float(f[2]), float(f[3]), float(f[4]))
            vol, amt = float(f[5]), float(f[6])
            vwap = amt / (vol * 100) if amt > 0 and vol > 0 else 0.0
            out.setdefault(day, []).append(
                [f[0][11:16], o, c, h, low, vol, vwap])
        if out:
            return out, "东财 5 分钟线"
        raise RuntimeError("东财返回空")
    except Exception as e:                          # noqa: BLE001
        print(f"  东财 5 分钟线不可用（{e}），退回新浪 15 分钟线")
    url = (f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_k=/"
           f"CN_MarketDataService.getKLineData?symbol={_sina_symbol(MAIN[1])}"
           f"&scale=15&ma=no&datalen=1300")
    raw = _http(url, {**UA, "Referer": "https://finance.sina.com.cn"},
                tries=5, gap=2.0).decode("utf-8", "replace")
    m = re.search(r"=\((\[.*\])\)", raw, re.S)
    if not m:
        raise RuntimeError("新浪分钟线解析失败")
    out = {}
    for k in json.loads(m.group(1)):
        d = k["day"]
        if d[:10] in WEEK:
            out.setdefault(d[:10], []).append(
                [d[11:16], float(k["open"]), float(k["close"]),
                 float(k["high"]), float(k["low"]), float(k["volume"]), 0.0])
    return out, "新浪 15 分钟线"


def fetch_daily() -> dict:
    daily = {}
    for name, secid in [MAIN] + SIDEBAR:
        url = (f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_k=/"
               f"CN_MarketDataService.getKLineData?symbol={_sina_symbol(secid)}"
               f"&scale=240&ma=no&datalen=200")
        raw = _http(url, {**UA, "Referer": "https://finance.sina.com.cn"},
                    tries=5, gap=2.0).decode("utf-8", "replace")
        m = re.search(r"=\((\[.*\])\)", raw, re.S)
        daily[name] = {}
        prev = None
        for k in json.loads(m.group(1)):
            d, close = k["day"][:10], float(k["close"])
            pct = (close / prev - 1) * 100 if prev else 0.0
            daily[name][d] = {"close": close, "pct": pct, "prev": prev}
            prev = close
    return daily


def fetch_all() -> dict:
    intraday, src = fetch_intraday()
    print(f"  分钟线来源：{src}")
    return {"intraday": intraday, "daily": fetch_daily()}


# ================= SVG =================
def svg_doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
            f'height="{h}" viewBox="0 0 {w} {h}">{body}</svg>')


def txt(x, y, s, size, fill, anchor="start", weight="normal", family=F_BODY):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{s}</text>')


def fmt_date(d: str) -> str:
    m, day = d.split("-")[1:]
    return f"{m}-{day} 周{WEEKDAY[date.fromisoformat(d).weekday()]}"


def day_range_m(bars: list, pc: float) -> float:
    """分时 y 量程半幅：绕昨收对称，最小 0.4%。"""
    return max(max(b[3] for b in bars) - pc,
               pc - min(b[4] for b in bars), pc * 0.004)


def build_chrome_main() -> str:
    """主区底板：面板、图底（延到 632 接侧栏）、网格、太阳云朵。

    不画全画布天空底：独立项目的画布 bg 即天空色；嵌入场景时透出
    宿主背景。
    """
    b = [f'<rect x="16" y="16" width="616" height="688" rx="24" '
         f'fill="{PANEL}" stroke="{PANEL_EDGE}" stroke-width="3"/>']
    b.append(f'<line x1="40" y1="96" x2="608" y2="96" stroke="#ffe3c2" '
             f'stroke-width="3"/>')
    b.append(f'<rect x="{PLOT_L}" y="{PLOT_T}" width="576" '
             f'height="{PLOT_H}" rx="12" fill="{PLOT_BG}"/>')
    # 笑脸太阳（图区左上，遮罩揭示时最先露出）
    sx, sy = 128, 182
    b.append(f'<circle cx="{sx}" cy="{sy}" r="30" fill="#ffd166" '
             f'stroke="#f4a259" stroke-width="3"/>')
    import math
    for i in range(8):
        a = i * math.pi / 4
        b.append(f'<line x1="{sx + 38 * math.cos(a):.0f}" '
                 f'y1="{sy + 38 * math.sin(a):.0f}" '
                 f'x2="{sx + 50 * math.cos(a):.0f}" '
                 f'y2="{sy + 50 * math.sin(a):.0f}" stroke="#f4a259" '
                 f'stroke-width="4" stroke-linecap="round"/>')
    b.append(f'<circle cx="{sx - 10}" cy="{sy - 6}" r="3.2" fill="#5c4218"/>'
             f'<circle cx="{sx + 10}" cy="{sy - 6}" r="3.2" fill="#5c4218"/>'
             f'<path d="M {sx - 11} {sy + 6} Q {sx} {sy + 16} {sx + 11} '
             f'{sy + 6}" fill="none" stroke="#5c4218" stroke-width="3" '
             f'stroke-linecap="round"/>')
    for cx, cy, s in ((470, 172, 0.75), (300, 214, 0.5)):
        b.append(f'<g fill="#ffffff" stroke="#d5ecfa" stroke-width="2.5">'
                 f'<ellipse cx="{cx}" cy="{cy}" rx="{46 * s}" ry="{20 * s}"/>'
                 f'<ellipse cx="{cx - 30 * s}" cy="{cy + 6 * s}" '
                 f'rx="{28 * s}" ry="{14 * s}"/>'
                 f'<ellipse cx="{cx + 32 * s}" cy="{cy + 5 * s}" '
                 f'rx="{30 * s}" ry="{15 * s}"/></g>')
    for gy in (PLOT_T, PLOT_T + 100, PLOT_T + 300, PLOT_T + 400):
        b.append(f'<line x1="{PLOT_L}" y1="{gy}" x2="{PLOT_L + PLOT_W}" '
                 f'y2="{gy}" stroke="{GRID}" stroke-width="1.5"/>')
    b.append(f'<line x1="{PLOT_L}" y1="{PLOT_T + 200}" '
             f'x2="{PLOT_L + PLOT_W}" y2="{PLOT_T + 200}" stroke="{MIDLINE}" '
             f'stroke-width="2" stroke-dasharray="7 6"/>')
    return svg_doc(1280, 720, "".join(b))


def build_chrome_side(sidebar_rows: list[tuple[str, str]]) -> str:
    """侧栏底板（持仓股票；面板加宽到画布缘，遮罩整车停在其下）。"""
    pw = 1264 - PANEL_X
    b = [f'<rect x="{PANEL_X}" y="16" width="{pw}" height="688" rx="24" '
         f'fill="{PANEL}" stroke="#4cc9f0" stroke-width="3"/>']
    b.append(txt(656, 52, "持仓股票", fs(26), "#ff6b6b", weight="bold",
                 family=F_TITLE))
    for i, (name, _code) in enumerate(sidebar_rows):
        ry = ROW_Y0 + i * ROW_STEP
        cy = ry + ROW_H // 2
        b.append(f'<rect x="648" y="{ry}" width="600" height="{ROW_H}" '
                 f'rx="16" fill="{ROW_TINTS[i % 5]}" stroke="#ffffff" '
                 f'stroke-width="2.5"/>')
        b.append(f'<circle cx="688" cy="{cy}" r="17" '
                 f'fill="{RANK_COLORS[i]}" stroke="#ffffff" '
                 f'stroke-width="2.5"/>')
        b.append(txt(688, cy + 6, str(i + 1), fs(16), "#ffffff", "middle",
                     "bold", F_NUM))
        b.append(txt(716, cy - 4, dn(name), fs(21), INK, weight="bold"))
    return svg_doc(1280, 720, "".join(b))


def build_curve(day_bars: list, pc: float) -> str:
    """一天的分时：蓝线 + 面积 + 橙均价线 + 圆角量能柱（svg 本地坐标）。"""
    n = len(day_bars)
    m = day_range_m(day_bars, pc)

    def y(p):
        return max(4.0, min(PLOT_H - 4.0,
                            PLOT_H - (p - (pc - m)) / (2 * m) * PLOT_H))

    step = PLOT_W / (n - 1)
    pts = [(round(i * step, 1), round(y(b[2]), 1))
           for i, b in enumerate(day_bars)]
    pline = " ".join(f"{x},{yy}" for x, yy in pts)
    mid = PLOT_H / 2
    area = (f'<path d="M{pts[0][0]},{mid} L' +
            " L".join(f"{x},{yy}" for x, yy in pts) +
            f' L{pts[-1][0]},{mid} Z" fill="rgba(47,111,237,0.13)"/>')
    b = [area, f'<polyline points="{pline}" fill="none" stroke="{LINE_C}" '
               f'stroke-width="3" stroke-linejoin="round" '
               f'stroke-linecap="round"/>']
    # 均价线：有 vwap 用成交额加权，否则以每根收盘价近似
    cv, cw = 0.0, 0.0
    vpts = []
    for i, bar in enumerate(day_bars):
        v = bar[6] if bar[6] > 0 else bar[2]
        cv += bar[5]
        cw += v * bar[5]
        if cv > 0:
            vpts.append((round(i * step, 1), round(y(cw / cv), 1)))
    if len(vpts) > 1:
        b.append(f'<polyline points="'
                 + " ".join(f"{x},{yy}" for x, yy in vpts) +
                 f'" fill="none" stroke="{AVG_C}" stroke-width="2" '
                 f'stroke-dasharray="1 5" stroke-linecap="round" '
                 f'opacity="0.95"/>')
    vmax = max(bar[5] for bar in day_bars) or 1
    bw = max(4, PLOT_W / n - 5)
    for i, bar in enumerate(day_bars):
        h = max(2, bar[5] / vmax * VOL_H)
        color = RED if bar[2] >= bar[1] else GREEN
        b.append(f'<rect x="{round(i * step - bw / 2, 1)}" '
                 f'y="{round(525 - h, 1)}" width="{round(bw, 1)}" '
                 f'height="{round(h, 1)}" rx="2.5" fill="{color}" '
                 f'opacity="0.8"/>')
    return svg_doc(PLOT_W, 560, "".join(b))


def build_labels(pc: float, m: float) -> str:
    """左价格轴 / 右涨跌幅轴 / 底部时间轴（网格五档 = pc±m, pc±m/2）。"""
    b = []
    r = m / pc * 100
    lev = [(pc + m, f"+{r:.2f}%"), (pc + m / 2, f"+{r / 2:.2f}%"),
           (pc, "0.00%"), (pc - m / 2, f"-{r / 2:.2f}%"),
           (pc - m, f"-{r:.2f}%")]
    for k_, (price, pct) in enumerate(lev):
        yy = 15 + k_ * 100
        b.append(txt(6, yy, f"{price:.2f}", fs(15), SUB_INK, family=F_NUM))
        b.append(txt(PLOT_W - 6, yy, pct, fs(15), SUB_INK, "end",
                     family=F_NUM))
    for fx, s, a in ((0, "9:30", "start"), (0.25, "10:30", "middle"),
                     (0.5, "11:30/13:00", "middle"),
                     (0.75, "14:00", "middle"), (1.0, "15:00", "end")):
        b.append(txt(PLOT_W * fx, 548, s, fs(15), SUB_INK, a, family=F_NUM))
    return svg_doc(PLOT_W, 580, "".join(b))


def build_date_badge(day: str, color: str) -> str:
    """日期贴纸：糖果色药丸 + 白描边，最终姿态歪 -3°（贴纸感）。"""
    return svg_doc(186, 50,
        f'<rect x="2" y="2" width="180" height="46" rx="23" fill="{color}" '
        f'stroke="#ffffff" stroke-width="3"/>' +
        txt(92, 33, fmt_date(day), fs(21), "#ffffff", "middle",
            family=F_TITLE))


def build_price_badge(close: float, pct: float) -> str:
    """现价签：上下两行堆叠（窄签，避开日期贴纸与侧栏面板）。"""
    up = pct >= 0
    color = RED if up else GREEN
    arrow = "▲" if up else "▼"
    return svg_doc(170, 60,
        txt(164, 26, f"{close:.2f}", fs(30), INK, "end", "bold", F_NUM) +
        txt(164, 52, f"{arrow}{abs(pct):.2f}%", fs(23), color, "end", "bold",
            F_NUM))


def build_caption(day: str, color: str) -> str:
    """台词气泡（乐景衬哀情）：白底彩边 + 小尾巴，随字数自适应宽。"""
    text = CAPTIONS.get(day, "")
    w = max(190, 36 + int(len(text) * fs(19) * 0.92))
    tw = max(56, int(w * 0.2))                       # 尾巴随宽度内移
    return svg_doc(w, 76,
        f'<rect x="2" y="2" width="{w - 4}" height="56" rx="18" '
        f'fill="#ffffff" stroke="{color}" stroke-width="3"/>' +
        f'<path d="M {tw - 22} 58 L {tw} 58 L {tw - 16} 74 Z" '
        f'fill="#ffffff" stroke="{color}" stroke-width="3" '
        f'stroke-linejoin="round"/>' +
        f'<rect x="{tw - 24}" y="52" width="28" height="10" '
        f'fill="#ffffff"/>' +
        txt(w // 2, 37, text, fs(19), "#4a4e69", "middle", "bold"))


def build_card(close: float, pct: float) -> str:
    color = RED if pct >= 0 else GREEN
    return svg_doc(150, 64,
        txt(146, 27, f"{close:.2f}", fs(20), INK, "end", "bold", F_NUM) +
        txt(146, 53, f"{pct:+.2f}%", fs(19), color, "end", "bold", F_NUM))


# ================= 看板片段（可嵌入场景） =================
def board_clips(assets_dir: Path, data: dict, days: list, rows: list,
                t0: float = 0.0, intro: float | None = None,
                frame: float | None = None, tail: float | None = None,
                k: float = 1.0, ox: float = 0.0, oy: float = 0.0,
                prefix: str = "", panel_to_edge: bool = False,
                exit: float | None = None) -> tuple[list[Clip], float]:
    """生成看板片段并写素材，返回 (clips, 总时长)。

    t0 起播时刻；k/ox/oy 把 1280x720 看板坐标仿射进宿主场景。
    """
    intro = INTRO if intro is None else intro
    frame = FRAME if frame is None else frame
    tail = TAIL if tail is None else tail
    duration = round(t0 + intro + len(days) * frame + tail, 2)
    t = (lambda x: round(t0 + x, 2))

    def px(x):
        return round(ox + x * k, 1)

    def py(y):
        return round(oy + y * k, 1)

    def mv(e: MoveEntry) -> MoveEntry:
        return MoveEntry(t(e.start), t(e.end),
                         px(e.x0), py(e.y0), px(e.x1), py(e.y1),
                         e.rot0, e.rot1)

    def clip(cid, asset, name, layer, start, end, x, y, moves=(),
             rotation=0.0):
        ms = [mv(e) for e in moves]
        if exit is not None:
            # 片尾整体上飞：从当前位置（末条目终点或基准位）同步滑出画布
            lx, ly = (ms[-1].x1, ms[-1].y1) if ms else (px(x), py(y))
            ms.append(MoveEntry(t(exit), t(exit + 0.8),
                                lx, ly, lx, ly - 800))
        return Clip(id=prefix + cid, type="svg", asset=prefix + asset,
                    name=name, layer=layer, start=t(start), end=t(end),
                    x=px(x), y=py(y), scale=k, rotation=rotation,
                    moves=ms)

    last = days[-1]
    (assets_dir / f"{prefix}chrome_main.svg").write_text(
        build_chrome_main(), encoding="utf-8")
    (assets_dir / f"{prefix}chrome_side.svg").write_text(
        build_chrome_side([(n, c) for n, c, _ in rows]), encoding="utf-8")
    (assets_dir / f"{prefix}title.svg").write_text(svg_doc(470, 66,
        txt(6, 34, dn(MAIN[0]), fs(29), "#ff6b6b", weight="bold")),
        encoding="utf-8")

    clips = [
        clip("chrome_main", "chrome_main.svg", "主区底板", 5, 0, duration,
             640, 360),
        clip("chrome_side", "chrome_side.svg", "侧栏底板", 2, 0, duration,
             640, 360),
        clip("title", "title.svg", "标题", 4, 0, duration, 255, 58,
             moves=[MoveEntry(0, intro, 195, 58, 255, 58)]),
    ]
    for i, day in enumerate(days):
        bars = data["intraday"][day]
        d = data["daily"][MAIN[0]][day]
        pc, close, pct = d["prev"], d["close"], d["pct"]
        if pc is None:
            pc = bars[0][1]
        color = DAY_COLORS[i % len(DAY_COLORS)]
        T = intro + i * frame
        E = duration - t0 if i == len(days) - 1 else T + frame
        (assets_dir / f"{prefix}curve{i}.svg").write_text(
            build_curve(bars, pc), encoding="utf-8")
        (assets_dir / f"{prefix}mask{i}.svg").write_text(
            svg_doc(PLOT_W, 560,
                    f'<rect width="{PLOT_W}" height="404" rx="12" '
                    f'fill="{PLOT_BG}"/>'
                    f'<rect y="400" width="{PLOT_W}" height="160" '
                    f'fill="{PANEL}"/>'), encoding="utf-8")
        (assets_dir / f"{prefix}labels{i}.svg").write_text(
            build_labels(pc, day_range_m(bars, pc)), encoding="utf-8")
        (assets_dir / f"{prefix}dateb{i}.svg").write_text(
            build_date_badge(day, color), encoding="utf-8")
        (assets_dir / f"{prefix}priceb{i}.svg").write_text(
            build_price_badge(close, pct), encoding="utf-8")
        (assets_dir / f"{prefix}cap{i}.svg").write_text(
            build_caption(day, color), encoding="utf-8")
        cx, cy = PLOT_L + PLOT_W / 2, PLOT_T + 280
        r0, r1 = 0.2, 0.2 + REVEAL
        clips += [
            clip(f"curve{i}", f"curve{i}.svg", f"分时 {day}", 4, T, E, cx, cy),
            # 遮罩右滑 → 曲线从左往右画出；左缘停在 796（车尾藏侧栏底板下）
            clip(f"mask{i}", f"mask{i}.svg", f"遮罩 {day}", 3, T, E, cx, cy,
                 moves=[MoveEntry(T + r0, T + r1, cx, cy, PARK_CX, cy)]),
            clip(f"labels{i}", f"labels{i}.svg", f"刻度 {day}", 2, T, E,
                 cx, PLOT_T + 290),
            clip(f"dateb{i}", f"dateb{i}.svg", f"日期 {day}", 0, T, E,
                 505, 56, rotation=-3.0,
                 moves=[MoveEntry(T, T + 0.6, 505, 26, 505, 56, -12.0, -3.0)]),
            # 现价签放标题原股票代码位置
            clip(f"priceb{i}", f"priceb{i}.svg", f"现价 {day}", 0,
                 T + 2.0, E, 300, 58,
                 moves=[MoveEntry(T + 2.0, T + 2.5, 272, 58, 300, 58)]),
            # 台词气泡：图区中部空白带（避开左价格轴/右百分比轴/曲线）
            clip(f"cap{i}", f"cap{i}.svg", f"台词 {day}", 0,
                 T + 2.3, E, 290, 330 if i == 0 else 148, rotation=2.0,
                 moves=[MoveEntry(T + 2.3, T + 3.0, 290,
                                  (330 if i == 0 else 148) - 22,
                                  290, 330 if i == 0 else 148,
                                  10.0, 2.0)]),
        ]
        for j, (name, code, per_day) in enumerate(rows):
            rclose, rpct = per_day.get(day, per_day[last])
            fn = f"{prefix}card{i}_{j}.svg"
            (assets_dir / fn).write_text(build_card(rclose, rpct),
                                         encoding="utf-8")
            y = ROW_Y0 + j * ROW_STEP + ROW_H // 2
            clips.append(clip(
                f"card{i}_{j}", f"card{i}_{j}.svg", f"{dn(name)} {day[5:]}", 1,
                T + 0.3, E, CARD_X, y,
                moves=[MoveEntry(T + 0.3, T + 0.9, CARD_X + 40, y,
                                 CARD_X, y)]))
    return clips, duration


def load_rows(data: dict, days: list) -> list:
    """侧栏固定顺序：按最后一天跌幅排序；数值逐日取自 daily。"""
    last = days[-1]
    return sorted(
        ((n, c, {d: (data["daily"][n][d]["close"], data["daily"][n][d]["pct"])
                 for d in days if d in data["daily"].get(n, {})})
         for n, c in SIDEBAR if last in data["daily"].get(n, {})),
        key=lambda r: r[2][last][1])


# ================= 独立看板项目 =================
def build():
    store = WorkspaceStore()
    cache = store.root / PROJECT / "_data.json"
    if cache.exists() and "--refresh" not in sys.argv:
        data = json.loads(cache.read_text(encoding="utf-8"))
        print("使用缓存数据 _data.json（--refresh 强制重拉）")
    else:
        print("拉取数据…")
        data = fetch_all()
        cache.parent.mkdir(parents=True, exist_ok=True)
    days = [d for d in WEEK if data["intraday"].get(d)]
    if not days:
        raise RuntimeError("没拉到分钟数据")
    for d in days:
        print(f"  {d}: {len(data['intraday'][d])} 根分钟K")
    rows = load_rows(data, days)

    shutil.rmtree(store.root / PROJECT, ignore_errors=True)
    proj = store.create(PROJECT)
    clips, duration = board_clips(store.assets_dir(PROJECT), data, days, rows)
    cache.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    proj.canvas = {"w": 1280, "h": 720, "fps": 30, "bg": SKY}
    proj.duration = duration
    proj.layers = 6
    proj.clips = clips
    store.save(proj)
    print(f"项目「{PROJECT}」：{len(days)} 天 × {FRAME}s，总时长 {duration}s，"
          f"{len(clips)} 片段")
    for j, (n, c, per_day) in enumerate(rows):
        cl, p = per_day[days[0]]
        print(f"  {j + 1}. {n}  首日 {cl:.2f} {p:+.2f}% → 末日 "
              f"{per_day[days[-1]][0]:.2f} {per_day[days[-1]][1]:+.2f}%")


if __name__ == "__main__":
    build()
