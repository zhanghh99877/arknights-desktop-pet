"""播放页：选 Spine/ 库里的任意模型，即点即播。

动作列表 = 骨架官方动作（skel 提取）+ 自创程序动作
（Spine/proc/<模型名>/*.js，✨ 前缀）。官方动作直接播；程序动作
在官方打底动作之上叠加姿势（见 core/pet_player.py 的运行时契约）。

取景框：全部官方动作的包围盒并集（封顶参照动作 5 倍），
结果按 模型+动作集+程序动作+skel mtime 缓存进库（与 PetWindow 同模式）。

导出MP4：列表下方一个按钮导出当前选中动作，按微信视频规格输出：
内容按全部帧 alpha 包围盒裁剪贴边（去白边）、居中补成方形白底、
480×480、H.264（yuv420p + faststart，微信硬件解码丝滑）、~20fps。
透明背景在视频格式下不存在，角色合成到白底（聊天场景白底无感）。
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRect, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, qAlpha
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QProgressDialog, QPushButton,
    QScrollArea, QWidget,
)

from core.assets import RelayLibrary
from core.pet_config import PetConfig
from core.pet_player import PetPlayer
from ui.widgets import NoWheelComboBox

_PROC_PREFIX = "✨ "
_MP4_FPS = 20              # 视频走硬件解码，20fps 丝滑
_MP4_PROC_SECONDS = 3.0    # 程序动作录 3 秒
_MP4_MAX_SECONDS = 3.5     # 官方动作最多录 3.5 秒
_MP4_SIDE = 480            # 方形边长（H.264 要求偶数，480 安全）
_MP4_MARGIN = 0.05         # 内容包围盒外扩余量（比例）
_MP4_CRF = 20              # 画质（18~23 均可）


class StickerMp4Exporter:
    """JPEG 帧经 stdin pipe → H.264 mp4（yuv420p + faststart，无音频）。

    stderr 写日志文件——ffmpeg 写满管道缓冲会阻塞整个导出。
    """

    def __init__(self, out_path: str | Path, fps: int, expected_frames: int,
                 side: int = _MP4_SIDE, crf: int = _MP4_CRF):
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.expected = max(1, int(expected_frames))
        self.frames = 0
        self.error = ""
        self._out = str(out_path)
        self._cancelled = False
        self._err_path = self._out + ".ffmpeg.log"
        self._err_f = open(self._err_path, "w", encoding="utf-8",
                           errors="replace")
        self._proc = subprocess.Popen(
            [exe, "-hide_banner", "-y",
             "-f", "image2pipe", "-vcodec", "mjpeg", "-r", str(int(fps)),
             "-i", "-",
             "-vf", f"scale={side}:{side}:flags=lanczos",
             "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-crf", str(crf), "-preset", "veryfast",
             "-movflags", "+faststart", "-an",
             self._out],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=self._err_f)

    @property
    def done(self) -> bool:
        return self.frames >= self.expected

    def write_jpg_bytes(self, data: bytes) -> bool:
        if self._cancelled:
            return False
        try:
            self._proc.stdin.write(data)
            self.frames += 1
            return True
        except (BrokenPipeError, OSError, ValueError) as e:
            self.error = f"写帧失败: {e}"
            return False

    def cancel(self):
        self._cancelled = True
        try:
            self._proc.kill()
        except OSError:
            pass

    def finish(self) -> tuple[bool, str]:
        if self._cancelled:
            try:
                self._err_f.close()
            except OSError:
                pass
            return False, "已取消"
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            rc = self._proc.wait(timeout=60)
            self._err_f.close()
            err = Path(self._err_path).read_text(encoding="utf-8",
                                                 errors="replace")
        except Exception as e:
            self.cancel()
            return False, f"ffmpeg 收尾失败: {e}"
        if rc != 0:
            return False, err[-1500:] or f"ffmpeg 退出码 {rc}"
        return True, ""


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
        self._mp4_expected = 0              # 计划帧数（先缓存后编码）
        self._mp4_progress: QProgressDialog | None = None
        self._mp4_name = ""
        self._mp4_is_proc = False
        self._mp4_path = ""
        self._mp4_frames: list[bytes] = []  # 抓取的原始帧（处理后编码）

        # ---- 左侧：模型 + 动作列表 ----
        controls = QGroupBox("播放")
        form = QFormLayout(controls)

        self.model_combo = NoWheelComboBox()
        form.addRow("角色皮肤", self.model_combo)

        self.anim_list = QListWidget()
        self.anim_list.setMinimumHeight(280)
        self.anim_list.currentRowChanged.connect(self._on_pick)
        form.addRow(self.anim_list)

        hint = QLabel("✨ = 自创程序动作；选中动作后点下方按钮导出 MP4")
        form.addRow(hint)

        self.mp4_button = QPushButton("导出选中为MP4")
        self.mp4_button.setFixedHeight(24)
        self.mp4_button.setToolTip("把当前选中的动作导出为方形 MP4（微信视频硬解，丝滑）")
        self.mp4_button.clicked.connect(self._export_selected_mp4)
        form.addRow(self.mp4_button)

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
    def _export_selected_mp4(self):
        """导出当前选中的动作：选路径 → 逐帧确定性渲染 → 裁剪编码。"""
        if self._mp4_expected:
            return
        row = self.anim_list.currentRow()
        item = self.anim_list.item(row) if row >= 0 else None
        if item is None or not self._model:
            return
        display = item.text()
        is_proc = display.startswith(_PROC_PREFIX)
        name = display[len(_PROC_PREFIX):] if is_proc else display

        default_name = self._safe_filename(f"{self._model}_{name}") + ".mp4"
        default_path = str(Path.home() / "Downloads" / default_name)
        out, _ = QFileDialog.getSaveFileName(
            self, "导出为MP4", default_path, "MP4 (*.mp4)")
        if not out:
            return
        if not out.lower().endswith(".mp4"):
            out += ".mp4"

        self._mp4_name = name
        self._mp4_is_proc = is_proc
        self._mp4_path = out
        self._mp4_frames = []
        if is_proc:
            self._begin_mp4_capture(_MP4_PROC_SECONDS)
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
        seconds = min(seconds if seconds > 0 else 1.0, _MP4_MAX_SECONDS)
        self._begin_mp4_capture(seconds)

    def _begin_mp4_capture(self, seconds: float):
        self._mp4_expected = max(1, int(round(seconds * _MP4_FPS)))
        self._set_mp4_controls_enabled(False)
        self._mp4_progress = QProgressDialog(
            f"正在导出 {self._mp4_name} …", "取消", 0, self._mp4_expected, self)
        self._mp4_progress.setWindowTitle("导出为MP4")
        self._mp4_progress.setMinimumDuration(0)
        self._mp4_progress.canceled.connect(self._cancel_mp4_export)
        self._mp4_progress.show()
        QTimer.singleShot(0, self._render_next_gif_frame)

    def _render_next_gif_frame(self):
        if not self._mp4_expected:
            return
        t = len(self._mp4_frames) / _MP4_FPS
        if self._mp4_is_proc:
            self.preview.render_pose(proc=self._mp4_name, t=t, fps=_MP4_FPS,
                                     callback=self._on_gif_frame_rendered)
        else:
            self.preview.render_pose(animation=self._mp4_name, t=t, fps=_MP4_FPS,
                                     callback=self._on_gif_frame_rendered)

    def _on_gif_frame_rendered(self, ok):
        if not ok:
            self._finish_mp4_export(False, "渲染预览帧失败")
            return
        self.preview.grab_canvas_png(self._on_gif_frame_png)

    def _on_gif_frame_png(self, data_url):
        if not self._mp4_expected:
            return
        if not data_url or "," not in data_url:
            self._finish_mp4_export(False, "从画布读取帧失败（页面未就绪？）")
            return
        try:
            data = base64.b64decode(data_url.split(",", 1)[1])
        except (ValueError, IndexError):
            self._finish_mp4_export(False, "帧数据解码失败")
            return
        self._mp4_frames.append(data)
        if self._mp4_progress:
            self._mp4_progress.setValue(len(self._mp4_frames))
        if len(self._mp4_frames) >= self._mp4_expected:
            if self._mp4_progress:
                self._mp4_progress.setLabelText("裁剪与编码中…")
            QTimer.singleShot(0, self._process_and_encode)
        else:
            QTimer.singleShot(0, self._render_next_gif_frame)

    def _cancel_mp4_export(self):
        self._mp4_frames = []
        self._finish_mp4_export(False, "已取消")

    # ---- 后处理与编码 ----
    @staticmethod
    def _alpha_bbox(img: QImage):
        """非透明像素的包围盒（步长 2 扫描提速）；全空返回 None。"""
        w, h = img.width(), img.height()
        minx, miny, maxx, maxy = w, h, -1, -1
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                if qAlpha(img.pixel(x, y)) > 10:
                    if x < minx: minx = x
                    if x > maxx: maxx = x
                    if y < miny: miny = y
                    if y > maxy: maxy = y
        if maxx < 0:
            return None
        return minx, miny, maxx + 1, maxy + 1

    def _fit_frames_square(self, frames_png: list[bytes]) -> list[bytes]:
        """去白边贴边：按全部帧的 alpha 并集裁出角色，外扩余量后居中
        补成方形。视频无 alpha，角色合成到白底（聊天场景白底无感），
        输出 JPEG 帧供 H.264 编码。"""
        imgs = []
        bbox = None
        for data in frames_png:
            img = QImage.fromData(data)
            if img.isNull():
                continue
            img = img.convertToFormat(QImage.Format.Format_ARGB32)
            imgs.append(img)
            b = self._alpha_bbox(img)
            if b:
                bbox = b if bbox is None else (
                    min(bbox[0], b[0]), min(bbox[1], b[1]),
                    max(bbox[2], b[2]), max(bbox[3], b[3]))
        if not imgs:
            return []
        if bbox is None:
            bbox = (0, 0, imgs[0].width(), imgs[0].height())
        x0, y0, x1, y1 = bbox
        bw, bh = x1 - x0, y1 - y0
        m = int(max(bw, bh) * _MP4_MARGIN)
        x0 = max(0, x0 - m); y0 = max(0, y0 - m)
        x1 = min(imgs[0].width(), x0 + bw + 2 * m)
        y1 = min(imgs[0].height(), y0 + bh + 2 * m)
        bw, bh = x1 - x0, y1 - y0
        side = max(bw, bh)
        out = []
        for img in imgs:
            canvas = QImage(side, side, QImage.Format.Format_RGB32)
            canvas.fill(QColor("#ffffff"))
            painter = QPainter(canvas)
            painter.drawImage((side - bw) // 2, (side - bh) // 2,
                              img.copy(QRect(x0, y0, bw, bh)))
            painter.end()
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.ReadWrite)
            canvas.save(buf, "JPG", 95)
            out.append(bytes(buf.data()))
        return out

    def _process_and_encode(self):
        frames = self._fit_frames_square(self._mp4_frames)
        if not frames:
            self._finish_mp4_export(False, "没有可用帧")
            return
        try:
            ex = StickerMp4Exporter(self._mp4_path, _MP4_FPS, len(frames))
        except ImportError:
            self._finish_mp4_export(False,
                                    "缺少 imageio-ffmpeg：pip install imageio-ffmpeg")
            return
        except Exception as e:
            self._finish_mp4_export(False, f"编码器启动失败：{e}")
            return
        for f in frames:
            if not ex.write_jpg_bytes(f):
                ex.cancel()
                self._finish_mp4_export(False, ex.error or "写帧失败")
                return
        ok, err = ex.finish()
        self._finish_mp4_export(ok, err)

    def _finish_mp4_export(self, ok: bool, error: str):
        self._mp4_expected = 0
        if self._mp4_progress:
            self._mp4_progress.close()
            self._mp4_progress = None

        # 导出期间把动作推进到了暂停单帧；恢复当前条目为循环播放。
        row = self.anim_list.currentRow()
        if row >= 0 and not self._loading:
            self._on_pick(row)

        self._set_mp4_controls_enabled(True)
        if not self._mp4_path:
            return
        if ok:
            size = Path(self._mp4_path).stat().st_size
            box = QMessageBox(self)
            box.setWindowTitle("导出完成")
            box.setText(f"MP4 已导出（{_MP4_SIDE}px 方形 · 白底 · "
                        f"{size / 1024:.0f} KB）：\n{self._mp4_path}")
            btn_open = box.addButton("打开所在文件夹", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("好的", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is btn_open:
                QDesktopServices.openUrl(QUrl.fromLocalFile(
                    str(Path(self._mp4_path).parent)))
        elif error != "已取消":
            QMessageBox.warning(self, "导出为MP4", f"导出失败：\n{error}")

    def _set_mp4_controls_enabled(self, enabled: bool):
        self.anim_list.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.mp4_button.setEnabled(enabled)

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
