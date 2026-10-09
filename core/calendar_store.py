"""日历事项存储：SQLite。

事项（event）与 DDL（ddl）同表，kind 区分。
DDL 提醒策略：有时间的 DDL 在截止前 REMIND_AHEAD 分钟开始提醒；
无时间的按当天 09:00 处理。每条只提醒一次（notified 落库，重启不重复打扰）。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from core.assets import PRTS_ROOT

DB_PATH = PRTS_ROOT / "data" / "prts.db"

REMIND_AHEAD_MIN = 60          # 截止前多久开始提醒
NO_TIME_DDL_HOUR = 9           # 全天 DDL 视为当天 9 点

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    date     TEXT NOT NULL,            -- YYYY-MM-DD
    time     TEXT,                     -- HH:MM，NULL = 全天
    title    TEXT NOT NULL,
    note     TEXT NOT NULL DEFAULT '',
    kind     TEXT NOT NULL DEFAULT 'event',  -- event | ddl
    done     INTEGER NOT NULL DEFAULT 0,
    notified INTEGER NOT NULL DEFAULT 0,
    parent_id INTEGER                  -- 子任务指向父任务；NULL = 顶层任务
);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(date);
"""


class CalendarStore:
    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        # 老库迁移：补 parent_id 列（子任务）
        cols = [r[1] for r in self._conn.execute("PRAGMA table_info(events)")]
        if "parent_id" not in cols:
            self._conn.execute(
                "ALTER TABLE events ADD COLUMN parent_id INTEGER")
            self._conn.commit()

    # ---- 增删改 ----
    def add_event(self, date: str, title: str, kind: str = "event",
                  time: str | None = None, note: str = "",
                  parent_id: int | None = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO events(date, time, title, note, kind, parent_id)"
            " VALUES (?,?,?,?,?,?)",
            (date, time, title, note, kind, parent_id),
        )
        self._conn.commit()
        return cur.lastrowid

    def set_done(self, event_id: int, done: bool) -> int:
        """设置完成状态；完成父任务时级联完成其整棵子任务树。

        返回级联完成的任务数（未级联则 0）。
        """
        self._conn.execute("UPDATE events SET done=? WHERE id=?",
                           (int(done), event_id))
        cascaded = 0
        if done:
            self._conn.execute(
                "WITH RECURSIVE subtree(id) AS ("
                "  SELECT id FROM events WHERE parent_id=?"
                "  UNION ALL"
                "  SELECT e.id FROM events e JOIN subtree s ON e.parent_id = s.id"
                ") UPDATE events SET done=1 "
                "WHERE id IN (SELECT id FROM subtree) AND done=0",
                (event_id,))
            # CTE 更新的 rowcount 不可用（返回 -1），用 changes() 取
            cascaded = self._conn.execute("SELECT changes()").fetchone()[0]
        self._conn.commit()
        return cascaded

    def update_event(self, event_id: int, title: str, kind: str,
                     time: str | None, note: str = ""):
        """改标题/类型/时间/详细内容（日期、完成状态不动）。"""
        self._conn.execute(
            "UPDATE events SET title=?, kind=?, time=?, note=? WHERE id=?",
            (title, kind, time, note, event_id))
        self._conn.commit()

    def move_event(self, event_id: int, new_date: str):
        """改期：移到另一天（标题/时间/详细内容/完成状态都不动）。"""
        self._conn.execute("UPDATE events SET date=? WHERE id=?",
                           (new_date, event_id))
        self._conn.commit()

    def delete(self, event_id: int):
        """删除任务；连同其整棵子任务树一并删除。"""
        self._conn.execute(
            "WITH RECURSIVE subtree(id) AS ("
            "  SELECT id FROM events WHERE parent_id=?"
            "  UNION ALL"
            "  SELECT e.id FROM events e JOIN subtree s ON e.parent_id = s.id"
            ") DELETE FROM events WHERE id IN (SELECT id FROM subtree)",
            (event_id,))
        self._conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        self._conn.commit()

    # ---- 查询 ----
    def events_on(self, date: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM events WHERE date=? ORDER BY done, time IS NULL, time, id",
            (date,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get(self, event_id: int) -> dict | None:
        """按 id 取单条事件（列表缓存失效后从数据库取最新用）。"""
        r = self._conn.execute("SELECT * FROM events WHERE id=?",
                               (event_id,)).fetchone()
        return dict(r) if r else None

    def month_marks(self, year: int, month: int) -> dict[str, dict]:
        """当月有事项的日期 → {has_event, has_pending_ddl, overdue_ddl}，供日历绘制。"""
        prefix = f"{year:04d}-{month:02d}-%"
        rows = self._conn.execute(
            "SELECT date, kind, done FROM events WHERE date LIKE ?", (prefix,)
        ).fetchall()
        today = datetime.now().date()
        marks: dict[str, dict] = {}
        for r in rows:
            m = marks.setdefault(r["date"], {"has_event": False,
                                             "has_pending_ddl": False,
                                             "overdue_ddl": False})
            if r["kind"] == "ddl" and not r["done"]:
                m["has_pending_ddl"] = True
                d = datetime.strptime(r["date"], "%Y-%m-%d").date()
                if d < today:
                    m["overdue_ddl"] = True
            else:
                m["has_event"] = True
        return marks

    def _rows_with_roots(self) -> list[dict]:
        """全部事件，每行附带 _root_id/_root_done（顶层祖先，按树归属拆分视图）。

        只存 id/done 两个标量——存整行会自引用（root 行的 _root 是自己），
        塞进 Qt 的 UserRole  QVariant 转换会无限递归直接栈溢出。
        """
        rows = [dict(r) for r in self._conn.execute("SELECT * FROM events")]
        by_id = {r["id"]: r for r in rows}
        for r in rows:
            cur, seen = r, set()
            while cur.get("parent_id") and cur["parent_id"] in by_id \
                    and cur["parent_id"] not in seen:
                seen.add(cur["id"])
                cur = by_id[cur["parent_id"]]
            r["_root_id"] = cur["id"]
            r["_root_done"] = cur["done"]
        return rows

    # ---- 一览 ----
    def pending_overview(self, limit: int = 200) -> list[dict]:
        """待办视图 = 未完成的顶层任务 + 它们的整棵子树。

        子任务不因其自身完成而离开：只要父任务没完成，子任务（含已画线的）
        都留在这里跟在父任务下方。
        """
        rows = [r for r in self._rows_with_roots() if not r["_root_done"]]
        rows.sort(key=lambda r: (r["date"], r["time"] is None, r["time"] or "", r["id"]))
        return rows[:limit]

    def completed_overview(self, limit: int = 200) -> list[dict]:
        """已完成视图 = 已完成的顶层任务 + 它们的整棵子树（父完成时级联，
        子树全部已完成；即使有个别残留也跟随父任务在此展示）。"""
        rows = [r for r in self._rows_with_roots() if r["_root_done"]]
        rows.sort(key=lambda r: (r["date"], r["time"] is None, r["time"] or "", r["id"]),
                  reverse=True)
        return rows[:limit]

    # ---- DDL 提醒 ----
    def due_reminders(self, now: datetime | None = None) -> list[dict]:
        """到点该提醒且还没提醒过的 DDL（含已过期未完成的）。"""
        now = now or datetime.now()
        rows = self._conn.execute(
            "SELECT * FROM events WHERE kind='ddl' AND done=0 AND notified=0"
        ).fetchall()
        due = []
        for r in rows:
            ddl_dt = datetime.strptime(
                f"{r['date']} {r['time'] or f'{NO_TIME_DDL_HOUR:02d}:00'}",
                "%Y-%m-%d %H:%M",
            )
            if now >= ddl_dt - timedelta(minutes=REMIND_AHEAD_MIN):
                e = dict(r)
                e["ddl_dt"] = ddl_dt
                due.append(e)
        return due

    def mark_notified(self, event_id: int):
        self._conn.execute("UPDATE events SET notified=1 WHERE id=?", (event_id,))
        self._conn.commit()

    def close(self):
        self._conn.close()
