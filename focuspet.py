"""
FocusPet - Study Focus Companion
A Python Tkinter mini-project.

Study with a Pomodoro timer, finish tasks, and watch your virtual pet
evolve (Egg -> Chick -> Buddy -> Dragon). Everything is saved in SQLite.

Only the Python standard library is used (tkinter, sqlite3, csv, math...).

Team split (3 students)
-----------------------
Member 1 : PetCanvas + Focus timer      (Home tab)
Member 2 : Database layer + Task manager (Tasks tab)
Member 3 : Stats chart + Achievements + Themes + CSV export + Settings
"""

import csv
import math
import random
import sqlite3
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk

DB_FILE = "focuspet.db"

# --------------------------------------------------------------------------
# Themes
# --------------------------------------------------------------------------
THEMES = {
    "Daylight": dict(bg="#f4f6fb", card="#ffffff", fg="#1f2937", accent="#6366f1",
                     soft="#e0e7ff", pet="#fbbf24", pet2="#f59e0b", sky="#dbeafe"),
    "Midnight": dict(bg="#111827", card="#1f2937", fg="#f3f4f6", accent="#8b5cf6",
                     soft="#374151", pet="#a78bfa", pet2="#7c3aed", sky="#0f172a"),
    "Neon":     dict(bg="#0b0b14", card="#16162a", fg="#e5fff7", accent="#00f5a0",
                     soft="#26264a", pet="#00f5a0", pet2="#00c2ff", sky="#05050d"),
    "Sakura":   dict(bg="#fff1f5", card="#ffffff", fg="#4a1d2c", accent="#ec4899",
                     soft="#fce7f3", pet="#f9a8d4", pet2="#ec4899", sky="#ffe4ec"),
}

STAGES = ["Egg", "Chick", "Buddy", "Dragon"]
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}

# (icon, title, priority) shown as one-click "Quick picks" in the Tasks tab
PRESETS = [
    ("📚", "Study", "High"),
    ("🏃", "Running", "Medium"),
    ("⏰", "Wake up early", "Medium"),
    ("💻", "Coding practice", "High"),
    ("📖", "Reading", "Low"),
    ("🧘", "Meditation", "Low"),
    ("📝", "Assignment work", "High"),
    ("🏋", "Gym workout", "Medium"),
    ("💧", "Drink water", "Low"),
    ("😴", "Sleep on time", "Medium"),
]
QUOTES = [
    "Small steps every day beat big steps once.",
    "Focus now, relax later.",
    "Your pet believes in you!",
    "One more session. You've got this.",
    "Deep work builds deep skill.",
    "Progress, not perfection.",
    "Close the tabs. Open your mind.",
]


