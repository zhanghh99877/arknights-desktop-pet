"""日历页：月历 + 右侧当日事项面板。

事项圆点 / DDL 变色 + 当日事项编辑面板。
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, QEvent, QRect, Qt, QTime
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QPainter, QPen, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget, QCheckBox, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMenu, QPlainTextEdit,
    QPushButton, QTabWidget, QTimeEdit, QVBoxLayout, QWidget,
)

from core import holidays
from core.calendar_store import CalendarStore
from ui.theme import ACCENT, DANGER, TEXT_DIM, WARN

_COLOR_DDL_SOON = QColor(DANGER)  # 3 天内 / 已过期 DDL：红字
_COLOR_DDL_FAR = QColor(WARN)     # 更远的 DDL：橙点
_COLOR_EVENT = QColor(ACCENT)     # 普通事项：蓝点
_ACCENT = QColor(ACCENT)
_TEXT_DIM = QColor(TEXT_DIM)


class MarkedCalendar(QCalendarWidget):
    """按事项/DDL 绘制格子标记。"""

    def __init__(self, store: CalendarStore, parent=None):
        super().__init__(parent)
        self._store = store
        self._marks: dict[str, dict] = {}
        # 不显示左侧周数
        self.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.refresh_marks()

    def refresh_marks(self):
        self._marks = self._store.month_marks(
            self.yearShown(), self.monthShown())
        self._apply_day_formats()
        self.updateCells()

    def _apply_day_formats(self):
        """逐格设置日期数字颜色：非当月变浅、法定节假日标红。"""
        y, m = self.yearShown(), self.monthShown()
        first = QDate(y, m, 1)
        first_day = self.locale().firstDayOfWeek().value
        # 回退到本月第一周的周首：注意 -(a % 7) 与 (-a) % 7 不同，必须加括号
        start = first.addDays(-((first.dayOfWeek() - first_day) % 7))
        dim = QTextCharFormat()
        dim.setForeground(QColor(TEXT_DIM))
        fest = QTextCharFormat()
        fest.setForeground(QColor(DANGER))
        blank = QTextCharFormat()
        for i in range(42):  # 6 行 × 7 列月历格
            d = start.addDays(i)
            if holidays.name_of(d.toPython()):
                self.setDateTextFormat(d, fest)
            elif d.month() != m:
                self.setDateTextFormat(d, dim)
            else:
                self.setDateTextFormat(d, blank)

    def _goto(self, year, month):
        super().setCurrentPage(year, month)
        self.refresh_marks()

    def showNextMonth(self):
        self._goto(*_shift(self.yearShown(), self.monthShown(), 1))

    def showPreviousMonth(self):
        self._goto(*_shift(self.yearShown(), self.monthShown(), -1))

    def paintCell(self, painter: QPainter, rect: QRect, date: QDate):
        super().paintCell(painter, rect, date)
        # Qt 日历对「非当月格子」忽略 setDateTextFormat 的前景色（实测：
        # 当月自定义颜色生效，格外日期不生效），这里用同色同位置重画
        # 数字来变色——新字形完全覆盖旧字形，等效于重新着色
        if date.month() != self.monthShown():
            painter.save()
            painter.setPen(QColor(TEXT_DIM))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                             str(date.day()))
            painter.restore()
        # 今天：主色实线圆角框；选中日期：主色虚线框（错开内缩，可叠加）
        if date == QDate.currentDate():
            painter.save()
            painter.setPen(QPen(_ACCENT, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
            painter.restore()
        if date == self.selectedDate():
            painter.save()
            painter.setPen(QPen(_ACCENT, 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 5, 5)
            painter.restore()
        self._paint_holiday_name(painter, rect, date)
        self._paint_event_marks(painter, rect, date)

    def _paint_holiday_name(self, painter: QPainter, rect: QRect, date: QDate):
        """法定节假日：日期数字下方标节日名（红，最多 3 字）。"""
        name = holidays.name_of(date.toPython())
        if not name:
            return
        painter.save()
        painter.setPen(QColor(DANGER))
        f = QFont(painter.font())
        f.setPointSizeF(7)
        painter.setFont(f)
        painter.drawText(
            QRect(rect.left(), rect.bottom() - 18, rect.width(), 10),
            Qt.AlignmentFlag.AlignCenter, name[:3])
        painter.restore()

    def _paint_event_marks(self, painter: QPainter, rect: QRect, date: QDate):
        key = date.toString("yyyy-MM-dd")
        m = self._marks.get(key)
        if not m:
            return
        today = datetime.now().date()
        d = date.toPython()
        # DDL：临近/过期红字重画
        if m["has_pending_ddl"] and (m["overdue_ddl"] or (d - today).days <= 3):
            painter.save()
            painter.setPen(_COLOR_DDL_SOON)
            f = QFont(painter.font())
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(date.day()))
            painter.restore()
        # 圆点：DDL 橙、事项蓝，画在格子底部
        dots = []
        if m["has_pending_ddl"]:
            dots.append(_COLOR_DDL_FAR)
        if m["has_event"]:
            dots.append(_COLOR_EVENT)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        r = 3
        total_w = len(dots) * 2 * r + (len(dots) - 1) * 4
        x = rect.center().x() - total_w // 2 + r
        y = rect.bottom() - 6
        for color in dots:
            painter.setBrush(QBrush(color))
            painter.drawEllipse(x - r, y - r, 2 * r, 2 * r)
            x += 2 * r + 4
        painter.restore()


def _shift(year: int, month: int, delta: int) -> tuple[int, int]:
    month += delta
    if month > 12:
        return year + 1, 1
    if month < 1:
        return year - 1, 12
    return year, month


def _group_under_parents(rows: list[dict]) -> list[tuple[dict, int]]:
    """一览/已完成用：把任意层级的任务树拍平，子任务紧跟父任务下方。

    返回 [(任务, 深度)]，深度用于缩进前缀（└ 重复 depth 次）。
    父不在本列表里的整棵子树按顶层排在末尾。数据结构保证无环，
    每个任务恰好出现一次。
    """
    by_id = {r["id"]: r for r in rows}
    children: dict[int, list] = {}
    for r in rows:
        if r.get("parent_id"):
            children.setdefault(r["parent_id"], []).append(r)
    tops = [r for r in rows
            if not r.get("parent_id") or r["parent_id"] not in by_id]
    out: list[tuple[dict, int]] = []
    for t in tops:
        stack = [(t, 0)]
        while stack:
            node, depth = stack.pop()
            out.append((node, depth))
            # 逆序压栈保持子任务原有顺序
            for k in reversed(children.get(node["id"], [])):
                stack.append((k, depth + 1))
    return out


class CalendarPage(QWidget):
    def __init__(self, store: CalendarStore, parent=None):
        super().__init__(parent)
        self._store = store

        self.calendar = MarkedCalendar(store)
        today_btn = QPushButton("回到今天")
        today_btn.clicked.connect(self._goto_today)

        # 右侧面板：当日 / 一览 两个标签页
        self.date_label = QLabel()
        self.date_label.setStyleSheet("font-weight: bold;")
        self.events = QListWidget()
        self.events.itemDoubleClicked.connect(self._double_click_done)
        self.events.itemClicked.connect(self._load_into_form)
        self.events.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.events.customContextMenuRequested.connect(
            lambda pos: self._show_item_menu(self.events, pos)
        )

        self.overview = QListWidget()
        self.overview.itemDoubleClicked.connect(self._double_click_done)
        self.overview.itemClicked.connect(self._load_into_form)
        self.overview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.overview.customContextMenuRequested.connect(
            lambda pos: self._show_item_menu(self.overview, pos)
        )
        # 已完成：与当日/一览平级的第三个顶条标签页
        self.done_list = QListWidget()
        self.done_list.itemDoubleClicked.connect(self._double_click_done)
        self.done_list.itemClicked.connect(self._load_into_form)
        self.done_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.done_list.customContextMenuRequested.connect(
            lambda pos: self._show_item_menu(self.done_list, pos)
        )
        # 条目过多时显式保证出竖向滚动条
        for lst in (self.events, self.overview, self.done_list):
            lst.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        day_tab = QWidget()
        day_layout = QVBoxLayout(day_tab)
        day_layout.setContentsMargins(0, 4, 0, 0)
        day_layout.addWidget(self.date_label)
        day_layout.addWidget(self.events, 1)

        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        overview_layout.setContentsMargins(0, 4, 0, 0)
        overview_layout.addWidget(self.overview, 1)

        done_tab = QWidget()
        done_layout = QVBoxLayout(done_tab)
        done_layout.setContentsMargins(0, 4, 0, 0)
        done_layout.addWidget(self.done_list, 1)

        self.tabs = QTabWidget()
        self.tabs.addTab(day_tab, "当日")
        self.tabs.addTab(overview_tab, "一览")
        self.tabs.addTab(done_tab, "已完成")
        # 切换顶条 = 重建列表：画线暂留的项（一览↔已完成）在此刻真正搬家
        self.tabs.currentChanged.connect(lambda _: self._refresh_all())

        # 添加表单：标题独占一行，详细内容第二行，选项第三行
        # 点击列表中的事项会回填到这里，「添加」变「修改」
        self._editing: dict | None = None  # 正在编辑的事件（None = 添加模式）
        self._collapsed: set[int] = set()  # 一览中被收起的父任务 id
        self._expandable: set[int] = set()  # 一览当前有子任务的父任务 id（三角可点）
        self.title_edit = QLineEdit(placeholderText="要做什么？")
        self.title_edit.setMinimumHeight(32)
        self.title_edit.returnPressed.connect(self._submit)
        # 详细内容：多行，随内容向上加高（最多 3 行），超出出竖向滚动条
        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("详细内容…（可留空）")
        self.note_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.note_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.note_edit.document().setDocumentMargin(2)  # 压掉内部页边距，高度贴紧文字
        # 行数变化和软换行（长行折行）都要触发重算高度
        self.note_edit.document().blockCountChanged.connect(
            lambda _: self._fit_note_height())
        self.note_edit.document().documentLayout().documentSizeChanged.connect(
            lambda _: self._fit_note_height())
        self._fit_note_height()
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("事项", "event")
        self.kind_combo.addItem("DDL", "ddl")
        self.time_check = QCheckBox("指定时间")
        self.time_edit = QTimeEdit(datetime.now().time())
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setEnabled(False)
        self.time_check.toggled.connect(self.time_edit.setEnabled)
        self.kind_combo.currentIndexChanged.connect(
            lambda i: self.time_check.setChecked(self.kind_combo.currentData() == "ddl")
        )
        self.submit_btn = QPushButton("添加")
        self.submit_btn.setProperty("class", "primary")
        self.submit_btn.clicked.connect(self._submit)

        form_row2 = QHBoxLayout()
        form_row2.addWidget(self.kind_combo)
        form_row2.addWidget(self.time_check)
        form_row2.addWidget(self.time_edit)
        form_row2.addStretch(1)
        form_row2.addWidget(self.submit_btn)

        ops = QHBoxLayout()
        done_btn = QPushButton("完成 / 取消完成")
        # 日期直接改：修改模式 = 事项日期（改动即移动事项）；
        # 添加模式 = 新事项的落点（默认跟日历选中那天）
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)  # 也可点箭头弹月历
        self.date_edit.dateChanged.connect(self._on_date_edit_changed)
        del_btn = QPushButton("删除")
        del_btn.setProperty("class", "danger")
        done_btn.clicked.connect(self._toggle_done)
        del_btn.clicked.connect(self._delete)
        ops.addWidget(done_btn)
        ops.addWidget(self.date_edit)
        ops.addWidget(del_btn)
        ops.addStretch(1)

        event_panel = QWidget()
        right = QVBoxLayout(event_panel)
        right.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self.tabs, 1)
        right.addLayout(ops)
        right.addWidget(self.title_edit)
        right.addWidget(self.note_edit)
        right.addLayout(form_row2)

        left = QVBoxLayout()
        left.addWidget(self.calendar, 1)
        left.addWidget(today_btn)

        body = QHBoxLayout()
        body.addLayout(left, 3)
        body.addWidget(event_panel, 2)

        layout = QVBoxLayout(self)
        layout.addLayout(body, 1)

        self.calendar.selectionChanged.connect(self._on_date_changed)
        self.calendar.currentPageChanged.connect(self._on_page_changed)
        # 点列表空白处：退出编辑模式回到「添加」，方便直接新建
        for lst in (self.events, self.overview, self.done_list):
            lst.viewport().installEventFilter(self)
        self._refresh_all()
        self._sync_move_ui()

    def _sync_move_ui(self):
        """日期框显示值：修改模式 = 事项日期；添加模式 = 日历选中那天。"""
        self.date_edit.blockSignals(True)
        try:
            if self._editing is not None:
                self.date_edit.setDate(
                    QDate.fromString(self._editing["date"], "yyyy-MM-dd"))
            else:
                self.date_edit.setDate(self.calendar.selectedDate())
        finally:
            self.date_edit.blockSignals(False)

    def _fit_note_height(self):
        """详细内容框按整行台阶调整高度：1/2/3 行，无中间态。

        行数按视觉折行计（长句折到第 2 行也会升档）；超过 3 行由滚动条接管。
        行高必须取 QTextLine 的实际高度：QSS 会用不同字号渲染，
        widget.fontMetrics() 与文档布局行高不一致，混用会导致档位错乱。
        """
        doc = self.note_edit.document()
        layout = doc.documentLayout()
        lines = 0
        line_h = 0.0
        b = doc.begin()
        while b.isValid():
            rect_h = layout.blockBoundingRect(b).height()
            tl = b.layout()
            lh = tl.lineAt(0).height() if tl.lineCount() else rect_h
            line_h = max(line_h, lh)
            lines += max(1, round(rect_h / lh)) if lh else 1
            b = b.next()
        lines = max(1, min(3, lines))
        self.note_edit.setFixedHeight(
            int(lines * line_h + doc.documentMargin() * 2
                + 2 * self.note_edit.frameWidth()))

    def showEvent(self, event):
        """主题字体会改变文档行高，显示时（样式已生效）重新校准高度。"""
        super().showEvent(event)
        self._fit_note_height()

    @staticmethod
    def _elide(lst: QListWidget, text: str) -> str:
        """标题过长以 … 结尾，宽度按列表可视区算。"""
        w = lst.viewport().width() - 24
        return lst.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, w)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "events"):  # 构造期可能早于列表创建
            self._reload()
            self._reload_overview()

    def eventFilter(self, obj, event):
        """列表 viewport：空白点击退出编辑；点行首三角小块 → 收起/展开子树。"""
        if event.type() == QEvent.Type.MouseButtonPress:
            lst = obj.parent()
            if not isinstance(lst, QListWidget):
                return super().eventFilter(obj, event)
            pos = event.position().toPoint()
            item = lst.itemAt(pos)
            if item is None:
                self._reset_form()
            elif lst is self.overview and pos.x() < 30:
                # 三角判定：仅行首 30px 的小块，且只有真有子任务的父任务响应；
                # 其他条目不吞事件，照常进入选中/编辑
                e = item.data(Qt.ItemDataRole.UserRole) or {}
                iid = e.get("id")
                if iid is not None and iid in self._expandable:
                    if iid in self._collapsed:
                        self._collapsed.discard(iid)
                    else:
                        self._collapsed.add(iid)
                    self._reload_overview()
                    return True  # 吃掉事件：不再触发 itemClicked
        return super().eventFilter(obj, event)

    # ---- 数据刷新 ----
    def _reload(self):
        d = self.calendar.selectedDate()
        self.date_label.setText(d.toString("yyyy年MM月dd日"))
        self.events.clear()
        for e in self._store.events_on(d.toString("yyyy-MM-dd")):
            tag = "DDL" if e["kind"] == "ddl" else "事项"
            time = f" {e['time']}" if e["time"] else ""
            item = QListWidgetItem(
                self._elide(self.events, f"[{tag}{time}] {e['title']}"))
            item.setData(Qt.ItemDataRole.UserRole, e)
            if e["done"]:
                f = item.font()
                f.setStrikeOut(True)
                item.setFont(f)
                item.setForeground(_TEXT_DIM)
            self.events.addItem(item)
        self._reselect_editing()

    def _refresh_all(self):
        self._reload()
        self._reload_overview()
        self.calendar.refresh_marks()
        # 正在编辑的事件被删除/移出列表（如标记完成后从一览消失）→ 回添加模式
        if self._editing is not None:
            alive = any(
                (lst.item(i).data(Qt.ItemDataRole.UserRole) or {}).get("id")
                == self._editing["id"]
                for lst in (self.events, self.overview)
                for i in range(lst.count())
            )
            if not alive:
                self._reset_form()

    def _on_date_changed(self):
        self._reset_form()  # 换日期即退出编辑；修改自动保存（不移动事项）
        self.tabs.setCurrentIndex(0)  # 右栏切回「当日」
        self._reload()
        self._sync_move_ui()  # 添加模式下日期显示跟日历选中走

    def _on_page_changed(self, year: int, month: int):
        # 导航栏翻月/菜单跳月都走这里，顺带刷新格子标记
        self.calendar.refresh_marks()

    def _goto_today(self):
        today = QDate.currentDate()
        self.calendar.setCurrentPage(today.year(), today.month())
        self.calendar.setSelectedDate(today)

    # ---- 一览 ----
    def _reload_overview(self):
        self.overview.clear()
        today = datetime.now().date()
        rows = _group_under_parents(self._store.pending_overview())
        by_id = {r["id"]: r for r, _d in rows}
        self._expandable = {r["parent_id"] for r, _d in rows if r.get("parent_id")}

        def under_collapsed(e: dict) -> bool:
            """祖先中有被收起的父任务则整棵子树不可见。"""
            anc = e.get("parent_id")
            while anc is not None:
                if anc in self._collapsed:
                    return True
                anc = by_id.get(anc, {}).get("parent_id")
            return False

        for e, depth in rows:
            if under_collapsed(e):
                continue
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
            days = (d - today).days
            if days < 0:
                countdown = f"已过期{-days}天"
            elif days == 0:
                countdown = "今天"
            elif days == 1:
                countdown = "明天"
            else:
                countdown = f"还剩{days}天"
            tag = "DDL" if e["kind"] == "ddl" else "事项"
            time = f" {e['time']}" if e["time"] else ""
            if depth == 0 and e["id"] in self._expandable:
                prefix = "▶ " if e["id"] in self._collapsed else "▼ "
            else:
                prefix = "└ " * depth
            item = QListWidgetItem(self._elide(
                self.overview,
                f"{prefix}[{tag}] {d.strftime('%Y-%m-%d')}{time}"
                f" {e['title']}（{countdown}）"))
            item.setData(Qt.ItemDataRole.UserRole, e)
            if e["done"]:
                # 已完成的子任务跟随父任务留在一览：画线灰显
                f = item.font()
                f.setStrikeOut(True)
                item.setFont(f)
                item.setForeground(_TEXT_DIM)
            elif e["kind"] == "ddl":
                item.setForeground(_COLOR_DDL_SOON if days <= 3 else _COLOR_DDL_FAR)
            self.overview.addItem(item)
        # 已完成列表：最近完成的在前，画线灰显
        self.done_list.clear()
        for e, depth in _group_under_parents(self._store.completed_overview()):
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
            tag = "DDL" if e["kind"] == "ddl" else "事项"
            time = f" {e['time']}" if e["time"] else ""
            prefix = "└ " * depth
            item = QListWidgetItem(self._elide(
                self.done_list,
                f"{prefix}[{tag}] {d.strftime('%Y-%m-%d')}{time} {e['title']}"))
            item.setData(Qt.ItemDataRole.UserRole, e)
            f = item.font()
            f.setStrikeOut(True)
            item.setFont(f)
            item.setForeground(_TEXT_DIM)
            self.done_list.addItem(item)
        self._reselect_editing()

    def _reselect_editing(self):
        """列表重建后恢复对正在编辑事项的选中（持续高亮，不闪一下就丢）。

        编辑态优先于一切：详情表单开着时，对应条目在当日/一览/已完成里
        保持高亮。已完成的项不选中——选中态的主题色会盖掉灰显。
        """
        if self._editing is None or self._editing.get("done"):
            return
        eid = self._editing["id"]
        for lst in (self.events, self.overview, self.done_list):
            for i in range(lst.count()):
                it = lst.item(i)
                if (it.data(Qt.ItemDataRole.UserRole) or {}).get("id") == eid:
                    lst.setCurrentItem(it)

    # ---- 操作 ----
    def _load_into_form(self, item: QListWidgetItem):
        """单击列表项：先保存对上一项的修改，再把这项回填到表单。

        注意：item.data() 返回的是快照副本，列表刷新后 item 即失效，
        所以必须先取 id、再刷新、再从数据库取最新数据回填。

        点的是「正在编辑的同一个项」时直接返回：不重建列表，两次点击
        之间视图状态完好，双击才能完成/取消完成；表单里的未保存改动
        也原样保留。
        """
        eid = item.data(Qt.ItemDataRole.UserRole)["id"]
        if self._editing is not None and self._editing["id"] == eid:
            return
        self._save_editing()
        self._refresh_all()  # 列表显示与缓存对齐数据库
        e = self._store.get(eid)
        if e is None:
            return
        self._editing = e
        self.title_edit.setText(e["title"])
        self.note_edit.setPlainText(e.get("note") or "")
        self._fit_note_height()
        self._reselect_editing()  # 编辑目标已定，恢复并持续高亮
        # 先设类型再设时间勾选：类型联动会自动勾/取消“指定时间”，需要覆盖
        self.kind_combo.setCurrentIndex(self.kind_combo.findData(e["kind"]))
        self.time_check.setChecked(bool(e["time"]))
        if e["time"]:
            self.time_edit.setTime(QTime.fromString(e["time"], "HH:mm"))
        self.submit_btn.setText("修改")
        self._sync_move_ui()

    def _save_editing(self):
        """把表单当前值写回正在编辑的事项（标题为空则放弃保存）。"""
        e = self._editing
        if e is None:
            return
        title = self.title_edit.text().strip()
        if not title:
            return
        time = (self.time_edit.time().toString("HH:mm")
                if self.time_check.isChecked() else None)
        self._store.update_event(
            e["id"], title, self.kind_combo.currentData(), time,
            self.note_edit.toPlainText().strip())

    def _reset_form(self):
        """退出编辑回到添加模式；编辑中的修改自动保存并刷新列表显示。"""
        if self._editing is not None:
            self._save_editing()
            self.title_edit.clear()
            self.note_edit.clear()
            self._editing = None  # 先清再刷新：_refresh_all 的存活检查靠它防递归
            self._refresh_all()
        self.submit_btn.setText("添加")
        self._sync_move_ui()

    def _submit(self):
        if self._editing is not None:
            # 修改：退出编辑即自动保存（_reset_form 内含刷新），与
            # 点空白/换日期行为一致
            self._reset_form()
            return
        title = self.title_edit.text().strip()
        if not title:
            return
        time = self.time_edit.time().toString("HH:mm") if self.time_check.isChecked() else None
        note = self.note_edit.toPlainText().strip()
        self._store.add_event(self.date_edit.date().toString("yyyy-MM-dd"),
                              title, self.kind_combo.currentData(), time, note)
        self.title_edit.clear()
        self.note_edit.clear()
        self._sync_move_ui()  # 日期框复位跟日历选中走
        self._refresh_all()

    def _current_list(self) -> QListWidget:
        # 顶条三个页签各对应一个列表
        return (self.events, self.overview, self.done_list)[self.tabs.currentIndex()]

    def _selected_event(self) -> dict | None:
        item = self._current_list().currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _set_done(self, e: dict):
        """完成/取消完成：只改数据库 + 就地同步外观，不动列表成员关系。

        画线/删线立即生效；项的搬家（一览↔已完成）统一推迟到下次
        列表重建（切换顶条标签、翻日期等）时发生。
        完成父任务会级联完成其子任务（涉及多项时整表重建同步画线）。
        """
        cascaded = self._store.set_done(e["id"], not e["done"])
        fresh = self._store.get(e["id"])
        if self._editing is not None and self._editing["id"] == e["id"]:
            self._editing = fresh
        if cascaded:
            self._refresh_all()  # 级联的子任务也要画线，整表重建最省事
        else:
            self._sync_item_look(fresh)
        self.calendar.refresh_marks()

    def _sync_item_look(self, e: dict):
        """三个列表里就地同步该项外观（画线/灰显/颜色）并刷新缓存数据。"""
        for lst in (self.events, self.overview, self.done_list):
            for i in range(lst.count()):
                it = lst.item(i)
                if (it.data(Qt.ItemDataRole.UserRole) or {}).get("id") != e["id"]:
                    continue
                it.setData(Qt.ItemDataRole.UserRole, e)
                f = it.font()
                f.setStrikeOut(bool(e["done"]))
                it.setFont(f)
                if e["done"]:
                    it.setForeground(QColor(TEXT_DIM))
                    # 选中态的主题色会盖掉灰显（变黑），完成项一律取消选中，
                    # 三个列表的完成项外观与「已完成」页签保持一致
                    if lst.currentItem() is it:
                        lst.setCurrentItem(None)
                elif lst is self.overview and e["kind"] == "ddl":
                    days = (datetime.strptime(e["date"], "%Y-%m-%d").date()
                            - datetime.now().date()).days
                    it.setForeground(_COLOR_DDL_SOON if days <= 3 else _COLOR_DDL_FAR)
                else:
                    it.setForeground(QBrush())  # 恢复默认色
                break  # 同一列表里最多出现一次

    def _delete_event(self, e: dict):
        self._store.delete(e["id"])
        self._refresh_all()

    def _double_click_done(self, _item: QListWidgetItem):
        """双击 = 完成/取消完成（当日/一览/已完成共用）。

        只对正在编辑的项生效：选中靠单击（点同一个不重建列表，双击
        才能被 Qt 识别）；信号携带的 _item 是单击重建后的野引用，弃用。
        已完成项故意不选中（选中会把灰显变黑），此时按编辑目标 id 在
        发送者列表里查找；双击未选中的项不做任何事，避免误完成。
        """
        lst = self.sender()
        if lst is None or self._editing is None:
            return
        e = None
        cur = lst.currentItem()
        if cur is not None:
            d = cur.data(Qt.ItemDataRole.UserRole)
            if d and d.get("id") == self._editing["id"]:
                e = d
        if e is None:
            for i in range(lst.count()):
                d = lst.item(i).data(Qt.ItemDataRole.UserRole) or {}
                if d.get("id") == self._editing["id"]:
                    e = d
                    break
        if e:
            self._set_done(e)

    def _toggle_done(self):
        e = self._selected_event()
        if e:
            self._set_done(e)

    def _delete(self):
        e = self._selected_event()
        if e:
            self._delete_event(e)

    def _on_date_edit_changed(self, d: QDate):
        """日期框被直接改动。

        修改模式：事项移到所选日期，列表同步刷新，但**不跳转**大日历
        （只有直接点大日历格子才切换日期视图）；
        添加模式：日期框的值就是新事项的落点，无需其他动作。
        """
        if self._editing is None:
            return
        new_date = d.toString("yyyy-MM-dd")
        if new_date == self._editing["date"]:
            return
        self._store.move_event(self._editing["id"], new_date)
        self._refresh_all()  # 各列表与标记同步

    def _show_item_menu(self, lst: QListWidget, pos):
        """右键菜单：跳转 / 添加子任务 / 完成 / 删除（三个列表共用）。"""
        item = lst.itemAt(pos)
        if not item:
            return
        lst.setCurrentItem(item)
        e = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        act_jump = QAction("跳转到日期", self)
        act_jump.triggered.connect(lambda: self._jump_to_date(e))
        menu.addAction(act_jump)
        # 任意层级的任务都能加子任务（数据结构保证无环）
        act_sub = QAction("添加子任务", self)
        act_sub.triggered.connect(lambda: self._add_subtask(e))
        menu.addAction(act_sub)
        act_done = QAction("取消完成" if e["done"] else "完成", self)
        act_del = QAction("删除", self)
        act_done.triggered.connect(lambda: self._set_done(e))
        act_del.triggered.connect(lambda: self._delete_event(e))
        menu.addAction(act_done)
        menu.addAction(act_del)
        menu.exec(lst.viewport().mapToGlobal(pos))

    def _add_subtask(self, e: dict):
        """在任务下新建子任务：弹框输标题 + 日期（默认继承父任务日期）。"""
        dlg = QDialog(self)
        dlg.setWindowTitle("添加子任务")
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("子任务标题")
        date_edit = QDateEdit(QDate.fromString(e["date"], "yyyy-MM-dd"))
        date_edit.setDisplayFormat("yyyy-MM-dd")
        date_edit.setCalendarPopup(True)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form = QVBoxLayout(dlg)
        form.addWidget(QLabel(f"「{e['title']}」的子任务："))
        form.addWidget(title_edit)
        form.addWidget(date_edit)
        form.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        title = title_edit.text().strip()
        if not title:
            return
        self._store.add_event(date_edit.date().toString("yyyy-MM-dd"),
                              title, "event", None, "", parent_id=e["id"])
        self._refresh_all()

    def _jump_to_date(self, e: dict):
        """日历跳到该事项所在日期，右栏回「当日」页。"""
        d = QDate.fromString(e["date"], "yyyy-MM-dd")
        self.calendar.setCurrentPage(d.year(), d.month())
        self.calendar.setSelectedDate(d)
        self.tabs.setCurrentIndex(0)
