"""工作区项目模型与存储。

项目 = workspace/<项目名>/ 文件夹：
    project.json   文档（画布/图层/片段/条目）
    assets/        项目素材（导入的 PNG/SVG/HTML 拷入此处）

Spine 模型是公用素材：片段按模型名引用 Spine/ 库，不复制。
片段（Clip）：
- spine：存在区间 + 基准变换 + 动画播放条目(anims) + 平移/旋转条目(moves)；
- png/svg：存在区间 + 静态变换。
求值语义见 html/stage.js（JS 实现为准）：
    move 条目命中 → 线性插值；否则夹取到最近条目的端点值；
    anim 条目命中 → 切动作、trackTime=(t-start)*speed，loop 取模否则
    clamp 冻结末帧；条目之间冻结上一动作；都没有 → setup pose。
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

PRTS_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = PRTS_ROOT / "workspace"

CANVAS_DEFAULT = {"w": 1280, "h": 720, "fps": 30, "bg": "#ffffff"}
SCHEMA = 1

_NAME_OK = re.compile(r"^[^\\/:*?\"<>|]{1,60}$")


@dataclass
class AnimEntry:
    """一段动画播放：x秒-x秒 播 anim，speed 倍速，loop=播1次或循环。"""
    start: float = 0.0
    end: float = 2.0
    anim: str = ""
    speed: float = 1.0
    loop: bool = False


@dataclass
class MoveEntry:
    """一段平移+绕中心旋转：x秒-x秒 从 (x0,y0,rot0) 插值到 (x1,y1,rot1)。"""
    start: float = 0.0
    end: float = 2.0
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    rot0: float = 0.0
    rot1: float = 0.0


@dataclass
class Clip:
    id: str
    type: str                    # spine | png | svg
    asset: str                   # 模型名（spine）或 assets/ 内文件名
    name: str = ""
    layer: int = 0               # 图层行号（0 = 最上层）
    start: float = 0.0
    end: float = 3.0
    x: float = 640.0             # 舞台像素（y 向下）；spine 为脚底中心
    y: float = 500.0
    scale: float = 1.0
    rotation: float = 0.0        # 度，绕中心（spine 绕脚底中心）
    opacity: float = 1.0
    anims: list[AnimEntry] = field(default_factory=list)   # 仅 spine
    moves: list[MoveEntry] = field(default_factory=list)   # 仅 spine

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "asset": self.asset,
            "name": self.name, "layer": self.layer,
            "start": self.start, "end": self.end,
            "x": self.x, "y": self.y, "scale": self.scale,
            "rotation": self.rotation, "opacity": self.opacity,
            "anims": [vars(a) for a in self.anims],
            "moves": [vars(m) for m in self.moves],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Clip":
        def f(key, default=0.0):
            try:
                return float(d.get(key, default))
            except (TypeError, ValueError):
                return default
        anims = [AnimEntry(**{k: float(v) if k != "anim" else str(v)
                              for k, v in a.items()})
                 for a in d.get("anims", []) if isinstance(a, dict)]
        moves = [MoveEntry(**{k: float(v) for k, v in m.items()})
                 for m in d.get("moves", []) if isinstance(m, dict)]
        return cls(
            id=str(d.get("id", "")), type=str(d.get("type", "png")),
            asset=str(d.get("asset", "")), name=str(d.get("name", "")),
            layer=int(f("layer")), start=f("start"), end=f("end", 3.0),
            x=f("x", 640.0), y=f("y", 500.0), scale=f("scale", 1.0) or 1.0,
            rotation=f("rotation"), opacity=f("opacity", 1.0),
            anims=anims, moves=moves,
        )


@dataclass
class Project:
    name: str = ""
    canvas: dict = field(default_factory=lambda: dict(CANVAS_DEFAULT))
    duration: float = 5.0
    layers: int = 3              # 图层行数（行序即 z 序，0 行最上层）
    clips: list[Clip] = field(default_factory=list)
    schema: int = SCHEMA

    def to_dict(self) -> dict:
        return {
            "schema": self.schema, "name": self.name,
            "canvas": dict(self.canvas), "duration": self.duration,
            "layers": self.layers,
            "clips": [c.to_dict() for c in self.clips],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        canvas = dict(CANVAS_DEFAULT)
        canvas.update({k: d.get("canvas", {}).get(k, v)
                       for k, v in CANVAS_DEFAULT.items()})
        return cls(
            name=str(d.get("name", "")),
            canvas=canvas,
            duration=float(d.get("duration", 5.0) or 5.0),
            layers=max(1, int(d.get("layers", 3) or 3)),
            clips=[Clip.from_dict(c) for c in d.get("clips", [])
                   if isinstance(c, dict)],
            schema=int(d.get("schema", SCHEMA) or SCHEMA),
        )

    def clip(self, clip_id: str) -> Clip | None:
        for c in self.clips:
            if c.id == clip_id:
                return c
        return None

    def remove_clip(self, clip_id: str) -> bool:
        before = len(self.clips)
        self.clips = [c for c in self.clips if c.id != clip_id]
        return len(self.clips) != before


def _norm_name(name: str) -> str:
    name = name.strip()
    if not name or not _NAME_OK.match(name) or name.startswith("."):
        raise ValueError(f"项目名不合法：{name!r}（不能含 \\ / : * ? \" < > |）")
    return name


class WorkspaceStore:
    """workspace/ 下的项目文件夹管理 + project.json 读写。"""

    def __init__(self, root: Path = WORKSPACE_DIR):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- 项目管理 ----
    def projects(self) -> list[str]:
        """全部项目名（含 project.json 的文件夹，按名称排序）。"""
        out = []
        for p in sorted(self.root.iterdir()):
            if p.is_dir() and (p / "project.json").exists():
                out.append(p.name)
        return out

    def create(self, name: str) -> Project:
        """新建项目：建文件夹 + assets/ + 默认 project.json。"""
        name = _norm_name(name)
        folder = self.root / name
        if (folder / "project.json").exists():
            raise ValueError(f"项目「{name}」已存在")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "assets").mkdir(exist_ok=True)
        proj = Project(name=name)
        self.save(proj)
        self.set_last(name)
        return proj

    def save(self, proj: Project):
        folder = self.root / _norm_name(proj.name or "未命名")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "assets").mkdir(exist_ok=True)
        data = proj.to_dict()
        data["name"] = folder.name
        (folder / "project.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        proj.name = folder.name
        self.set_last(folder.name)

    def load(self, name: str) -> Project | None:
        try:
            name = _norm_name(name)
        except ValueError:
            return None
        path = self.root / name / "project.json"
        if not path.exists():
            return None
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        proj = Project.from_dict(d)
        proj.name = name
        return proj

    def assets_dir(self, name: str) -> Path:
        return self.root / _norm_name(name) / "assets"

    def asset_uri(self, name: str, filename: str) -> str:
        """assets/ 内文件的 file:// URI（给 stage.js 加载用）。"""
        p = self.assets_dir(name) / filename
        return p.resolve().as_uri()

    def import_files(self, name: str, paths) -> list[str]:
        """把外部文件拷进项目 assets/，返回拷入后的文件名列表。"""
        dest = self.assets_dir(name)
        dest.mkdir(parents=True, exist_ok=True)
        out = []
        for src in paths:
            src = Path(src)
            if not src.is_file():
                continue
            target = dest / src.name
            n = 1
            while target.exists():  # 重名自动加序号
                target = dest / f"{src.stem}_{n}{src.suffix}"
                n += 1
            shutil.copy2(src, target)
            out.append(target.name)
        return out

    def asset_files(self, name: str) -> list[str]:
        """项目 assets/ 下的素材文件名（png/svg/html，排序）。"""
        dest = self.assets_dir(name)
        if not dest.is_dir():
            return []
        exts = {".png", ".svg", ".html", ".htm"}
        return sorted(p.name for p in dest.iterdir()
                      if p.is_file() and p.suffix.lower() in exts)

    # ---- 最后打开的项目 ----
    def set_last(self, name: str):
        try:
            (self.root / ".last").write_text(_norm_name(name), encoding="utf-8")
        except (OSError, ValueError):
            pass

    def last(self) -> str | None:
        try:
            name = (self.root / ".last").read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return name if name in self.projects() else None
