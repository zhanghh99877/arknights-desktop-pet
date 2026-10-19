"""时间轴：标尺 + 图层行（子通道纵向扩展）+ 片段块 + 播放头。自绘 QWidget。

图层 = 行：行 0 在最上面（z 最上层）。同一行内时间段重叠的片段自动分到
不同子通道纵向铺开（区间图染色），单条高度 20px，行高随子通道数伸缩。
行首有 显/隐 眼睛开关（点击切换图层可见性）。

片段块颜色：spine 蓝 / png 绿 / svg 紫。拖动语义：中部=整体平移（连带
anims/moves 条目，Qt 侧负责），左右 6px 边缘=裁剪起止，标尺区=拖播放头。
外部把本控件放进 QScrollArea 实现纵向滚动（见 content_height()）。
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui.stage_view import MIME_ASSET

RULER_H = 26
LANE_H = 20            # 单条片段高度
LANE_GAP = 2
ROW_PAD = 3
LABEL_W = 64
EYE_W = 22
COLORS = {"spine": QColor("#2f8cff"), "png": QColor("#2ea44f"),
          "svg": QColor("#b15fd3")}
BG_ROW = QColor("#f7fafd")
BG_ROW_ALT = QColor("#eef4fa")
BG_BASE = QColor("#e8edf3")
BORDER = QColor("#cfd9e4")
PLAYHEAD = QColor("#e5534b")
SEL_BORDER = QColor("#ffb020")

_STEPS = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120]


class Timeline(QWidget):
    seek = Signal(float)                 # 播放头拖动（实时）
    selected = Signal(str)               # 选中片段（'' = 取消）
    moved = Signal(str, float)           # 片段整体平移：id, 时间增量（秒）
    trimmed = Signal(str, float, float)  # 裁剪起止：id, start, end
    assetDropped = Signal(str, str, int, float)  # kind, name, 图层行, 时间秒
    layerVisibilityToggled = Signal(int)         # 眼睛开关：图层行号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 5.0
        self._layers = 3
        self._clips: list[dict] = []
        self._sel = ""
        self._playhead = 0.0
        self._pps = 80.0
        self._visible = []           # 每行可见标志（[] = 全可见）
        self._drag = None
        self._row_tops: list[int] = []
        self._row_heights: list[int] = []
        self._lane_of: dict[str, int] = {}
        self.setMinimumWidth(400)

    # ---- 数据 ----
    def set_data(self, duration: float, layers: int, clips: list[dict],
                 selection: str = "", visible: list | None = None):
        self._duration = max(0.5, float(duration))
        self._layers = max(1, int(layers))
        self._clips = clips
        self._sel = selection
        self._visible = list(visible) if visible else [True] * self._layers
        self._relayout()
        self.update()

    def _relayout(self):
        """计算每行 top/高度与片段子通道分配（区间图染色：重叠的纵向铺开）。"""
        self._row_tops = []
        self._row_heights = []
        self._lane_of = {}
        y = RULER_H
        for row in range(self._layers):
            self._row_tops.append(y)
            clips = sorted(
                (c for c in self._clips if int(c.get("layer", 0)) == row),
                key=lambda c: float(c.get("start", 0)))
            lane_ends: list[float] = []
            for c in clips:
                s = float(c.get("start", 0))
                e = float(c.get("end", 0))
                for li, le in enumerate(lane_ends):
                    if le <= s + 1e-9:
                        lane_ends[li] = e
                        self._lane_of[c.get("id", "")] = li
                        break
                else:
                    lane_ends.append(e)
                    self._lane_of[c.get("id", "")] = len(lane_ends) - 1
            lanes = max(1, len(lane_ends))
            h = lanes * (LANE_H + LANE_GAP) + 2 * ROW_PAD
            self._row_heights.append(h)
            y += h
        self.setFixedHeight(y + 2)

    def content_height(self) -> int:
        return self.height()

    def set_playhead(self, t: float):
        self._playhead = max(0.0, t)
        self.update()

    def set_selection(self, clip_id: str):
        self._sel = clip_id
        self.update()

    # ---- 坐标 ----
    def _x(self, t: float) -> float:
        return LABEL_W + t * self._pps

    def _t(self, x: float) -> float:
        return max(0.0, (x - LABEL_W) / self._pps)

    def _step(self) -> float:
        for s in _STEPS:
            if s * self._pps >= 56:
                return s
        return _STEPS[-1]

    def _row_at(self, y: float) -> int:
        for row in range(self._layers):
            if self._row_tops[row] <= y < self._row_tops[row] + self._row_heights[row]:
                return row
        return -1

    def _is_visible(self, row: int) -> bool:
        return row >= len(self._visible) or self._visible[row]

    # ---- 绘制 ----
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, BG_BASE)

        # 标尺
        p.fillRect(0, 0, w, RULER_H, QColor("#dde5ee"))
        step = self._step()
        t = 0.0
        p.setPen(QPen(QColor("#7c8896")))
        while t <= self._duration + 1e-9:
            x = self._x(t)
            if x > w:
                break
            p.drawLine(int(x), RULER_H - 7, int(x), RULER_H)
            p.drawText(QRectF(x - 40, 1, 80, 15),
                       Qt.AlignmentFlag.AlignHCenter, f"{t:g}")
            t += step
        p.setPen(QPen(BORDER))
        p.drawLine(0, RULER_H - 1, w, RULER_H - 1)

        # 图层行
        for row in range(self._layers):
            y0 = self._row_tops[row]
            rh = self._row_heights[row]
            p.fillRect(0, y0, w, rh,
                       BG_ROW if row % 2 == 0 else BG_ROW_ALT)
            p.setPen(QPen(BORDER))
            p.drawLine(0, y0 + rh - 1, w, y0 + rh - 1)
            # 眼睛开关 + 行号（隐藏行整体灰显）
            eye_rect = QRectF(2, y0 + rh / 2 - 8, EYE_W, 16)
            p.setPen(QPen(QColor("#4a90d9") if self._is_visible(row)
                          else QColor("#b0b8c0")))
            p.drawText(eye_rect, Qt.AlignmentFlag.AlignCenter,
                       "显" if self._is_visible(row) else "隐")
            p.setPen(QPen(QColor("#9fb0c2") if self._is_visible(row)
                          else QColor("#c0c8d0")))
            p.drawText(QRectF(EYE_W + 2, y0, LABEL_W - EYE_W - 6, rh),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                       f"层{row + 1}")
        p.setPen(QPen(BORDER))
        p.drawLine(LABEL_W - 1, 0, LABEL_W - 1, h)

        # 片段块（子通道纵向铺开；隐藏图层半透明）
        p.setFont(self.font())
        for c in self._clips:
            cid = c.get("id", "")
            row = int(c.get("layer", 0))
            if not (0 <= row < self._layers):
                continue
            lane = self._lane_of.get(cid, 0)
            x0 = self._x(float(c.get("start", 0)))
            x1 = self._x(float(c.get("end", 0)))
            if x1 < LABEL_W or x0 > w:
                continue
            y = self._row_tops[row] + ROW_PAD + lane * (LANE_H + LANE_GAP)
            rect = QRectF(x0, y, max(6.0, x1 - x0 - 1.5), LANE_H)
            color = QColor(COLORS.get(c.get("type", ""), QColor("#888888")))
            if not self._is_visible(row):
                color.setAlpha(70)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(rect, 4, 4)
            if cid == self._sel:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(SEL_BORDER, 2))
                p.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 4, 4)
            label = str(c.get("name") or c.get("asset") or "")
            if c.get("type") == "spine" and c.get("anims"):
                first = c["anims"][0].get("anim", "")
                if first:
                    label = f"{label}·{first}"
            p.setPen(QPen(QColor("#ffffff")))
            p.drawText(rect.adjusted(5, 0, -3, 0),
                       Qt.AlignmentFlag.AlignVCenter |
                       Qt.AlignmentFlag.AlignLeft |
                       Qt.TextFlag.TextSingleLine,
                       p.fontMetrics().elidedText(
                           label, Qt.TextElideMode.ElideRight,
                           int(rect.width() - 8)))

        # 播放头
        px = self._x(self._playhead)
        p.setPen(QPen(PLAYHEAD, 2))
        p.drawLine(int(px), 0, int(px), h)
        p.setBrush(PLAYHEAD)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(px - 5, 0, 10, 7))
        p.end()

    # ---- 命中 / 拖动 ----
    EDGE = 7  # 裁剪热区 px

    def _hit_clip(self, x: float, row: int, y: float):
        """同行命中：先按子通道纵坐标过滤，再取时间相交的最后绘制者。"""
        best = None
        for c in self._clips:
            if int(c.get("layer", 0)) != row:
                continue
            lane = self._lane_of.get(c.get("id", ""), 0)
            cy = self._row_tops[row] + ROW_PAD + lane * (LANE_H + LANE_GAP)
            if not (cy - 1 <= y <= cy + LANE_H + 1):
                continue
            x0 = self._x(float(c.get("start", 0)))
            x1 = self._x(float(c.get("end", 0)))
            if x0 - 1 <= x <= x1 + 1:
                best = (c, x0, x1)
        return best

    def mousePressEvent(self, e):
        x, y = e.position().x(), e.position().y()
        if y < RULER_H:
            self._drag = ("seek",)
            self.seek.emit(round(self._t(x), 3))
            return
        if x < LABEL_W:
            row = self._row_at(y)
            if row >= 0:
                # 眼睛开关热区
                rh = self._row_heights[row]
                eye_rect = QRectF(2, self._row_tops[row] + rh / 2 - 8,
                                  EYE_W, 16)
                if eye_rect.contains(x, y):
                    self.layerVisibilityToggled.emit(row)
            return
        row = self._row_at(y)
        if row < 0:
            return
        hit = self._hit_clip(x, row, y)
        if not hit:
            self._drag = None
            self.selected.emit("")
            return
        c, x0, x1 = hit
        self.selected.emit(c.get("id", ""))
        if abs(x - x0) <= self.EDGE:
            self._drag = ("trim_l", c["id"], float(c["start"]), float(c["end"]))
        elif abs(x - x1) <= self.EDGE:
            self._drag = ("trim_r", c["id"], float(c["start"]), float(c["end"]))
        else:
            self._drag = ("move", c["id"], float(c["start"]), float(c["end"]),
                          x - self._x(float(c["start"])))

    def mouseMoveEvent(self, e):
        if not self._drag:
            return
        x = e.position().x()
        mode = self._drag[0]
        if mode == "seek":
            self.seek.emit(round(min(self._t(x), self._duration), 3))
        elif mode == "move":
            _, cid, orig_start, orig_end, grab = self._drag[:5]
            delta = round((self._t(x - grab) - orig_start) * 10) / 10
            delta = max(delta, -orig_start)
            if abs(delta) > 1e-9:
                self._drag = ("move", cid, orig_start, orig_end, grab, delta)
                for c in self._clips:                # 仅改本地副本做实时反馈
                    if c.get("id") == cid:           # release 后由 moved 信号落模型
                        c["start"] = orig_start + delta
                        c["end"] = orig_end + delta
                self._relayout()
                self.update()
        elif mode in ("trim_l", "trim_r"):
            _, cid, s0, e0 = self._drag
            t = round(self._t(x) * 10) / 10
            if mode == "trim_l":
                t = max(0.0, min(t, e0 - 0.1))
                self.trimmed.emit(cid, t, e0)
            else:
                t = max(t, s0 + 0.1)
                self.trimmed.emit(cid, s0, t)

    def mouseReleaseEvent(self, _e):
        if self._drag:
            mode = self._drag[0]
            if mode == "move" and len(self._drag) >= 6:
                _, cid, _s0, _e0, _g, dt = self._drag
                self.moved.emit(cid, dt)
            self._drag = None

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = e.angleDelta().y()
            factor = 1.25 if delta > 0 else 0.8
            self._pps = min(600.0, max(10.0, self._pps * factor))
            self.update()
        else:
            e.ignore()   # 交给外层 QScrollArea 纵向滚动

    # ---- 素材拖入（按落点图层行/时间建片段） ----
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_ASSET):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_ASSET):
            e.acceptProposedAction()

    def dropEvent(self, e):
        import json
        raw = bytes(e.mimeData().data(MIME_ASSET)).decode("utf-8", "replace")
        try:
            info = json.loads(raw)
        except ValueError:
            return
        pos = e.position()
        row = self._row_at(pos.y())
        if row < 0:
            row = self._layers - 1
        t = round(min(self._t(pos.x()), self._duration) * 10) / 10
        self.assetDropped.emit(info.get("kind", ""), info.get("name", ""),
                               row, max(0.0, t))
