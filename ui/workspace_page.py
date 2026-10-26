"""工作区页：时间轴动画合成器。

布局：顶部工具条（项目/画布/播放/导出）＋左素材面板＋中舞台＋右属性面板
＋底部时间轴。单一数据流：Qt 持有 Project 模型，任何编辑 → 防抖 100ms →
stage.sync_project + timeline.set_data；JS 只回报交互事件。
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QMimeData, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QMessageBox, QProgressDialog, QPushButton,
    QScrollArea, QSpinBox, QSplitter, QToolButton, QVBoxLayout, QWidget,
)

from core.assets import RelayLibrary
from core.workspace import AnimEntry, Clip, MoveEntry, Project, WorkspaceStore
from core.workspace_exporter import VideoExporter
from ui.stage_view import MIME_ASSET, StageView
from ui.timeline import Timeline
from ui.widgets import NoWheelComboBox, NoWheelDoubleSpinBox

_IMG_EXT = "图片/SVG/HTML (*.png *.svg *.html *.htm)"


# ---------------- 素材列表（自定义拖放 mime） ----------------

class AssetList(QListWidget):
    """素材列表：拖出时携带 {kind, name} JSON 的自定义 mime。"""

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self._kind = kind
        self.setDragEnabled(True)
        self.setMaximumHeight(220)

    def mimeData(self, items):  # QListWidget 虚拟：startDrag 时调用
        md = QMimeData()
        if items:
            name = items[0].text()
            if self._kind == "asset":
                kind = "png" if name.lower().endswith(".png") else "svg"
            else:
                kind = self._kind
            payload = json.dumps({"kind": kind, "name": name},
                                 ensure_ascii=False)
            md.setData(MIME_ASSET, payload.encode("utf-8"))
            md.setText(payload)  # 舞台走 HTML5 DnD，只保证 text/plain 可达
        return md


# ---------------- 条目编辑器 ----------------

class AnimEntryEditor(QWidget):
    """动画播放条目：每行 开始/结束/动作/倍速/次数/水平翻转 + ×，底部 ＋。"""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clip: Clip | None = None
        self._model_anims: list[str] = []
        self._loading = False
        self._rows = QVBoxLayout()
        self._rows.setSpacing(1)
        self._rows.setContentsMargins(0, 0, 0, 0)
        add = QPushButton("＋ 添加动画条目")
        add.clicked.connect(self._add_row)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self._rows)
        lay.addWidget(add, alignment=Qt.AlignmentFlag.AlignLeft)

    def load(self, clip: Clip, model_anims: list[str],
             procs: list[str] = ()):
        self._clip = clip
        self._model_anims = list(model_anims)
        self._procs = list(procs)
        self._rebuild()

    def _rebuild(self):
        while self._rows.count():
            item = self._rows.takeAt(0)
            item.widget().deleteLater()
        if not self._clip:
            return
        for e in self._clip.anims:
            self._rows.addWidget(self._make_row(e))

    def _spin(self, value, lo, hi, step):
        s = NoWheelDoubleSpinBox(minimum=lo, maximum=hi, singleStep=step)
        s.setValue(value)
        s.setFixedWidth(50)
        return s

    def _make_row(self, e: AnimEntry):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        start = self._spin(e.start, 0, 36000, 0.1)
        end = self._spin(e.end, 0, 36000, 0.1)
        anim = NoWheelComboBox()
        anim.setMinimumContentsLength(6)
        for a in self._model_anims:
            anim.addItem(a, a)
        for p in self._procs:
            anim.addItem("✨" + p, p)   # 自创程序动作（Spine/proc/）
        idx = anim.findData(e.anim)
        if idx >= 0:
            anim.setCurrentIndex(idx)
        elif e.anim:
            anim.addItem(e.anim + "（缺）", e.anim)
            anim.setCurrentIndex(anim.count() - 1)
        speed = self._spin(e.speed, 0.1, 10.0, 0.1)
        mode = NoWheelComboBox()
        mode.addItem("播1次", False)
        mode.addItem("循环", True)
        mode.setCurrentIndex(1 if e.loop else 0)
        flip = QCheckBox("水平翻转")
        flip.setChecked(e.flip)
        flip.setToolTip("该动画条目内 Spine 骨架水平镜像")
        rm = QPushButton("×")
        rm.setFixedWidth(24)
        rm.setProperty("class", "icon")

        def commit(*_):
            if self._loading:
                return
            e.start, e.end = start.value(), end.value()
            e.anim = anim.currentData() or anim.currentText()
            e.speed = speed.value()
            e.loop = bool(mode.currentData())
            e.flip = flip.isChecked()
            self.changed.emit()

        for wdg in (start, end, speed):
            wdg.valueChanged.connect(commit)
        anim.currentIndexChanged.connect(commit)
        mode.currentIndexChanged.connect(commit)
        flip.toggled.connect(commit)
        rm.clicked.connect(lambda: (self._clip.anims.remove(e),
                                    self._rebuild(), self.changed.emit()))
        for wdg in (start, end, anim, speed, mode, flip, rm):
            h.addWidget(wdg)
        h.addStretch(1)
        return row

    def _add_row(self):
        if not self._clip:
            return
        t0 = self._clip.start
        first = self._model_anims[0] if self._model_anims else \
            (self._procs[0] if self._procs else "")
        self._clip.anims.append(AnimEntry(
            start=t0, end=self._clip.end,
            anim=first, speed=1.0, loop=True))
        self._rebuild()
        self.changed.emit()


class MoveEntryEditor(QWidget):
    """平移/旋转条目：每行 开始/结束/起点x,y→终点x,y/起始°→结束° + ×。"""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clip: Clip | None = None
        self._loading = False
        self._rows = QVBoxLayout()
        self._rows.setSpacing(1)
        self._rows.setContentsMargins(0, 0, 0, 0)
        add = QPushButton("＋ 添加平移/旋转条目")
        add.clicked.connect(self._add_row)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self._rows)
        lay.addWidget(add, alignment=Qt.AlignmentFlag.AlignLeft)

    def load(self, clip: Clip):
        self._clip = clip
        self._rebuild()

    def _rebuild(self):
        while self._rows.count():
            item = self._rows.takeAt(0)
            item.widget().deleteLater()
        if not self._clip:
            return
        for e in self._clip.moves:
            self._rows.addWidget(self._make_row(e))

    def _spin(self, value, lo=-99999, hi=99999, step=1.0):
        s = NoWheelDoubleSpinBox(minimum=lo, maximum=hi, singleStep=step)
        s.setValue(value)
        s.setFixedWidth(52)
        return s

    def _make_row(self, e: MoveEntry):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        start = self._spin(e.start, 0, 36000, 0.1)
        end = self._spin(e.end, 0, 36000, 0.1)
        x0 = self._spin(e.x0)
        y0 = self._spin(e.y0)
        x1 = self._spin(e.x1)
        y1 = self._spin(e.y1)
        r0 = self._spin(e.rot0, -36000, 36000, 15)
        r1 = self._spin(e.rot1, -36000, 36000, 15)
        rm = QPushButton("×")
        rm.setFixedWidth(24)
        rm.setProperty("class", "icon")
        start.setToolTip("开始秒")
        end.setToolTip("结束秒")
        x0.setToolTip("起点 x")
        y0.setToolTip("起点 y")
        x1.setToolTip("终点 x")
        y1.setToolTip("终点 y")
        r0.setToolTip("起始角度°")
        r1.setToolTip("结束角度°")

        def commit(*_):
            if self._loading:
                return
            e.start, e.end = start.value(), end.value()
            e.x0, e.y0, e.x1, e.y1 = x0.value(), y0.value(), x1.value(), y1.value()
            e.rot0, e.rot1 = r0.value(), r1.value()
            self.changed.emit()

        for wdg in (start, end, x0, y0, x1, y1, r0, r1):
            wdg.valueChanged.connect(commit)
        rm.clicked.connect(lambda: (self._clip.moves.remove(e),
                                    self._rebuild(), self.changed.emit()))
        for wdg in (start, end, x0, y0, x1, y1, r0, r1, rm):
            h.addWidget(wdg)
        h.addStretch(1)
        return row

    def _add_row(self):
        if not self._clip:
            return
        self._clip.moves.append(MoveEntry(
            start=self._clip.start, end=self._clip.end,
            x0=self._clip.x, y0=self._clip.y,
            x1=self._clip.x, y1=self._clip.y))
        self._rebuild()
        self.changed.emit()


# ---------------- 页面 ----------------

class WorkspacePage(QWidget):
    def __init__(self, library: RelayLibrary, parent=None):
        super().__init__(parent)
        self._library = library
        self._store = WorkspaceStore()
        self._project: Project | None = None
        self._sel = ""
        self._current_time = 0.0
        self._exporter: VideoExporter | None = None
        self._progress: QProgressDialog | None = None
        self._preview_dialog: QDialog | None = None
        self._preview_time = 0.0
        self._preview_sizes: list[int] = []
        self._loading = False

        self._build_ui()

        # 事件回流
        st = self.stage
        st.bridge.sigClipSelected.connect(self._select)
        st.bridge.sigClipMoved.connect(self._on_stage_moved)
        st.bridge.sigTime.connect(self._on_time)
        st.bridge.sigExportFrame.connect(self._on_export_frame)
        st.bridge.sigLog.connect(lambda m: print("[stage]", m))
        st.bridge.sigReady.connect(self._sync_now)  # 资源就绪后补一次全量同步
        st.pageLoaded.connect(self._sync_now)       # 页面加载晚于首次同步时兜底
        st.bridge.sigAssetDropped.connect(
            lambda kind, name, x, y: self._add_clip(
                kind, name, x, y, start=self._current_time))
        self.timeline.seek.connect(self._on_seek)
        self.timeline.selected.connect(self._select)
        self.timeline.moved.connect(self._on_timeline_moved)
        self.timeline.trimmed.connect(self._on_timeline_trimmed)
        self.timeline.assetDropped.connect(self._on_timeline_drop)
        self.timeline.layerVisibilityToggled.connect(self._on_layer_toggle)
        self.timeline.widthHintChanged.connect(self._update_timeline_width)
        self.timeline.panRequested.connect(self._on_timeline_pan)

        # 模型同步防抖
        self._sync_timer = QTimer(self)
        self._sync_timer.setSingleShot(True)
        self._sync_timer.setInterval(100)
        self._sync_timer.timeout.connect(self._sync_now)

        self._init_project()

    # ================= UI =================
    def _build_ui(self):
        # ---- 工具条 ----
        bar = QHBoxLayout()
        bar.setContentsMargins(8, 6, 8, 0)
        self.project_combo = NoWheelComboBox()
        self.project_combo.setMinimumWidth(140)
        btn_new = QPushButton("新建项目")
        btn_save = QPushButton("保存")
        btn_settings = QPushButton("画布设置")
        self.btn_play = QToolButton(text="▶ 播放")
        self.btn_play.setAutoRaise(True)
        btn_pause = QToolButton(text="⏸ 暂停")
        btn_pause.setAutoRaise(True)
        btn_stop = QToolButton(text="⏹ 停止")
        btn_stop.setAutoRaise(True)
        self.btn_fullscreen = QToolButton(text="⛶ 全屏预览")
        self.btn_fullscreen.setAutoRaise(True)
        self.btn_fullscreen.setToolTip("从头全屏播放，按 Esc 退出")
        self.time_label = QLabel("0.00 / 0.00 s")
        btn_export = QPushButton("导出视频…")
        btn_export.setProperty("class", "primary")
        self.status_label = QLabel("")
        bar.addWidget(QLabel("项目"))
        bar.addWidget(self.project_combo)
        bar.addWidget(btn_new)
        bar.addWidget(btn_save)
        bar.addSpacing(10)
        bar.addWidget(btn_settings)
        bar.addSpacing(10)
        bar.addWidget(self.btn_play)
        bar.addWidget(btn_pause)
        bar.addWidget(btn_stop)
        bar.addWidget(self.btn_fullscreen)
        bar.addWidget(self.time_label)
        bar.addStretch(1)
        bar.addWidget(self.status_label)
        bar.addWidget(btn_export)

        # ---- 左：素材 ----
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 6, 4, 6)
        lv.addWidget(QLabel("Spine 模型（公用素材）"))
        self.spine_list = AssetList("spine")
        lv.addWidget(self.spine_list)
        lv.addWidget(QLabel("项目素材（拖入时间轴或舞台）"))
        self.asset_list = AssetList("asset")
        lv.addWidget(self.asset_list)
        btn_import = QPushButton("导入素材…")
        lv.addWidget(btn_import, alignment=Qt.AlignmentFlag.AlignLeft)
        lv.addStretch(1)

        # ---- 中：舞台 ----
        self.stage = StageView()

        # ---- 右：属性（无美化紧凑版：窄边框直角控件、小字号、贴边布局） ----
        self._props = QWidget()
        self._props_lay = QVBoxLayout(self._props)
        self._props_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._props_lay.setSpacing(2)
        self._props_lay.setContentsMargins(2, 2, 2, 2)
        props_scroll = QScrollArea()
        props_scroll.setWidgetResizable(True)
        props_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        props_scroll.setMinimumWidth(270)
        # 局部样式覆盖全局主题：白底、灰直边框、零圆角、极小内边距
        props_scroll.setStyleSheet("""
            QWidget { font-size: 6.5pt; background-color: #ffffff; }
            QGroupBox { border: none; margin-top: 7px; padding-top: 1px;
                        font-weight: bold; color: #555555; }
            QGroupBox::title { subcontrol-origin: margin; left: 0px;
                               padding: 0 1px; }
            QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox {
                border: 1px solid #aaaaaa; border-radius: 0;
                padding: 0 1px; min-height: 14px; background: #ffffff; }
            QComboBox::drop-down { width: 14px; }
            QPushButton { border: 1px solid #aaaaaa; border-radius: 0;
                          padding: 0 5px; min-height: 14px;
                          background: #f2f2f2; }
            QPushButton:hover { background: #e4e4e4; border-color: #888888; }
            QPushButton[class="danger"]:hover { background: #e5534b;
                                                color: #ffffff; }
            QScrollBar:vertical { width: 8px; }
        """)
        props_scroll.setWidget(self._props)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(left)
        self._splitter.addWidget(self.stage)
        self._splitter.addWidget(props_scroll)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        self._splitter.setSizes([220, 700, 400])

        # ---- 底：时间轴（QScrollArea 纵向滚动；横向按内容宽撑开可滚） ----
        bottom = QHBoxLayout()
        bottom.setContentsMargins(8, 4, 8, 8)
        self.timeline = Timeline()
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidget(self.timeline)
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.timeline_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setMaximumHeight(300)
        self.timeline_scroll.viewport().installEventFilter(self)
        layer_btns = QVBoxLayout()
        btn_add_layer = QPushButton("＋图层")
        btn_del_layer = QPushButton("－图层")
        layer_btns.addWidget(btn_add_layer)
        layer_btns.addWidget(btn_del_layer)
        layer_btns.addStretch(1)
        bottom.addWidget(self.timeline_scroll, 1)
        bottom.addLayout(layer_btns)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addLayout(bar)
        root.addWidget(self._splitter, 1)
        root.addLayout(bottom)

        # ---- 信号 ----
        self.project_combo.activated.connect(self._on_project_pick)
        btn_new.clicked.connect(self._on_project_new)
        btn_save.clicked.connect(self._on_save)
        btn_settings.clicked.connect(self._on_canvas_settings)
        self.btn_play.clicked.connect(self.stage.play)
        btn_pause.clicked.connect(self.stage.pause)
        btn_stop.clicked.connect(self._on_stop)
        self.btn_fullscreen.clicked.connect(self._on_fullscreen_preview)
        btn_export.clicked.connect(self._on_export)
        btn_import.clicked.connect(self._on_import_assets)
        btn_add_layer.clicked.connect(self._on_add_layer)
        btn_del_layer.clicked.connect(self._on_del_layer)
        self.timeline.setAcceptDrops(True)

    # ================= 项目 =================
    def _init_project(self):
        name = self._store.last()
        if name is None:
            if not self._store.projects():
                try:
                    self._store.create("默认项目")
                except ValueError:
                    pass
            names = self._store.projects()
            name = names[0] if names else None
        self._project = self._store.load(name) if name else None
        self._refresh_project_combo(select=self._project.name if self._project else "")
        self._refresh_asset_list()
        self._fill_spine_list()
        self._select("")
        self._emit_change()

    def _refresh_project_combo(self, select: str = ""):
        self._loading = True
        self.project_combo.clear()
        for n in self._store.projects():
            self.project_combo.addItem(n, n)
        idx = self.project_combo.findData(select)
        self.project_combo.setCurrentIndex(max(0, idx))
        self._loading = False

    def _refresh_asset_list(self):
        self.asset_list.clear()
        if self._project:
            for f in self._store.asset_files(self._project.name):
                self.asset_list.addItem(f)

    def _fill_spine_list(self):
        self.spine_list.clear()
        for m in self._library.models():
            self.spine_list.addItem(m)

    def _on_project_pick(self):
        if self._loading:
            return
        name = self.project_combo.currentData()
        proj = self._store.load(name)
        if not proj:
            return
        self._project = proj
        self._store.set_last(name)
        self._refresh_asset_list()
        self._select("")
        self._emit_change()

    def _on_project_new(self):
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称：")
        if not ok:
            return
        try:
            proj = self._store.create(name.strip())
        except ValueError as e:
            QMessageBox.warning(self, "新建项目", str(e))
            return
        self._project = proj
        self._refresh_project_combo(select=proj.name)
        self._refresh_asset_list()
        self._select("")
        self._emit_change()

    def _on_save(self):
        if not self._project:
            return
        self._store.save(self._project)
        from datetime import datetime
        self.status_label.setText("已保存 " + datetime.now().strftime("%H:%M:%S"))

    def _on_canvas_settings(self):
        if not self._project:
            return
        p = self._project
        dlg = QDialog(self)
        dlg.setWindowTitle("画布设置")
        form = QFormLayout(dlg)
        w = QSpinBox(minimum=16, maximum=7680, value=int(p.canvas["w"]))
        h = QSpinBox(minimum=16, maximum=7680, value=int(p.canvas["h"]))
        fps = QSpinBox(minimum=1, maximum=120, value=int(p.canvas["fps"]))
        dur = NoWheelDoubleSpinBox(minimum=0.5, maximum=36000,
                                   value=float(p.duration), singleStep=0.5)
        bg_btn = QPushButton(p.canvas["bg"])
        bg = [p.canvas["bg"]]
        bg_btn.clicked.connect(lambda: self._pick_color(bg, bg_btn))
        form.addRow("宽", w)
        form.addRow("高", h)
        form.addRow("帧率", fps)
        form.addRow("总时长(秒)", dur)
        form.addRow("背景色", bg_btn)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        p.canvas.update({"w": w.value(), "h": h.value(), "fps": fps.value(),
                         "bg": bg[0]})
        p.duration = dur.value()
        self._emit_change()

    def _pick_color(self, holder, btn):
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(holder[0]), self, "背景色")
        if c.isValid():
            holder[0] = c.name()
            btn.setText(c.name())

    # ================= 模型同步 =================
    def _emit_change(self):
        """模型被改 → 防抖同步舞台+时间轴。也会自动延长总时长。"""
        if self._loading or not self._project:
            return
        ends = [c.end for c in self._project.clips]
        if ends and max(ends) > self._project.duration:
            self._project.duration = round(max(ends) * 10) / 10
        self._sync_timer.start()

    def _sync_now(self):
        if not self._project:
            return
        d = self._project.to_dict()
        assets_base = self._store.assets_dir(self._project.name).resolve().as_uri() + "/"
        # 素材版本 = project.json 的 mtime：重新生成/保存后素材 URL 换版拉新
        try:
            rev = int((self._store.root / self._project.name /
                       "project.json").stat().st_mtime)
        except OSError:
            rev = 0
        self.stage.sync_project(d, self._library, assets_base, str(rev))
        self.timeline.set_data(self._project.duration, self._project.layers,
                               d["clips"], self._sel,
                               d.get("layers_visible"))
        self.timeline.setFixedHeight(self.timeline.content_height())
        self._update_timeline_width()
        self.time_label.setText(
            f"{self._current_time:.2f} / {self._project.duration:.2f} s")

    # ================= 片段操作 =================
    def _add_clip(self, kind: str, name: str, x: float, y: float,
                  start: float | None = None, layer: int = 0):
        if not self._project or not name:
            return
        t0 = round((self._current_time if start is None else start) * 10) / 10
        t0 = max(0.0, t0)
        cid = uuid.uuid4().hex[:8]
        if kind == "spine":
            info = self._library.spine_info(name)
            anims = info["animations"] if info else []
            clip = Clip(id=cid, type="spine", asset=name, name=name,
                        layer=layer, start=t0, end=t0 + 3.0, x=x, y=y)
            if anims:
                clip.anims.append(AnimEntry(start=t0, end=t0 + 3.0,
                                            anim=anims[0], speed=1.0, loop=True))
        else:
            clip = Clip(id=cid, type=kind, asset=name, name=name, layer=layer,
                        start=t0, end=t0 + 3.0, x=x, y=y)
        self._project.clips.append(clip)
        self._select(cid)
        self._emit_change()
        self._sync_now()   # 立即推给舞台：拖入立刻看到落点（骨架加载有占位提示）

    def _on_stage_moved(self, clip_id: str, x: float, y: float,
                        ddx: float = 0.0, ddy: float = 0.0):
        clip = self._project.clip(clip_id) if self._project else None
        if not clip:
            return
        clip.x, clip.y = x, y
        if clip.moves and (ddx or ddy):
            # 拖动时活动的平移条目在 JS 侧已跟手，这里把增量落到模型
            for m in clip.moves:
                m.x0 += ddx; m.x1 += ddx
                m.y0 += ddy; m.y1 += ddy
        self._emit_change()
        self._rebuild_props()   # 基准位置变了，刷新右栏

    def _on_timeline_moved(self, clip_id: str, dt: float):
        clip = self._project.clip(clip_id) if self._project else None
        if not clip or abs(dt) < 1e-9:
            return
        clip.start = round((clip.start + dt) * 10) / 10
        clip.end = round((clip.end + dt) * 10) / 10
        for e in clip.anims:
            e.start = round((e.start + dt) * 10) / 10
            e.end = round((e.end + dt) * 10) / 10
        for e in clip.moves:
            e.start = round((e.start + dt) * 10) / 10
            e.end = round((e.end + dt) * 10) / 10
        self._emit_change()

    def _on_timeline_trimmed(self, clip_id: str, start: float, end: float):
        clip = self._project.clip(clip_id) if self._project else None
        if not clip:
            return
        clip.start, clip.end = start, end
        self._emit_change()

    def _on_timeline_drop(self, kind: str, name: str, layer: int, t: float):
        if not self._project:
            return
        x = float(self._project.canvas["w"]) / 2
        y = float(self._project.canvas["h"]) / 2
        self._add_clip(kind, name, x, y, start=t, layer=layer)

    def _on_timeline_pan(self, dx: int):
        sb = self.timeline_scroll.horizontalScrollBar()
        sb.setValue(sb.value() + dx)

    def _on_seek(self, t: float):
        self._current_time = t
        self.stage.set_time(t)
        self.timeline.set_playhead(t)
        self.time_label.setText(
            f"{t:.2f} / {self._project.duration:.2f} s" if self._project else f"{t:.2f}")

    def _on_time(self, t: float):
        changed = abs(t - self._current_time) > 1e-9
        self._current_time = t
        self.timeline.set_playhead(t)
        if self._project:
            self.time_label.setText(f"{t:.2f} / {self._project.duration:.2f} s")
        # 时间变化时，播放头跑出可视范围才自动跟随
        if changed:
            sb = self.timeline_scroll.horizontalScrollBar()
            vw = self.timeline_scroll.viewport().width()
            px = self.timeline.playhead_x()
            if px < sb.value() or px > sb.value() + vw:
                sb.setValue(int(max(0, min(px - vw / 2, sb.maximum()))))
        if self._exporter and self._progress:
            self._progress.setValue(self._exporter.frames)
            # JS 播到结尾（t 到 duration）自然收尾
            if self._project and t >= self._project.duration - 1e-6:
                self._export_finish(True, "")

    def _on_stop(self):
        self.stage.pause()
        self.stage.set_time(0)

    def _on_fullscreen_preview(self):
        if not self._project or self._exporter or self._preview_dialog:
            return
        self._preview_time = self._current_time
        self._preview_sizes = self._splitter.sizes()
        self.stage.pause()
        self.stage.set_time(0)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"全屏预览 - {self._project.name}")
        dlg.setModal(True)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.stage)
        self.stage.setEnabled(False)
        self._preview_dialog = dlg
        dlg.finished.connect(self._on_fullscreen_finished)
        dlg.showFullScreen()
        QTimer.singleShot(0, self.stage.play)

    def _on_fullscreen_finished(self, _result: int):
        dlg = self._preview_dialog
        if dlg is None:
            return
        self.stage.pause()
        self._splitter.insertWidget(1, self.stage)
        self._splitter.setSizes(self._preview_sizes)
        self.stage.setEnabled(True)
        self.stage.show()
        self._on_seek(self._preview_time)
        self._preview_dialog = None
        dlg.deleteLater()

    def eventFilter(self, obj, e):
        # 时间轴宽度 = max(视口宽, 内容宽)：时长超视口时撑开横向滚动
        if obj is self.timeline_scroll.viewport() and \
                e.type() == e.Type.Resize:
            self._update_timeline_width()
        return super().eventFilter(obj, e)

    def _update_timeline_width(self):
        w = max(400, self.timeline_scroll.viewport().width(),
                self.timeline.content_width())
        self.timeline.setFixedWidth(w)

    def _select(self, clip_id: str):
        self._sel = clip_id
        self.timeline.set_selection(clip_id)
        self.stage.select_clip(clip_id)   # 同步给舞台点选循环
        self._rebuild_props()

    # ================= 属性面板 =================
    def _rebuild_props(self):
        while self._props_lay.count():
            item = self._props_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        clip = self._project.clip(self._sel) if self._project else None
        if not clip:
            self._props_lay.addWidget(QLabel("在舞台或时间轴上点选片段\n（从左侧拖素材到舞台/时间轴新建片段）"))
            return
        self._loading = True
        box = QGroupBox(f"片段：{clip.name or clip.asset}")
        form = QFormLayout(box)
        form.setSpacing(1)
        form.setContentsMargins(4, 2, 4, 2)

        name_edit = QLineEdit(clip.name)
        form.addRow("名称", name_edit)
        layer_spin = QSpinBox(minimum=-99, maximum=self._project.layers - 1,
                              value=clip.layer)
        form.addRow("图层（负数=更顶层）", layer_spin)
        start = NoWheelDoubleSpinBox(minimum=0, maximum=36000,
                                     value=clip.start, singleStep=0.1)
        end = NoWheelDoubleSpinBox(minimum=0, maximum=36000,
                                   value=clip.end, singleStep=0.1)
        form.addRow("开始(秒)", start)
        form.addRow("结束(秒)", end)
        scale = NoWheelDoubleSpinBox(minimum=0.01, maximum=100,
                                     value=clip.scale, singleStep=0.05)
        form.addRow("缩放（1=半屏高）" if clip.type == "spine" else "缩放",
                    scale)
        rot = NoWheelDoubleSpinBox(minimum=-36000, maximum=36000,
                                   value=clip.rotation, singleStep=15)
        form.addRow("旋转(°)", rot)
        op = NoWheelDoubleSpinBox(minimum=0, maximum=1, value=clip.opacity,
                                  singleStep=0.05)
        form.addRow("透明度", op)
        x = NoWheelDoubleSpinBox(minimum=-99999, maximum=99999,
                                 value=clip.x, singleStep=10)
        y = NoWheelDoubleSpinBox(minimum=-99999, maximum=99999,
                                 value=clip.y, singleStep=10)
        form.addRow("基准 x" if clip.type == "spine" else "x", x)
        form.addRow("基准 y" if clip.type == "spine" else "y", y)
        del_btn = QPushButton("删除片段")
        del_btn.setProperty("class", "danger")
        form.addRow(del_btn)

        def commit(*_):
            if self._loading:
                return
            clip.name = name_edit.text()
            clip.layer = layer_spin.value()
            clip.start, clip.end = start.value(), end.value()
            clip.scale, clip.rotation, clip.opacity = \
                scale.value(), rot.value(), op.value()
            clip.x, clip.y = x.value(), y.value()
            self._emit_change()

        # 数值框定宽：加减步进按钮留在可视区内，不随表单拉满
        for wdg in (start, end, scale, rot, op, x, y, layer_spin):
            wdg.setFixedWidth(100)
        for wdg in (start, end, scale, rot, op, x, y):
            wdg.valueChanged.connect(commit)
        name_edit.textChanged.connect(commit)
        layer_spin.valueChanged.connect(commit)
        del_btn.clicked.connect(lambda: self._delete_clip(clip.id))
        self._props_lay.addWidget(box)

        if clip.type == "spine":
            info = self._library.spine_info(clip.asset)
            anims = info["animations"] if info else []
            procs = list(self._library.procs(clip.asset).keys())

            g1 = QGroupBox("动画播放（一条一条：x秒~x秒 播 动作）")
            v1 = QVBoxLayout(g1)
            self._anim_editor = AnimEntryEditor()
            self._anim_editor.load(clip, anims, procs)
            self._anim_editor.changed.connect(self._emit_change)
            v1.addWidget(self._anim_editor)
            self._props_lay.addWidget(g1)

        g2 = QGroupBox("平移/绕中心旋转" +
                       ("（与动画独立）" if clip.type == "spine" else ""))
        v2 = QVBoxLayout(g2)
        self._move_editor = MoveEntryEditor()
        self._move_editor.load(clip)
        self._move_editor.changed.connect(self._emit_change)
        v2.addWidget(self._move_editor)
        self._props_lay.addWidget(g2)

        self._props_lay.addStretch(1)
        self._loading = False

    def _delete_clip(self, clip_id: str):
        if self._project and self._project.remove_clip(clip_id):
            self._select("")
            self._emit_change()

    # ================= 图层 / 素材 =================
    def _on_add_layer(self):
        if self._project:
            self._project.layers += 1
            vis = list(self._project.layers_visible) or [True] * (self._project.layers - 1)
            vis.append(True)
            self._project.layers_visible = vis
            self._emit_change()

    def _on_del_layer(self):
        if not self._project or self._project.layers <= 1:
            return
        last = self._project.layers - 1
        if any(c.layer == last for c in self._project.clips):
            QMessageBox.information(self, "删除图层", "最底图层还有片段，先移走或删除")
            return
        self._project.layers -= 1
        vis = list(self._project.layers_visible) or [True] * (self._project.layers + 1)
        self._project.layers_visible = vis[:self._project.layers]
        self._emit_change()

    def _on_layer_toggle(self, row: int):
        """时间轴眼睛开关：切换图层可见性。"""
        if not self._project or not (0 <= row < self._project.layers):
            return
        vis = list(self._project.layers_visible) or [True] * self._project.layers
        vis = (vis + [True] * self._project.layers)[:self._project.layers]
        vis[row] = not vis[row]
        self._project.layers_visible = vis
        self._emit_change()

    def _on_import_assets(self):
        if not self._project:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "导入素材", "", _IMG_EXT)
        if not paths:
            return
        self._store.import_files(self._project.name, paths)
        self._refresh_asset_list()

    # ================= 导出 =================
    def _on_export(self):
        if not self._project or self._exporter:
            return
        out, _ = QFileDialog.getSaveFileName(
            self, "导出视频", f"{self._project.name}.mp4", "MP4 (*.mp4)")
        if not out:
            return
        fps = int(self._project.canvas["fps"])
        total = float(self._project.duration)
        frames = max(1, int(round(total * fps)))
        try:
            self._exporter = VideoExporter(out, fps, frames)
        except ImportError:
            QMessageBox.warning(self, "导出视频",
                                "缺少 imageio-ffmpeg：pip install imageio-ffmpeg")
            return
        self._export_out = out
        self._progress = QProgressDialog("导出中（实时速度）…", "取消", 0, frames, self)
        self._progress.setWindowTitle("导出视频")
        self._progress.setMinimumDuration(0)
        self._progress.canceled.connect(self._export_cancel)
        self.stage.set_export_mode(True)
        self.stage.export_begin()
        self.stage.export_next()   # 步进导出：收到一帧回一脚，直至 expected
        self._progress.show()

    def _on_export_frame(self, b64: str, _index: int):
        ex = self._exporter
        if not ex:
            return
        if self._progress:
            self._progress.setValue(ex.frames)   # 帧到即更新，不依赖 timeUpdate
        if not ex.write_png_base64(b64):
            self._export_finish(False, ex.error or "写帧失败")
            return
        if self._progress:
            self._progress.setValue(ex.frames)
        if ex.done:
            self._export_finish(True, "")
        else:
            self.stage.export_next()

    def _export_cancel(self):
        if self._exporter:
            self._exporter.cancel()
        self._export_finish(False, "已取消")

    def _export_finish(self, ok: bool, err: str):
        ex, self._exporter = self._exporter, None
        self.stage.pause()
        self.stage.set_export_mode(False)
        if self._progress:
            self._progress.close()
            self._progress = None
        if not ex:
            return
        ok2, err2 = ex.finish()
        ok = ok and ok2
        err = err or err2
        if ok:
            box = QMessageBox(self)
            box.setWindowTitle("导出完成")
            box.setText(f"视频已导出：\n{self._export_out}")
            btn_open = box.addButton("打开所在文件夹", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("好的", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is btn_open:
                QDesktopServices.openUrl(QUrl.fromLocalFile(
                    str(Path(self._export_out).parent)))
        else:
            QMessageBox.warning(self, "导出视频", f"导出失败：\n{err}")
