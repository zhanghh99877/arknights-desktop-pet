"""GIF 导出：PNG 帧经 stdin pipe 喂 ffmpeg 调色板编码。"""

from __future__ import annotations

import subprocess
from pathlib import Path


class GifExporter:
    """管理 ffmpeg 子进程；write_png_bytes 逐帧写入，finish 收尾。

    max_side/colors 控制体积：帧先等比缩到 max_side 边长，再用
    palettegen 量化到 colors 色。贴纸级小 GIF 一般 (320, 256)。
    """

    def __init__(self, out_path: str | Path, fps: int, expected_frames: int,
                 max_side: int = 320, colors: int = 256):
        import imageio_ffmpeg  # 静态 ffmpeg（requirements 依赖）
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.expected = max(1, int(expected_frames))
        self.frames = 0
        self.error = ""
        self._out = str(out_path)
        self._cancelled = False
        self._err_path = self._out + ".ffmpeg.log"
        self._err_f = open(self._err_path, "w", encoding="utf-8",
                           errors="replace")
        palette = (f"[0:v]scale={int(max_side)}:-2:flags=lanczos,"
                   f"split[s0][s1];[s0]palettegen=max_colors={int(colors)}[p];"
                   "[s1][p]paletteuse=dither=bayer:bayer_scale=5[v]")
        self._proc = subprocess.Popen(
            [exe, "-hide_banner", "-y",
             "-f", "image2pipe", "-vcodec", "png", "-r", str(int(fps)),
             "-i", "-",
             "-filter_complex", palette,
             "-map", "[v]", "-loop", "0",
             self._out],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=self._err_f)

    @property
    def done(self) -> bool:
        return self.frames >= self.expected

    def write_png_bytes(self, data: bytes) -> bool:
        """写入一帧 PNG 字节。失败返回 False 并记录 error。"""
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
        """关闭 stdin 等 ffmpeg 退出。返回 (成功, 错误信息)。"""
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
