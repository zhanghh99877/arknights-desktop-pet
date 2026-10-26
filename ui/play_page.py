"""播放页：选 Spine/ 库里的任意模型，即点即播。

动作列表 = 骨架官方动作（skel 提取）+ 自创程序动作
（Spine/proc/<模型名>/*.js，✨ 前缀）。官方动作直接播；程序动作
在官方打底动作之上叠加姿势（见 core/pet_player.py 的运行时契约）。

取景框：全部官方动作的包围盒并集（封顶参照动作 5 倍），
结果按 模型+动作集+程序动作+skel mtime 缓存进库（与 PetWindow 同模式）。

导出GIF：列表下方一个按钮导出当前选中动作。帧从页面 WebGL 画布
JS 读回（widget.grab 抓 WebGL 不可靠），ffmpeg 调色板编码；
超过 1MB 自动降分辨率/减色重编码。
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QProgressDialog, QPushButton,
    QScrollArea, QWidget,
)

from core.assets import RelayLibrary
from core.gif_exporter import GifExporter
from core.pet_config import PetConfig
from core.pet_player import PetPlayer
from ui.widgets import NoWheelComboBox

_PROC_PREFIX = "✨ "
_GIF_FPS = 15               # 贴纸级 GIF 15fps 足够
_GIF_PROC_SECONDS = 3.0     # 程序动作录 3 秒
_GIF_MAX_SECONDS = 3.5      # 官方动作最多录 3.5 秒（体积控制）
_GIF_SIZE_LIMIT = 1_000_000
# 超限时按序降级：(最大边长, 色数)
_GIF_FALLBACKS = ((240, 128), (192, 96), (160, 64))


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
        self._gif_exporter: GifExporter | None = None
        self._gif_progress: QProgressDialog | None = None
        self._gif_name = ""
        self._gif_is_proc = False
        self._gif_path = ""
        self._gif_frames: list[bytes] = []  # 已抓帧，供超限降级重编码

        # ---- 左侧：模型 + 动作列表 ----
        controls = QGroupBox("播放")
        form = QFormLayout(controls)

        self.model_combo = NoWheelComboBox()
        form.addRow("角色皮肤", self.model_combo)

        self.anim_list = QListWidget()
        self.anim_list.setMinimumHeight(280)
        self.anim_list.currentRowChanged.connect(self._on_pick)
        form.addRow(self.anim_list)

        hint = QLabel("✨ = 自创程序动作；选中动作后点下方按钮导出 GIF")
        form.addRow(hint)

        self.gif_button = QPushButton("导出选中为GIF")
        self.gif_button.setFixedHeight(24)
        self.gif_button.setToolTip("把当前选中的动作导出为 GIF（≤1MB）")
        self.gif_button.clicked.connect(self._export_selected_gif)
        form.addRow(self.gif_button)

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
            self.anim_list.addItem(QListWidgetItem(a))
        for name in self._procs:
            item = QListWidgetItem(_PROC_PREFIX + name)
            item.setToolTip("自创程序动作（Spine/proc/<模型名>/ 下的 .js）")
            self.anim_list.addItem(item)
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

    @staticmethod
    def _safe_filename(value: str) -> str:
        value = re.sub(r'[\\/:*?"<>|\r\n]+', "_", value)
        return value.strip(" .") or "未命名"

    # ---- GIF 导出 ----
    def _export_selected_gif(self):
        """导出当前选中的动作：选路径 → 逐帧确定性渲染 → 调色板编码。"""
        if self._gif_exporter:
            return
        row = self.anim_list.currentRow()
        item = self.anim_list.item(row) if row >= 0 else None
        if item is None or not self._model:
            return
        display = item.text()
        is_proc = display.startswith(_PROC_PREFIX)
        name = display[len(_PROC_PREFIX):] if is_proc else display

        default_name = self._safe_filename(f"{self._model}_{name}") + ".gif"
        default_path = str(Path.home() / "Downloads" / default_name)
        out, _ = QFileDialog.getSaveFileName(
            self, "导出为GIF", default_path, "GIF (*.gif)")
        if not out:
            return
        if not out.lower().endswith(".gif"):
            out += ".gif"

        self._gif_name = name
        self._gif_is_proc = is_proc
        self._gif_path = out
        self._gif_frames = []
        if is_proc:
            self._begin_gif_export(out, _GIF_PROC_SECONDS)
        else:
            self._query_gif_duration(name, out)

    def _query_gif_duration(self, name: str, out: str):
        js = f"""
        (function() {{
          var p = window.player;
          if (!p || !p.loaded) return -1;
          var a = p.skeleton.data.findAnimation({json.dumps(name)});
          return a ? a.duration : -1;
        }})()
        """
        self.preview.page().runJavaScript(
            js, lambda duration, path=out: self._on_gif_duration(duration, path))

    def _on_gif_duration(self, duration, out: str):
        try:
            seconds = float(duration)
        except (TypeError, ValueError):
            seconds = 0.0
        seconds = min(seconds if seconds > 0 else 1.0, _GIF_MAX_SECONDS)
        self._begin_gif_export(out, seconds)

    def _begin_gif_export(self, out: str, seconds: float):
        frames = max(1, int(round(seconds * _GIF_FPS)))
        try:
            self._gif_exporter = GifExporter(out, _GIF_FPS, frames)
        except ImportError:
            QMessageBox.warning(self, "导出为GIF",
                                "缺少 imageio-ffmpeg：pip install imageio-ffmpeg")
            return
        except Exception as e:
            QMessageBox.warning(self, "导出为GIF", f"无法启动导出：\n{e}")
            return

        self._set_gif_controls_enabled(False)
        self._gif_progress = QProgressDialog(
            f"正在导出 {self._gif_name} …", "取消", 0, frames, self)
        self._gif_progress.setWindowTitle("导出为GIF")
        self._gif_progress.setMinimumDuration(0)
        self._gif_progress.canceled.connect(self._cancel_gif_export)
        self._gif_progress.show()
        QTimer.singleShot(0, self._render_next_gif_frame)

    def _render_next_gif_frame(self):
        exporter = self._gif_exporter
        if not exporter:
            return
        t = exporter.frames / _GIF_FPS
        if self._gif_is_proc:
            self.preview.render_pose(proc=self._gif_name, t=t, fps=_GIF_FPS,
                                     callback=self._on_gif_frame_rendered)
        else:
            self.preview.render_pose(animation=self._gif_name, t=t, fps=_GIF_FPS,
                                     callback=self._on_gif_frame_rendered)

    def _on_gif_frame_rendered(self, ok):
        if not ok:
            self._finish_gif_export(False, "渲染预览帧失败")
            return
        self.preview.grab_canvas_png(self._on_gif_frame_png)

    def _on_gif_frame_png(self, data_url):
        exporter = self._gif_exporter
        if not exporter:
            return
        if not data_url or "," not in data_url:
            self._finish_gif_export(False, "从画布读取帧失败（页面未就绪？）")
            return
        try:
            data = base64.b64decode(data_url.split(",", 1)[1])
        except (ValueError, IndexError):
            self._finish_gif_export(False, "帧数据解码失败")
            return
        self._gif_frames.append(data)
        if not exporter.write_png_bytes(data):
            self._finish_gif_export(False, exporter.error or "写帧失败")
            return
        if self._gif_progress:
            self._gif_progress.setValue(exporter.frames)
        if exporter.done:
            self._finish_gif_export(True, "")
        else:
            QTimer.singleShot(0, self._render_next_gif_frame)

    def _cancel_gif_export(self):
        exporter = self._gif_exporter
        if not exporter:
            return
        exporter.cancel()
        self._finish_gif_export(False, "已取消")

    def _reencode_gif(self, max_side: int, colors: int) -> tuple[bool, str]:
        """用已缓存的帧按更小参数重编码（超 1MB 时降级）。"""
        try:
            ex = GifExporter(self._gif_path, _GIF_FPS, len(self._gif_frames),
                             max_side=max_side, colors=colors)
        except Exception as e:
            return False, f"降级重编码启动失败: {e}"
        for f in self._gif_frames:
            if not ex.write_png_bytes(f):
                ex.cancel()
                return False, ex.error or "写帧失败"
        return ex.finish()

    def _finish_gif_export(self, ok: bool, error: str):
        exporter, self._gif_exporter = self._gif_exporter, None
        if self._gif_progress:
            self._gif_progress.close()
            self._gif_progress = None

        # 导出期间把动作推进到了暂停单帧；恢复当前条目为循环播放。
        row = self.anim_list.currentRow()
        if row >= 0 and not self._loading:
            self._on_pick(row)

        if not exporter:
            self._set_gif_controls_enabled(True)
            return
        ok2, err2 = exporter.finish()
        ok = ok and ok2
        error = error or err2

        # 体积控制：超 1MB 按 (边长, 色数) 阶梯降级重编码
        if ok and self._gif_path:
            for max_side, colors in _GIF_FALLBACKS:
                try:
                    if Path(self._gif_path).stat().st_size <= _GIF_SIZE_LIMIT:
                        break
                except OSError:
                    break
                ok, error = self._reencode_gif(max_side, colors)
                if not ok:
                    break

        self._set_gif_controls_enabled(True)
        if ok:
            size = Path(self._gif_path).stat().st_size
            box = QMessageBox(self)
            box.setWindowTitle("导出完成")
            box.setText(f"GIF 已导出（{size/1024:.0f} KB）：\n{self._gif_path}")
            btn_open = box.addButton("打开所在文件夹", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("好的", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is btn_open:
                QDesktopServices.openUrl(QUrl.fromLocalFile(
                    str(Path(self._gif_path).parent)))
        elif error != "已取消":
            QMessageBox.warning(self, "导出为GIF", f"导出失败：\n{error}")

    def _set_gif_controls_enabled(self, enabled: bool):
        self.anim_list.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.gif_button.setEnabled(enabled)

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
