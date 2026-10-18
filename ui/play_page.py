"""播放页：选 Spine/ 库里的任意模型，即点即播。

动作列表 = 骨架官方动作（skel 提取）+ 自创程序动作
（Spine/proc/<模型名>/*.js，✨ 前缀）。官方动作直接播；程序动作
在官方打底动作之上叠加姿势（见 core/pet_player.py 的运行时契约）。

取景框：全部官方动作的包围盒并集（封顶参照动作 5 倍），
结果按 模型+动作集+程序动作+skel mtime 缓存进库（与 PetWindow 同模式）。
"""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QScrollArea, QWidget,
)

from core.assets import RelayLibrary
from core.pet_config import PetConfig
from core.pet_player import PetPlayer
from ui.widgets import NoWheelComboBox

_PROC_PREFIX = "✨ "


class PlayPage(QWidget):
    """播放页：模型下拉 + 动作列表（官方/自创）+ 内嵌渲染预览。"""

    def __init__(self, library: RelayLibrary, config_store: PetConfig,
                 parent=None):
        super().__init__(parent)
        self._library = library
        self._cfg_store = config_store
        self._model: str | None = None      # 当前已加载的模型名
        self._procs: dict[str, str] = {}    # 当前模型的程序动作 {名: JS 源码}
        self._vp_sig: tuple | None = None   # 取景框缓存键 (model, sig)
        self._loading = False               # 初始填充期间不触发加载

        # ---- 左侧：模型 + 动作列表 ----
        controls = QGroupBox("播放")
        form = QFormLayout(controls)

        self.model_combo = NoWheelComboBox()
        form.addRow("角色皮肤", self.model_combo)

        self.anim_list = QListWidget()
        self.anim_list.setMinimumHeight(280)
        self.anim_list.currentRowChanged.connect(self._on_pick)
        form.addRow(self.anim_list)

        hint = QLabel("✨ = 自创程序动作（Spine/proc/<模型名>/ 下的 .js）")
        form.addRow(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(300)
        scroll.setWidget(controls)

        # ---- 右侧：渲染预览 ----
        self.preview = PetPlayer(background="#ffffff")
        self.preview.setMinimumSize(420, 420)
        # JS 算完取景框 → 落库缓存
        self.preview.bridge.viewportComputed.connect(self._on_viewport_computed)

        layout = QHBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(self.preview, 2)

        for m in library.models():
            self.model_combo.addItem(m, m)
        self.model_combo.currentIndexChanged.connect(self._reload_model)

        self._loading = True
        self.model_combo.setCurrentIndex(0)
        self._loading = False
        self._reload_model()

    # ---- 模型 / 动作列表 ----
    def _reload_model(self):
        """切模型：整套重载（骨架 + 程序动作），列表重填，默认播第一个官方动作。"""
        model = self.model_combo.currentData()
        info = self._library.spine_info(model)
        if not info:
            return
        self._model = model
        self._procs = self._read_procs(model)
        anims = info["animations"]

        self.anim_list.blockSignals(True)
        self.anim_list.clear()
        for a in anims:
            self.anim_list.addItem(a)
        for name in self._procs:
            it = QListWidgetItem(_PROC_PREFIX + name)
            it.setToolTip("自创程序动作（Spine/proc/<模型名>/ 下的 .js）")
            self.anim_list.addItem(it)
        self.anim_list.blockSignals(False)

        # 取景参照确定性：排序后取第一个（缓存键稳定，与 PetWindow 同思路）
        fit_ref = sorted(anims)[0] if anims else ""
        sig = json.dumps({
            "anims": sorted(anims), "procs": sorted(self._procs),
            "mtime": info["skel"].stat().st_mtime,
        })
        cached_vp = self._cfg_store.get_viewport(model, sig) \
            if self._cfg_store else None
        self._vp_sig = (model, sig)

        first = anims[0] if anims else ""
        self.preview.play_spine(
            info["skel"], info["atlas"], first, loop=True,
            fit=fit_ref, fit_all=anims, viewport=cached_vp,
            procs=self._procs or None)
        # 列表指到初始动作
        self.anim_list.blockSignals(True)
        self.anim_list.setCurrentRow(0)
        self.anim_list.blockSignals(False)

    def _read_procs(self, model: str) -> dict[str, str]:
        """读取模型的程序动作 JS 源码；读失败的文件跳过（列表里也不出现）。"""
        out = {}
        for name, path in self._library.procs(model).items():
            try:
                out[name] = path.read_text(encoding="utf-8")
            except OSError as e:
                print(f"[play] 程序动作 {path.name} 读取失败: {e}")
        return out

    def _on_pick(self, row: int):
        """列表选择：官方动作直接播；程序动作走叠加层。"""
        if row < 0 or self._loading:
            return
        item = self.anim_list.item(row)
        if item is None:
            return
        text = item.text()
        if text.startswith(_PROC_PREFIX):
            self.preview.set_proc(text[len(_PROC_PREFIX):])
        else:
            self.preview.set_animation(text, loop=True)

    # ---- 取景框缓存 ----
    def _on_viewport_computed(self, vp_json: str):
        """JS 算完并集取景框 → 按当前缓存键落库，下次加载直接套用。"""
        if not self._cfg_store or not self._vp_sig:
            return
        try:
            vp = json.loads(vp_json)
        except ValueError:
            return
        self._cfg_store.set_viewport(self._vp_sig[0], self._vp_sig[1], vp)
