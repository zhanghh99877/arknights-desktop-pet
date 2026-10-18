"""视频导出：JPEG 帧经 stdin pipe 喂 ffmpeg → H.264 mp4。

帧来源：stage.js 导出模式按项目 fps 抽帧 toDataURL('image/jpeg') 经
QWebChannel 回传（PNG 单帧 0.3~1MB 传输太慢，JPEG 快一个数量级）。
实时速度：时间轴多长，导出多久；播放头走到结尾即收尾。
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path


class VideoExporter:
    """管理 ffmpeg 子进程；write_png_base64 逐帧写入，finish 收尾。"""

    def __init__(self, out_path: str | Path, fps: int, expected_frames: int,
                 crf: int = 18):
        import imageio_ffmpeg  # 静态 ffmpeg（requirements 依赖）
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.expected = max(1, int(expected_frames))
        self.frames = 0
        self.error = ""
        self._out = str(out_path)
        self._cancelled = False
        # stderr 不能走 PIPE 且不读：ffmpeg 写满管道缓冲会阻塞 →
        # Python stdin 写阻塞 → Qt 主线程卡死、帧流停滞。写日志文件。
        self._err_path = self._out + ".ffmpeg.log"
        self._err_f = open(self._err_path, "w", encoding="utf-8",
                           errors="replace")
        self._proc = subprocess.Popen(
            [exe, "-hide_banner", "-y",
             "-f", "image2pipe", "-vcodec", "mjpeg", "-r", str(int(fps)),
             "-i", "-",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf),
             self._out],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=self._err_f)

    @property
    def done(self) -> bool:
        return self.frames >= self.expected

    def write_png_base64(self, b64: str) -> bool:
        """写入一帧（dataURL 字符串）。失败返回 False 并记录 error。"""
        if self._cancelled:
            return False
        try:
            data = base64.b64decode(b64.split(",", 1)[-1])
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
        """关闭 stdin 等 ffmpeg 退出。返回 (成功, 错误信息)。"""
        if self._cancelled:
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
