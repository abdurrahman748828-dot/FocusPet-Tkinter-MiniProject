# 🐾 FocusPet – Study Focus Companion

> A Python Tkinter desktop app where your study time raises a virtual pet.
> Focus, finish tasks, earn XP, and watch your pet evolve: **Egg → Chick → Buddy → Dragon**.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![GUI](https://img.shields.io/badge/GUI-Tkinter-green)
![Database](https://img.shields.io/badge/Database-SQLite-lightgrey)
![Status](https://img.shields.io/badge/Status-Completed-brightgreen)

## 📸 Screenshots

| Home (pet + timer) | Tasks (quick picks) |
|---|---|
| ![Home](screenshots/home.png) | ![Tasks](screenshots/tasks.png) |

| Stats (7-day chart) | Achievements |
|---|---|
| ![Stats](screenshots/stats.png) | ![Achievements](screenshots/achievements.png) |

## ✨ Features

- **Animated virtual pet** drawn live on a Tkinter `Canvas` (no image files). It blinks, bobs, flaps its wings while you focus, and celebrates when you finish.
- **Pomodoro focus timer** with start, pause, resume, reset and skip.
- **10 one-click Quick Picks**: Study, Running, Wake up early, Coding practice, Reading, Meditation, Assignment work, Gym workout, Drink water, Sleep on time.
- **Task manager** with priority, due date validation, overdue highlighting, and linking a task to a focus session.
- **XP and levels**: 1 XP per focus minute, +10 XP per finished task, 100 XP per level.
- **Stats dashboard** with a custom-drawn 7-day bar chart.
- **8 achievements** with unlock dates.
- **4 themes**: Daylight, Midnight, Neon, Sakura.
- **CSV export** of all focus sessions.
- **SQLite storage**: your progress is saved between runs.

## 🚀 How to run

```bash
git clone https://github.com/<your-username>/FocusPet-Tkinter-MiniProject.git
cd FocusPet-Tkinter-MiniProject
python3 focuspet.py
```

Requirements: **Python 3.8+**. No extra packages are needed (only the standard library).
On Linux, install Tkinter first: `sudo apt install python3-tk`.
A local `focuspet.db` file is created automatically on first run.

## 🧱 Project structure

```
FocusPet-Tkinter-MiniProject/
├── focuspet.py        # complete application
├── README.md
├── requirements.txt
├── .gitignore
└── screenshots/       # images used in this README
```

## 🛠️ Tech and concepts used

Python 3 · Tkinter / ttk (`Notebook`, `Treeview`, `Combobox`, `Spinbox`, `Progressbar`, `Style`) · Canvas drawing · `after()` event-loop timers (no threads) · SQLite with parameterised queries · OOP (separate classes for database, pet canvas, application) · input validation · CSV export.

## 👥 Team

| Member | Role | Main parts |
|---|---|---|
| **Name 1** | Pet and timer | `PetCanvas`, Home tab, timer logic |
| **Name 2** | Database and tasks | `Database` class, Tasks tab, Quick Picks |
| **Name 3** | Stats and UI | Stats chart, achievements, themes, settings, CSV export |

## 🎮 How XP works

| Action | Reward |
|---|---|
| Finish a focus session | +1 XP per minute |
| Finish a task | +10 XP |
| Every 100 XP | +1 level |
| Level 2 / 4 / 7 | Chick / Buddy / Dragon |

## 📄 License

Created as an academic mini-project. Free to use for learning.