# --------------------------------------------------------------------------
# Database layer  (Member 2)
# --------------------------------------------------------------------------
class Database:
    def __init__(self, path=DB_FILE):
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS tasks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority TEXT NOT NULL,
                due TEXT,
                done INTEGER DEFAULT 0,
                created TEXT);
            CREATE TABLE IF NOT EXISTS sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                task_id INTEGER);
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS achievements(
                key TEXT PRIMARY KEY, unlocked_on TEXT);
        """)
        self.con.commit()

    # generic helpers
    def run(self, sql, args=()):
        cur = self.con.execute(sql, args)
        self.con.commit()
        return cur

    def all(self, sql, args=()):
        return self.con.execute(sql, args).fetchall()

    def one(self, sql, args=()):
        return self.con.execute(sql, args).fetchone()

    # settings
    def get(self, key, default):
        r = self.one("SELECT value FROM settings WHERE key=?", (key,))
        return r["value"] if r else default

    def set(self, key, value):
        self.run("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, str(value)))

    # tasks
    def add_task(self, title, priority, due):
        self.run("INSERT INTO tasks(title,priority,due,created) VALUES(?,?,?,?)",
                 (title, priority, due or None, datetime.now().isoformat(timespec="seconds")))

    def tasks(self):
        rows = self.all("SELECT * FROM tasks")
        return sorted(rows, key=lambda r: (r["done"], PRIORITY_ORDER[r["priority"]],
                                           r["due"] or "9999"))

    def toggle_task(self, tid):
        self.run("UPDATE tasks SET done = 1 - done WHERE id=?", (tid,))

    def delete_task(self, tid):
        self.run("DELETE FROM tasks WHERE id=?", (tid,))

    # sessions
    def add_session(self, minutes, task_id=None):
        self.run("INSERT INTO sessions(day,minutes,task_id) VALUES(?,?,?)",
                 (date.today().isoformat(), minutes, task_id))

    def minutes_on(self, day):
        r = self.one("SELECT COALESCE(SUM(minutes),0) m FROM sessions WHERE day=?", (day,))
        return r["m"]

    def stats(self):
        total = self.one("SELECT COALESCE(SUM(minutes),0) m, COUNT(*) c FROM sessions")
        done = self.one("SELECT COUNT(*) c FROM tasks WHERE done=1")["c"]
        days = {r["day"] for r in self.all("SELECT DISTINCT day FROM sessions")}
        streak, d = 0, date.today()
        if d.isoformat() not in days:
            d -= timedelta(days=1)
        while d.isoformat() in days:
            streak += 1
            d -= timedelta(days=1)
        xp = total["m"] + done * 10
        return dict(minutes=total["m"], sessions=total["c"], tasks=done, streak=streak,
                    xp=xp, level=xp // 100 + 1, today=self.minutes_on(date.today().isoformat()))

    # achievements
    def unlocked(self):
        return {r["key"]: r["unlocked_on"] for r in self.all("SELECT * FROM achievements")}

    def unlock(self, key):
        self.run("INSERT OR IGNORE INTO achievements VALUES(?,?)", (key, date.today().isoformat()))

    def reset(self):
        for t in ("tasks", "sessions", "achievements"):
            self.run(f"DELETE FROM {t}")


ACHIEVEMENTS = [
    ("first",   "First Spark",    "Finish your first focus session",   lambda s: s["sessions"] >= 1),
    ("hour",    "Hour Hero",      "Focus for 60 minutes in total",     lambda s: s["minutes"] >= 60),
    ("five",    "High Five",      "Complete 5 focus sessions",         lambda s: s["sessions"] >= 5),
    ("tasker",  "Task Slayer",    "Complete 5 tasks",                  lambda s: s["tasks"] >= 5),
    ("streak3", "On Fire",        "Reach a 3-day streak",              lambda s: s["streak"] >= 3),
    ("marathon", "Marathoner",    "Focus 120 minutes in one day",      lambda s: s["today"] >= 120),
    ("lvl4",    "Pet Whisperer",  "Reach level 4 (Buddy stage)",       lambda s: s["level"] >= 4),
    ("lvl7",    "Dragon Master",  "Reach level 7 (Dragon stage)",      lambda s: s["level"] >= 7),
]


# --------------------------------------------------------------------------
# Pet drawing  (Member 1)
# --------------------------------------------------------------------------
def stage_for(level):
    if level >= 7:
        return 3
    if level >= 4:
        return 2
    if level >= 2:
        return 1
    return 0


class PetCanvas(tk.Canvas):
    W, H = 340, 270

    def __init__(self, master, theme):
        super().__init__(master, width=self.W, height=self.H, highlightthickness=0)
        self.theme = theme
        self.stage = 0
        self.mood = "happy"
        self.t = 0
        self.focusing = False
        self.particles = []
        self.cheer = 0
        self.animate()

    def set_state(self, stage, mood):
        self.stage, self.mood = stage, mood

    def celebrate(self):
        self.cheer = 60
        for _ in range(25):
            self.particles.append([random.randint(80, 260), 200, random.uniform(-1.5, 1.5),
                                   random.uniform(-4, -1.5), random.choice("★✦✧♥")])

    def animate(self):
        self.t += 1
        self.draw()
        self.after(50, self.animate)

    def eyes(self, x, y, gap, size, blink):
        for sx in (-gap, gap):
            if blink:
                self.create_line(x + sx - size, y, x + sx + size, y, width=3, fill="#222")
            else:
                self.create_oval(x + sx - size, y - size, x + sx + size, y + size,
                                 fill="white", outline="#222", width=2)
                self.create_oval(x + sx - size / 2, y - size / 2 + 1, x + sx + size / 2,
                                 y + size / 2 + 1, fill="#222")

    def mouth(self, x, y):
        if self.cheer > 0:
            self.create_oval(x - 10, y - 4, x + 10, y + 14, fill="#7f1d1d", outline="#222", width=2)
        elif self.mood == "happy":
            self.create_arc(x - 14, y - 10, x + 14, y + 10, start=200, extent=140,
                            style="arc", width=3, outline="#222")
        elif self.mood == "ok":
            self.create_line(x - 9, y + 2, x + 9, y + 2, width=3, fill="#222")
        else:
            self.create_arc(x - 14, y + 2, x + 14, y + 22, start=20, extent=140,
                            style="arc", width=3, outline="#222")

    def draw(self):
        th = self.theme
        self.delete("all")
        self.configure(bg=th["sky"])
        # ground + sun/moon
        self.create_oval(-40, 215, self.W + 40, 330, fill=th["soft"], outline="")
        self.create_oval(270, 20, 310, 60, fill=th["pet"], outline="")
        # shadow
        self.create_oval(100, 205, 240, 228, fill="#00000022" if False else th["card"], outline="")

        bob = math.sin(self.t / 8) * (7 if self.cheer else 4)
        if self.cheer:
            bob -= abs(math.sin(self.t / 3)) * 14
            self.cheer -= 1
        blink = (self.t % 70) < 3
        cx, base = self.W / 2, 205 + 0
        p1, p2 = th["pet"], th["pet2"]

        if self.stage == 0:      # EGG
            wob = math.sin(self.t / 6) * 4 if self.focusing else math.sin(self.t / 15) * 2
            self.create_oval(cx - 55 + wob, base - 125 + bob, cx + 55 + wob, base + bob,
                             fill="#fffaf0", outline="#d6c9b0", width=3)
            for dx, dy, r in ((-32, -100, 8), (30, -98, 6), (-37, -22, 9), (34, -26, 7), (0, -113, 5)):
                self.create_oval(cx + dx - r + wob, base + dy - r + bob, cx + dx + r + wob,
                                 base + dy + r + bob, fill=p1, outline="")
            self.eyes(cx + wob, base - 62 + bob, 17, 7, blink)
            self.mouth(cx + wob, base - 38 + bob)

        elif self.stage == 1:    # CHICK
            self.create_oval(cx - 55, base - 95 + bob, cx + 55, base + bob, fill=p1, outline=p2, width=3)
            self.create_oval(cx - 42, base - 150 + bob, cx + 42, base - 70 + bob, fill=p1, outline=p2, width=3)
            self.create_polygon(cx - 8, base - 112 + bob, cx + 8, base - 112 + bob, cx, base - 98 + bob,
                                fill="#f97316", outline="#c2410c")
            self.create_polygon(cx - 5, base - 155 + bob, cx, base - 175 + bob, cx + 5, base - 155 + bob,
                                fill=p2, outline="")
            self.eyes(cx, base - 125 + bob, 18, 7, blink)
            self.mouth(cx, base - 90 + bob + 14)
            for sx in (-20, 20):
                self.create_line(cx + sx, base + bob, cx + sx, base + 12, width=4, fill="#f97316")
            wing = math.sin(self.t / 4) * 8 if self.focusing or self.cheer else 0
            self.create_oval(cx - 70, base - 70 + bob + wing, cx - 42, base - 30 + bob + wing, fill=p2, outline="")
            self.create_oval(cx + 42, base - 70 + bob - wing, cx + 70, base - 30 + bob - wing, fill=p2, outline="")

        elif self.stage == 2:    # BUDDY
            for sx in (-1, 1):
                self.create_polygon(cx + sx * 20, base - 140 + bob, cx + sx * 48, base - 185 + bob,
                                    cx + sx * 55, base - 130 + bob, fill=p2, outline="")
            self.create_oval(cx - 68, base - 150 + bob, cx + 68, base + bob, fill=p1, outline=p2, width=4)
            self.create_oval(cx - 38, base - 70 + bob, cx + 38, base - 8 + bob, fill="#ffffffaa" if False else th["card"], outline="")
            self.eyes(cx, base - 100 + bob, 24, 9, blink)
            self.create_oval(cx - 56, base - 82 + bob, cx - 38, base - 70 + bob, fill="#fda4af", outline="")
            self.create_oval(cx + 38, base - 82 + bob, cx + 56, base - 70 + bob, fill="#fda4af", outline="")
            self.mouth(cx, base - 68 + bob)
            for sx in (-30, 30):
                self.create_oval(cx + sx - 14, base - 6 + bob, cx + sx + 14, base + 12, fill=p2, outline="")

        else:                    # DRAGON
            flap = math.sin(self.t / 5) * (22 if self.focusing or self.cheer else 8)
            for sx in (-1, 1):   # wings
                self.create_polygon(cx + sx * 40, base - 110 + bob, cx + sx * 135, base - 175 + bob + flap,
                                    cx + sx * 120, base - 100 + bob, cx + sx * 95, base - 90 + bob + flap / 2,
                                    cx + sx * 70, base - 60 + bob, fill=p2, outline=th["fg"], width=2)
            tail = math.sin(self.t / 9) * 12
            self.create_polygon(cx + 50, base - 40 + bob, cx + 125, base - 20 + bob + tail,
                                cx + 150, base - 55 + bob + tail, cx + 120, base - 5 + bob + tail,
                                cx + 55, base + bob, fill=p1, outline=p2, width=3)
            self.create_oval(cx - 62, base - 145 + bob, cx + 62, base + bob, fill=p1, outline=p2, width=4)
            self.create_oval(cx - 34, base - 85 + bob, cx + 34, base - 8 + bob, fill="#fff7d6", outline="")
            for i in range(-2, 3):   # back spikes
                self.create_polygon(cx + i * 22 - 8, base - 140 + bob + abs(i) * 8, cx + i * 22, base - 168 + bob + abs(i) * 8,
                                    cx + i * 22 + 8, base - 140 + bob + abs(i) * 8, fill=p2, outline="")
            for sx in (-1, 1):   # horns
                self.create_polygon(cx + sx * 28, base - 138 + bob, cx + sx * 38, base - 185 + bob,
                                    cx + sx * 12, base - 145 + bob, fill="#f8fafc", outline="#94a3b8")
            self.eyes(cx, base - 105 + bob, 24, 9, blink)
            for sx in (-6, 6):
                self.create_oval(cx + sx - 2, base - 82 + bob, cx + sx + 2, base - 78 + bob, fill="#222", outline="")
            self.mouth(cx, base - 62 + bob)

        # particles (stars / hearts)
        if self.focusing and self.t % 12 == 0:
            self.particles.append([random.randint(90, 250), 190, random.uniform(-.5, .5),
                                   random.uniform(-2, -1), "✦"])
        for p in self.particles[:]:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.04
            self.create_text(p[0], p[1], text=p[4], fill=th["accent"], font=("Segoe UI Symbol", 14))
            if p[1] < 10 or p[1] > 260:
                self.particles.remove(p)


# --------------------------------------------------------------------------
# Main application
# --------------------------------------------------------------------------
class FocusPetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FocusPet - Study Focus Companion")
        self.geometry("920x640")
        self.minsize(860, 600)
        self.db = Database()
        self.theme_name = self.db.get("theme", "Daylight")
        self.pet_name = self.db.get("pet_name", "Pixel")
        self.focus_min = int(self.db.get("focus_min", 25))
        self.break_min = int(self.db.get("break_min", 5))

        self.mode = "Focus"
        self.remaining = self.focus_min * 60
        self.running = False
        self.job = None
        self.session_task_id = None

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.build_ui()
        self.apply_theme()
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bring_to_front()

    def bring_to_front(self):
        """On macOS the window can open behind other apps; force it forward."""
        self.update_idletasks()
        self.lift()
        self.attributes("-topmost", True)
        self.after(600, lambda: self.attributes("-topmost", False))
        self.focus_force()

    # ---------------------------------------------------------- UI building
    def build_ui(self):
        self.header = tk.Label(self, text="", font=("Segoe UI", 18, "bold"), anchor="w", padx=18, pady=8)
        self.header.pack(fill="x")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.tab_home = ttk.Frame(self.nb)
        self.tab_tasks = ttk.Frame(self.nb)
        self.tab_stats = ttk.Frame(self.nb)
        self.tab_ach = ttk.Frame(self.nb)
        self.tab_set = ttk.Frame(self.nb)
        for tab, name in ((self.tab_home, "  Home  "), (self.tab_tasks, "  Tasks  "),
                          (self.tab_stats, "  Stats  "), (self.tab_ach, "  Achievements  "),
                          (self.tab_set, "  Settings  ")):
            self.nb.add(tab, text=name)
        self.status = tk.Label(self, text="", anchor="w", padx=14, font=("Segoe UI", 9))
        self.status.pack(fill="x", side="bottom", pady=(0, 6), before=self.nb)
        self.build_home()
        self.build_tasks()
        self.build_stats()
        self.build_ach()
        self.build_settings()

    # ------------------------------ Home (Member 1)
    def build_home(self):
        f = self.tab_home
        left = ttk.Frame(f)
        left.pack(side="left", padx=20, pady=15)
        self.pet = PetCanvas(left, THEMES[self.theme_name])
        self.pet.pack()
        self.pet_label = ttk.Label(left, font=("Segoe UI", 13, "bold"))
        self.pet_label.pack(pady=(8, 2))
        self.xp_bar = ttk.Progressbar(left, length=300, maximum=100)
        self.xp_bar.pack()
        self.xp_label = ttk.Label(left, font=("Segoe UI", 9))
        self.xp_label.pack(pady=2)
        self.quote = ttk.Label(left, font=("Segoe UI", 10, "italic"), wraplength=320, justify="center")
        self.quote.pack(pady=8)

        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=20, pady=15)
        self.mode_label = ttk.Label(right, font=("Segoe UI", 14, "bold"))
        self.mode_label.pack(pady=(10, 0))
        self.time_label = ttk.Label(right, text="25:00", font=("Consolas", 64, "bold"))
        self.time_label.pack(pady=4)
        self.ring = ttk.Progressbar(right, length=300, maximum=100)
        self.ring.pack(pady=4)
        btns = ttk.Frame(right)
        btns.pack(pady=12)
        self.start_btn = ttk.Button(btns, text="Start", width=10, command=self.toggle_timer)
        self.start_btn.grid(row=0, column=0, padx=4)
        ttk.Button(btns, text="Reset", width=10, command=self.reset_timer).grid(row=0, column=1, padx=4)
        ttk.Button(btns, text="Skip", width=10, command=self.finish_phase).grid(row=0, column=2, padx=4)

        ttk.Label(right, text="Focusing on:").pack(pady=(14, 2))
        self.task_combo = ttk.Combobox(right, state="readonly", width=34)
        self.task_combo.pack()
        self.today_label = ttk.Label(right, font=("Segoe UI", 11))
        self.today_label.pack(pady=18)

    # ------------------------------ Tasks (Member 2)
    def build_tasks(self):
        f = self.tab_tasks
        quick = ttk.LabelFrame(f, text=" Quick picks - click to add and focus ")
        quick.pack(fill="x", padx=14, pady=(12, 0))
        for i, (icon, title, prio) in enumerate(PRESETS):
            ttk.Button(quick, text=f"{icon}  {title}",
                       command=lambda t=title, p=prio: self.add_preset(t, p)
                       ).grid(row=i // 5, column=i % 5, padx=5, pady=5, sticky="ew")
            quick.columnconfigure(i % 5, weight=1)
        form = ttk.Frame(f)
        form.pack(fill="x", padx=14, pady=12)
        ttk.Label(form, text="Task").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Priority").grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(form, text="Due (YYYY-MM-DD)").grid(row=0, column=2, sticky="w")
        self.t_title = ttk.Entry(form, width=40)
        self.t_title.grid(row=1, column=0, pady=2)
        self.t_prio = ttk.Combobox(form, values=list(PRIORITY_ORDER), state="readonly", width=10)
        self.t_prio.set("Medium")
        self.t_prio.grid(row=1, column=1, padx=8)
        self.t_due = ttk.Entry(form, width=16)
        self.t_due.grid(row=1, column=2)
        ttk.Button(form, text="Add Task", command=self.add_task).grid(row=1, column=3, padx=10)
        self.t_title.bind("<Return>", lambda e: self.add_task())

        cols = ("title", "priority", "due", "status")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=8)
        for c, w in zip(cols, (380, 90, 120, 100)):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w, anchor="w" if c == "title" else "center")
        self.tree.pack(fill="both", expand=True, padx=14)
        self.tree.tag_configure("done", foreground="#9ca3af")
        self.tree.tag_configure("late", foreground="#ef4444")
        self.tree.tag_configure("High", foreground="#dc2626")
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=14, pady=10)
        ttk.Button(bar, text="Toggle Done (+10 XP)", command=self.toggle_task).pack(side="left")
        ttk.Button(bar, text="Delete", command=self.delete_task).pack(side="left", padx=8)
        ttk.Button(bar, text="Focus on this", command=self.focus_selected).pack(side="left")
        self.task_info = ttk.Label(bar)
        self.task_info.pack(side="right")

    # ------------------------------ Stats (Member 3)
    def build_stats(self):
        f = self.tab_stats
        self.cards = ttk.Frame(f)
        self.cards.pack(fill="x", padx=14, pady=12)
        self.card_labels = {}
        for i, (k, name) in enumerate((("minutes", "Total minutes"), ("sessions", "Sessions"),
                                       ("tasks", "Tasks done"), ("streak", "Day streak"),
                                       ("level", "Level"))):
            box = tk.Frame(self.cards, padx=14, pady=8)
            box.grid(row=0, column=i, padx=6, sticky="nsew")
            self.cards.columnconfigure(i, weight=1)
            v = tk.Label(box, text="0", font=("Segoe UI", 22, "bold"))
            v.pack()
            n = tk.Label(box, text=name, font=("Segoe UI", 9))
            n.pack()
            self.card_labels[k] = (box, v, n)
        self.chart = tk.Canvas(f, height=300, highlightthickness=0)
        self.chart.pack(fill="both", expand=True, padx=14, pady=6)
        self.chart.bind("<Configure>", lambda e: self.draw_chart())
        ttk.Button(f, text="Export sessions to CSV", command=self.export_csv).pack(pady=8)

    # ------------------------------ Achievements (Member 3)
    def build_ach(self):
        self.ach_wrap = ttk.Frame(self.tab_ach)
        self.ach_wrap.pack(fill="both", expand=True, padx=14, pady=14)

    # ------------------------------ Settings (Member 3)
    def build_settings(self):
        f = self.tab_set
        g = ttk.Frame(f)
        g.pack(padx=30, pady=24, anchor="n")
        ttk.Label(g, text="Theme").grid(row=0, column=0, sticky="w", pady=6)
        self.s_theme = ttk.Combobox(g, values=list(THEMES), state="readonly", width=16)
        self.s_theme.set(self.theme_name)
        self.s_theme.grid(row=0, column=1, padx=10)
        ttk.Label(g, text="Pet name").grid(row=1, column=0, sticky="w", pady=6)
        self.s_name = ttk.Entry(g, width=18)
        self.s_name.insert(0, self.pet_name)
        self.s_name.grid(row=1, column=1, padx=10)
        ttk.Label(g, text="Focus minutes").grid(row=2, column=0, sticky="w", pady=6)
        self.s_focus = ttk.Spinbox(g, from_=1, to=120, width=8)
        self.s_focus.set(self.focus_min)
        self.s_focus.grid(row=2, column=1, sticky="w", padx=10)
        ttk.Label(g, text="Break minutes").grid(row=3, column=0, sticky="w", pady=6)
        self.s_break = ttk.Spinbox(g, from_=1, to=60, width=8)
        self.s_break.set(self.break_min)
        self.s_break.grid(row=3, column=1, sticky="w", padx=10)
        ttk.Button(g, text="Save Settings", command=self.save_settings).grid(row=4, column=0, columnspan=2, pady=14)
        ttk.Button(g, text="Reset all progress", command=self.reset_all).grid(row=5, column=0, columnspan=2)
        ttk.Label(g, justify="left", text=(
            "\nHow XP works\n"
            "  • 1 XP per focus minute completed\n"
            "  • +10 XP for every finished task\n"
            "  • 100 XP = 1 level\n"
            "  • Level 2: Chick | Level 4: Buddy | Level 7: Dragon")).grid(row=6, column=0, columnspan=2, pady=10)

    # --------------------------------------------------------------- theming
    def apply_theme(self):
        th = THEMES[self.theme_name]
        self.configure(bg=th["bg"])
        s = self.style
        s.configure(".", background=th["bg"], foreground=th["fg"], fieldbackground=th["card"])
        s.configure("TFrame", background=th["bg"])
        s.configure("TLabel", background=th["bg"], foreground=th["fg"])
        s.configure("TButton", background=th["accent"], foreground="#ffffff", padding=7, borderwidth=0)
        s.map("TButton", background=[("active", th["pet2"])])
        s.configure("TNotebook", background=th["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", background=th["soft"], foreground=th["fg"], padding=(10, 6))
        s.map("TNotebook.Tab", background=[("selected", th["accent"])], foreground=[("selected", "#ffffff")])
        s.configure("Treeview", background=th["card"], foreground=th["fg"], fieldbackground=th["card"], rowheight=28)
        s.configure("Treeview.Heading", background=th["accent"], foreground="#ffffff")
        s.configure("TProgressbar", background=th["accent"], troughcolor=th["soft"])
        s.configure("TCombobox", fieldbackground=th["card"], foreground=th["fg"],
                    background=th["soft"], arrowcolor=th["fg"], selectbackground=th["card"],
                    selectforeground=th["fg"])
        s.map("TCombobox",
              fieldbackground=[("readonly", th["card"])],
              foreground=[("readonly", th["fg"])],
              background=[("readonly", th["soft"])],
              selectbackground=[("readonly", th["card"])],
              selectforeground=[("readonly", th["fg"])])
        s.configure("TEntry", fieldbackground=th["card"], foreground=th["fg"], insertcolor=th["fg"])
        s.configure("TSpinbox", fieldbackground=th["card"], foreground=th["fg"],
                    background=th["soft"], arrowcolor=th["fg"], insertcolor=th["fg"])
        s.configure("TLabelframe", background=th["bg"])
        s.configure("TLabelframe.Label", background=th["bg"], foreground=th["fg"])
        self.option_add("*TCombobox*Listbox.background", th["card"])
        self.option_add("*TCombobox*Listbox.foreground", th["fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", th["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.header.configure(bg=th["bg"], fg=th["accent"])
        self.status.configure(bg=th["bg"], fg=th["fg"])
        self.pet.theme = th
        self.chart.configure(bg=th["card"])
        for box, v, n in self.card_labels.values():
            box.configure(bg=th["card"])
            v.configure(bg=th["card"], fg=th["accent"])
            n.configure(bg=th["card"], fg=th["fg"])
        self.draw_chart()
        self.build_achievements_view()

    # ------------------------------------------------------------ refreshing
    def refresh_all(self):
        s = self.db.stats()
        stage = stage_for(s["level"])
        mood = "happy" if s["today"] >= 25 else ("ok" if s["streak"] > 0 else "sad")
        self.pet.set_state(stage, mood)
        self.header.configure(text=f"🐾 FocusPet  —  {self.pet_name} the {STAGES[stage]}")
        self.pet_label.configure(text=f"{self.pet_name}  •  Level {s['level']}  •  {STAGES[stage]}")
        self.xp_bar["value"] = s["xp"] % 100
        self.xp_label.configure(text=f"{s['xp'] % 100}/100 XP to next level   (total {s['xp']} XP)")
        self.today_label.configure(text=f"Today: {s['today']} min focused  |  Streak: {s['streak']} day(s)")
        self.quote.configure(text=random.choice(QUOTES))
        mood_text = {"happy": "feeling great", "ok": "a bit sleepy", "sad": "missing you"}[mood]
        self.status.configure(text=f"{self.pet_name} is {mood_text}.  Keep the streak alive!")
        self.refresh_tasks()
        self.refresh_stats(s)
        self.draw_chart()
        self.build_achievements_view()

    def refresh_tasks(self):
        self.tree.delete(*self.tree.get_children())
        today = date.today().isoformat()
        open_titles = []
        self.open_ids = []
        for t in self.db.tasks():
            late = t["due"] and t["due"] < today and not t["done"]
            status = "✔ Done" if t["done"] else ("⚠ Overdue" if late else "Pending")
            tags = ("done",) if t["done"] else (("late",) if late else (t["priority"],))
            self.tree.insert("", "end", iid=str(t["id"]), tags=tags,
                             values=(t["title"], t["priority"], t["due"] or "-", status))
            if not t["done"]:
                open_titles.append(t["title"])
                self.open_ids.append(t["id"])
        self.task_combo["values"] = ["(No specific task)"] + open_titles
        if self.task_combo.current() < 0 or self.task_combo.current() >= len(open_titles) + 1:
            self.task_combo.current(0)
        total = len(self.db.tasks())
        self.task_info.configure(text=f"{len(open_titles)} pending / {total} total")

    def refresh_stats(self, s):
        for k in ("minutes", "sessions", "tasks", "streak", "level"):
            self.card_labels[k][1].configure(text=str(s[k]))

    def draw_chart(self):
        c = self.chart
        th = THEMES[self.theme_name]
        c.delete("all")
        w, h = max(c.winfo_width(), 400), max(c.winfo_height(), 200)
        days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
        vals = [self.db.minutes_on(d.isoformat()) for d in days]
        top = max(max(vals), 30)
        c.create_text(w / 2, 18, text="Focus minutes — last 7 days", fill=th["fg"], font=("Segoe UI", 12, "bold"))
        left, right, bottom, ceil = 50, w - 30, h - 40, 45
        for i in range(5):
            y = bottom - (bottom - ceil) * i / 4
            c.create_line(left, y, right, y, fill=th["soft"])
            c.create_text(left - 8, y, text=str(int(top * i / 4)), fill=th["fg"], anchor="e", font=("Segoe UI", 8))
        slot = (right - left) / 7
        for i, (d, v) in enumerate(zip(days, vals)):
            x0 = left + i * slot + slot * 0.2
            x1 = left + (i + 1) * slot - slot * 0.2
            y = bottom - (bottom - ceil) * v / top
            c.create_rectangle(x0, y, x1, bottom, fill=th["accent"] if d != date.today() else th["pet2"], outline="")
            if v:
                c.create_text((x0 + x1) / 2, y - 10, text=str(v), fill=th["fg"], font=("Segoe UI", 9, "bold"))
            c.create_text((x0 + x1) / 2, bottom + 16, text=d.strftime("%a"), fill=th["fg"], font=("Segoe UI", 9))

    def build_achievements_view(self):
        for w in self.ach_wrap.winfo_children():
            w.destroy()
        th = THEMES[self.theme_name]
        got = self.db.unlocked()
        for i, (key, title, desc, _) in enumerate(ACHIEVEMENTS):
            on = key in got
            card = tk.Frame(self.ach_wrap, bg=th["card"], padx=12, pady=10,
                            highlightbackground=th["accent"] if on else th["soft"], highlightthickness=2)
            card.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")
            self.ach_wrap.columnconfigure(i % 2, weight=1)
            tk.Label(card, text=("🏆 " if on else "🔒 ") + title, bg=th["card"],
                     fg=th["accent"] if on else th["fg"], font=("Segoe UI", 12, "bold")).pack(anchor="w")
            tk.Label(card, text=desc, bg=th["card"], fg=th["fg"], font=("Segoe UI", 9)).pack(anchor="w")
            tk.Label(card, text=f"Unlocked {got[key]}" if on else "Locked", bg=th["card"],
                     fg=th["fg"], font=("Segoe UI", 8, "italic")).pack(anchor="w")

    # -------------------------------------------------------------- timer
    def toggle_timer(self):
        if self.running:
            self.running = False
            self.pet.focusing = False
            self.start_btn.configure(text="Resume")
            if self.job:
                self.after_cancel(self.job)
        else:
            if self.mode == "Focus" and self.remaining == self.focus_min * 60:
                idx = self.task_combo.current()
                self.session_task_id = self.open_ids[idx - 1] if idx > 0 else None
            self.running = True
            self.pet.focusing = self.mode == "Focus"
            self.start_btn.configure(text="Pause")
            self.tick()

    def tick(self):
        if not self.running:
            return
        self.remaining -= 1
        self.update_clock()
        if self.remaining <= 0:
            self.finish_phase(completed=True)
            return
        self.job = self.after(1000, self.tick)

    def update_clock(self):
        m, s = divmod(max(self.remaining, 0), 60)
        self.time_label.configure(text=f"{m:02d}:{s:02d}")
        total = (self.focus_min if self.mode == "Focus" else self.break_min) * 60
        self.ring["value"] = 100 * (1 - self.remaining / total)
        self.mode_label.configure(text=("🎯 Focus time" if self.mode == "Focus" else "☕ Break time"))
        self.title(f"{self.time_label.cget('text')} - FocusPet")

    def reset_timer(self):
        self.stop_timer()
        self.mode = "Focus"
        self.remaining = self.focus_min * 60
        self.update_clock()
        self.title("FocusPet - Study Focus Companion")

    def stop_timer(self):
        self.running = False
        self.pet.focusing = False
        if self.job:
            self.after_cancel(self.job)
        self.start_btn.configure(text="Start")

    def finish_phase(self, completed=False):
        was_focus = self.mode == "Focus"
        self.stop_timer()
        if was_focus and completed:
            before = self.db.stats()
            self.db.add_session(self.focus_min, self.session_task_id)
            self.pet.celebrate()
            self.bell()
            new = self.check_achievements()
            after = self.db.stats()
            msg = f"Session complete! +{self.focus_min} XP"
            if after["level"] > before["level"]:
                msg += f"\n\n🎉 {self.pet_name} reached level {after['level']}!"
                if stage_for(after["level"]) > stage_for(before["level"]):
                    msg += f"\n{self.pet_name} evolved into a {STAGES[stage_for(after['level'])]}!"
            if new:
                msg += "\n\nNew achievement: " + ", ".join(new)
            self.refresh_all()
            messagebox.showinfo("Great job!", msg)
        self.mode = "Break" if was_focus else "Focus"
        self.remaining = (self.break_min if self.mode == "Break" else self.focus_min) * 60
        self.update_clock()
        self.title("FocusPet - Study Focus Companion")

    def check_achievements(self):
        s, got, new = self.db.stats(), self.db.unlocked(), []
        for key, title, _, test in ACHIEVEMENTS:
            if key not in got and test(s):
                self.db.unlock(key)
                new.append(title)
        return new

    # -------------------------------------------------------------- tasks
    def add_task(self):
        title = self.t_title.get().strip()
        due = self.t_due.get().strip()
        if not title:
            messagebox.showwarning("Missing title", "Please type a task title.")
            return
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Bad date", "Use the format YYYY-MM-DD (e.g. 2026-11-10).")
                return
        self.db.add_task(title, self.t_prio.get(), due)
        self.t_title.delete(0, "end")
        self.t_due.delete(0, "end")
        self.refresh_all()

    def add_preset(self, title, priority):
        row = self.db.one("SELECT id FROM tasks WHERE title=? AND done=0", (title,))
        if row is None:
            self.db.add_task(title, priority, "")
            row = self.db.one("SELECT id FROM tasks WHERE title=? AND done=0", (title,))
        self.refresh_all()
        if row["id"] in self.open_ids:
            self.task_combo.current(self.open_ids.index(row["id"]) + 1)
        self.status.configure(text=f"Ready to focus on: {title}. Go to the Home tab and press Start.")

    def selected_task(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a task", "Click a task in the list first.")
            return None
        return int(sel[0])

    def toggle_task(self):
        tid = self.selected_task()
        if tid is None:
            return
        self.db.toggle_task(tid)
        self.pet.celebrate()
        self.check_achievements()
        self.refresh_all()

    def delete_task(self):
        tid = self.selected_task()
        if tid is not None and messagebox.askyesno("Delete", "Delete this task?"):
            self.db.delete_task(tid)
            self.refresh_all()

    def focus_selected(self):
        tid = self.selected_task()
        if tid is None or tid not in self.open_ids:
            return
        self.task_combo.current(self.open_ids.index(tid) + 1)
        self.nb.select(self.tab_home)

    # ------------------------------------------------- settings / export
    def save_settings(self):
        try:
            fm, bm = int(self.s_focus.get()), int(self.s_break.get())
            if not (1 <= fm <= 120 and 1 <= bm <= 60):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid", "Focus must be 1-120 and break 1-60 minutes.")
            return
        self.theme_name = self.s_theme.get()
        self.pet_name = self.s_name.get().strip() or "Pixel"
        self.focus_min, self.break_min = fm, bm
        for k, v in (("theme", self.theme_name), ("pet_name", self.pet_name),
                     ("focus_min", fm), ("break_min", bm)):
            self.db.set(k, v)
        self.reset_timer()
        self.apply_theme()
        self.refresh_all()
        messagebox.showinfo("Saved", "Settings saved.")

    def reset_all(self):
        if messagebox.askyesno("Reset", "Delete ALL tasks, sessions and achievements?"):
            self.db.reset()
            self.refresh_all()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="focus_sessions.csv",
                                            filetypes=[("CSV file", "*.csv")])
        if not path:
            return
        rows = self.db.all("""SELECT s.day, s.minutes, COALESCE(t.title,'-') task
                              FROM sessions s LEFT JOIN tasks t ON t.id=s.task_id ORDER BY s.day""")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Date", "Minutes", "Task"])
            for r in rows:
                w.writerow([r["day"], r["minutes"], r["task"]])
        messagebox.showinfo("Exported", f"Saved {len(rows)} sessions to:\n{path}")

    def on_close(self):
        if self.running and not messagebox.askyesno("Quit", "A session is running. Quit anyway?"):
            return
        self.db.con.close()
        self.destroy()


if __name__ == "__main__":
    FocusPetApp().mainloop()
