# ZenFlow

**ZenFlow** is a beautiful CLI productivity tool that combines task management, habit tracking, focus sessions, and gamification to help you achieve your goals and build better habits.

---

## ✨ Features

### 📋 Task Management
- Create, list, complete, update, and delete tasks
- Priority levels: LOW, MEDIUM, HIGH
- Due date tracking
- Status management: TODO, IN_PROGRESS, DONE
- Earn XP for completing tasks (10-50 XP based on priority)

### 🎯 Habit Tracking
- Create daily or weekly habits
- Track completions and build streaks
- Visual calendar view (30-day history)
- Milestone rewards (7-day, 30-day, 100-day streaks)
- Streak statistics and progress tracking

### 🍅 Focus Sessions (Pomodoro)
- Customizable focus timer (default 25 minutes)
- Live countdown display
- Session history tracking
- Earn XP for completed sessions (15 XP per session)

### 🎮 Gamification System
- **XP System**: Earn points for completing tasks, habits, and focus sessions
- **Levels**: Progress through levels (1000 XP per level)
- **Achievements**: Unlock 12+ achievements with bonus XP
- **Profile**: Track your stats and progress
- **Leaderboard**: Personal records and milestones

### 📊 Statistics & Analytics
- Daily, weekly, and monthly productivity reports
- Task completion trends
- Habit streak visualization
- Focus time tracking
- ASCII charts for terminal display

### 🤖 AI Insights (Optional)
- Productivity pattern analysis
- Personalized recommendations
- Optimal work time predictions
- Powered by OpenAI GPT-4

### 💾 Data Export
- Export to CSV, JSON, or TXT
- Backup all data or specific categories
- Date range filtering

---

## 🚀 Installation

### Prerequisites
- Python 3.11 or higher
- pip package manager

### Install from Source

```bash
# Clone or download the repository
cd zenflow

# Install in development mode
pip install -e .

# Or install dependencies manually
pip install -r requirements.txt
```

### Verify Installation

```bash
zenflow --version
zenflow --help
```

---

## 🏁 Quick Start

### 1. Initialize Your Profile

```bash
zenflow init
```

This creates your database and user profile. You'll be prompted for:
- Username
- Email

### 2. Create Your First Task

```bash
zenflow task add "Complete project documentation" --priority HIGH --due 2026-01-30
```

### 3. Track a Habit

```bash
zenflow habit add "Morning exercise" --frequency DAILY
zenflow habit track 1
```

### 4. Start a Focus Session

```bash
zenflow focus start --duration 25
```

### 5. Check Your Profile

```bash
zenflow profile
```

---

## 📖 Command Reference

### Global Commands

#### `zenflow --version`
Display ZenFlow version

#### `zenflow --help`
Display help information

### Initialization

#### `zenflow init`
Initialize user profile and database

**Options:**
- `--username`: Your username (prompted if not provided)
- `--email`: Your email address (prompted if not provided)

**Example:**
```bash
zenflow init --username john_doe --email john@example.com
```

---

### Task Management

#### `zenflow task add TITLE`
Create a new task

**Arguments:**
- `TITLE`: Task title (required)

**Options:**
- `--description, -d`: Task description
- `--priority, -p`: Priority level (LOW, MEDIUM, HIGH) - default: MEDIUM
- `--due`: Due date in YYYY-MM-DD format

**Examples:**
```bash
zenflow task add "Write documentation"
zenflow task add "Review PR" --priority HIGH --due 2026-01-25
zenflow task add "Refactor code" -p MEDIUM -d "Clean up authentication module"
```

#### `zenflow task list`
List tasks with optional filtering

**Options:**
- `--status, -s`: Filter by status (TODO, IN_PROGRESS, DONE)
- `--priority, -p`: Filter by priority (LOW, MEDIUM, HIGH)
- `--all, -a`: Show all tasks including completed

**Examples:**
```bash
zenflow task list
zenflow task list --status TODO
zenflow task list --priority HIGH
zenflow task list --all
```

#### `zenflow task complete TASK_ID`
Mark a task as complete and earn XP

**Arguments:**
- `TASK_ID`: ID of the task to complete (required)

**Example:**
```bash
zenflow task complete 1
```

#### `zenflow task update TASK_ID`
Update task details

**Arguments:**
- `TASK_ID`: ID of the task to update (required)

**Options:**
- `--title, -t`: New title
- `--description, -d`: New description
- `--priority, -p`: New priority (LOW, MEDIUM, HIGH)
- `--due`: New due date (YYYY-MM-DD)
- `--status, -s`: New status (TODO, IN_PROGRESS, DONE)

**Examples:**
```bash
zenflow task update 1 --priority HIGH
zenflow task update 2 --status IN_PROGRESS --due 2026-02-01
zenflow task update 3 -t "Updated title" -d "New description"
```

#### `zenflow task delete TASK_ID`
Delete a task

**Arguments:**
- `TASK_ID`: ID of the task to delete (required)

**Options:**
- `--yes, -y`: Skip confirmation prompt

**Examples:**
```bash
zenflow task delete 1
zenflow task delete 2 --yes
```

---

### Habit Tracking

#### `zenflow habit add NAME`
Create a new habit

**Arguments:**
- `NAME`: Habit name (required)

**Options:**
- `--frequency, -f`: Habit frequency (DAILY, WEEKLY) - default: DAILY
- `--target, -t`: Target streak goal (optional)

**Examples:**
```bash
zenflow habit add "Morning exercise"
zenflow habit add "Read 30 minutes" --frequency DAILY --target 30
zenflow habit add "Weekly review" -f WEEKLY
```

#### `zenflow habit list`
List all habits with streak information

**Options:**
- `--frequency, -f`: Filter by frequency (DAILY, WEEKLY)
- `--active, -a`: Show only habits with active streaks

**Examples:**
```bash
zenflow habit list
zenflow habit list --frequency DAILY
zenflow habit list --active
```

#### `zenflow habit track HABIT_ID`
Mark habit as completed for today

**Arguments:**
- `HABIT_ID`: ID of the habit to track (required)

**Example:**
```bash
zenflow habit track 1
```

#### `zenflow habit calendar HABIT_ID`
Display 30-day habit completion calendar

**Arguments:**
- `HABIT_ID`: ID of the habit (required)

**Options:**
- `--days, -d`: Number of days to display (default: 30, max: 365)

**Examples:**
```bash
zenflow habit calendar 1
zenflow habit calendar 2 --days 90
```

#### `zenflow habit delete HABIT_ID`
Delete a habit

**Arguments:**
- `HABIT_ID`: ID of the habit to delete (required)

**Options:**
- `--yes, -y`: Skip confirmation prompt

**Examples:**
```bash
zenflow habit delete 1
zenflow habit delete 2 --yes
```

---

### Focus Sessions

#### `zenflow focus start`
Start a Pomodoro focus session with live countdown

**Options:**
- `--duration, -d`: Session duration in minutes (default: 25, max: 120)

**Examples:**
```bash
zenflow focus start
zenflow focus start --duration 50
zenflow focus start -d 15
```

**Controls:**
- Press `Ctrl+C` to stop the timer early (no XP awarded)

#### `zenflow focus history`
View focus session history

**Options:**
- `--limit, -l`: Number of recent sessions to show (default: 10)
- `--all, -a`: Show all sessions (completed and incomplete)

**Examples:**
```bash
zenflow focus history
zenflow focus history --limit 20
zenflow focus history --all
```

---

### Gamification

#### `zenflow profile`
Display your profile with gamification stats

Shows:
- Current level and XP
- Progress to next level
- Tasks completed
- Habits tracked
- Focus sessions completed
- Current streaks
- Achievements unlocked

**Example:**
```bash
zenflow profile
```

#### `zenflow achievements`
Display all achievements with unlock status

Shows all available achievements, descriptions, XP rewards, and progress for locked achievements.

**Example:**
```bash
zenflow achievements
```

---

### Statistics

#### `zenflow stats`
Display productivity statistics and analytics

**Options:**
- `--period, -p`: Time period (day, week, month) - default: week

**Examples:**
```bash
zenflow stats
zenflow stats --period day
zenflow stats --period week
zenflow stats --period month
```

**Displays:**
- Total tasks completed
- Total XP earned
- Total focus time
- Active habits count
- Daily breakdown with ASCII chart
- Most/least productive days

---

### AI Insights

#### `zenflow insights`
Get AI-powered productivity insights and recommendations

**Requirements:**
- AI enabled in `config.yaml` (`ai.enabled: true`)
- `OPENAI_API_KEY` environment variable set
- OpenAI library installed (`pip install openai`)

**Example:**
```bash
export OPENAI_API_KEY=sk-...
zenflow insights
```

**Provides:**
- Productivity pattern analysis
- Personalized recommendations
- Optimal work time predictions

---

### Data Export

#### `zenflow export`
Export ZenFlow data to file for backup or analysis

**Options:**
- `--type, -t`: Data type to export (tasks, habits, stats, achievements, focus, all) - default: all
- `--format, -f`: Output format (csv, json, txt) - default: json
- `--output, -o`: Output file path (required)
- `--start-date`: Filter start date (YYYY-MM-DD)
- `--end-date`: Filter end date (YYYY-MM-DD)

**Examples:**
```bash
zenflow export --type tasks --format csv --output tasks.csv
zenflow export --type all --format json --output backup.json
zenflow export -t stats -f txt -o report.txt --start-date 2026-01-01
```

---

## ⚙️ Configuration

ZenFlow uses a `config.yaml` file for configuration. The default configuration is:

```yaml
database:
  path: "zenflow.db"

gamification:
  xp_per_level: 1000
  task_xp:
    low: 10
    medium: 25
    high: 50
  habit_milestone_xp:
    7: 25
    30: 100
    100: 500
  focus_xp: 15

focus:
  default_duration: 25
  break_duration: 5
  long_break_duration: 15

ai:
  enabled: false
  provider: "openai"
  model: "gpt-4"

ui:
  theme: "default"
  color_scheme:
    success: "green"
    warning: "yellow"
    error: "red"
    info: "cyan"
    primary: "blue"

logging:
  level: "INFO"
  file: "zenflow.log"
```

### Environment Variables

Create a `.env` file in the project directory:

```bash
# OpenAI API Key (required for AI insights)
OPENAI_API_KEY=sk-your-api-key-here
```

---

## 🏆 Gamification System

### XP Rewards

**Tasks:**
- LOW priority: 10 XP
- MEDIUM priority: 25 XP
- HIGH priority: 50 XP

**Habits:**
- Daily tracking: 15 XP
- 7-day streak: +25 XP bonus
- 30-day streak: +100 XP bonus
- 100-day streak: +500 XP bonus

**Focus Sessions:**
- Complete 25-min session: 15 XP
- 5 sessions in one day: +25 XP bonus

### Levels

- Level = (Total XP / 1000) + 1
- Each level requires 1000 XP
- No maximum level

### Achievements

**Task Achievements:**
- "First Task" - Complete your first task: +25 XP
- "Task Master" - Complete 10 tasks: +100 XP
- "Centurion" - Complete 100 tasks: +500 XP
- "Task Legend" - Complete 500 tasks: +1000 XP
- "Productive Day" - Complete 5+ tasks in one day: +50 XP
- "Super Productive" - Complete 10+ tasks in one day: +150 XP

**Habit Achievements:**
- "Week Warrior" - Maintain a 7-day streak: +100 XP
- "Month Master" - Maintain a 30-day streak: +300 XP
- "Century Club" - Maintain a 100-day streak: +500 XP
- "Habit Builder" - Create 3 active habits: +75 XP

**Focus Achievements:**
- "Focus Beginner" - Complete 10 focus sessions: +150 XP
- "Focus Master" - Complete 50 focus sessions: +500 XP

**Level Achievements:**
- "Level 5" - Reach level 5: +200 XP
- "Level 10" - Reach level 10: +500 XP

---

## 💡 Examples & Use Cases

### Morning Routine

```bash
# Track your morning habits
zenflow habit track 1  # Morning exercise
zenflow habit track 2  # Meditation
zenflow habit track 3  # Journal

# Add today's tasks
zenflow task add "Review emails" --priority MEDIUM
zenflow task add "Team standup" --priority HIGH --due 2026-01-24

# Start a focus session
zenflow focus start --duration 25
```

### End of Day Review

```bash
# Check your progress
zenflow profile
zenflow stats --period day

# Complete remaining tasks
zenflow task list --status TODO
zenflow task complete 5

# View achievements
zenflow achievements
```

### Weekly Planning

```bash
# Review weekly stats
zenflow stats --period week

# Export data for analysis
zenflow export --type all --format json --output weekly_backup.json

# Get AI insights
zenflow insights

# Plan next week's high-priority tasks
zenflow task add "Quarterly report" --priority HIGH --due 2026-01-31
zenflow task add "Code review sprint" --priority MEDIUM
```

### Backup & Data Management

```bash
# Backup all data
zenflow export --type all --format json --output backup_$(date +%Y%m%d).json

# Export specific data types
zenflow export --type tasks --format csv --output tasks.csv
zenflow export --type habits --format txt --output habits.txt

# Export date range
zenflow export --type stats --format json --output january_stats.json \
  --start-date 2026-01-01 --end-date 2026-01-31
```

---

## 🐛 Troubleshooting

### Database Issues

**Problem:** "No user profile found" error  
**Solution:** Run `zenflow init` to create your profile

**Problem:** Database locked error  
**Solution:** Close any other ZenFlow instances or delete `zenflow.db-journal`

### AI Insights Not Working

**Problem:** "OpenAI Library Not Installed"  
**Solution:** Run `pip install openai`

**Problem:** "AI Insights Disabled"  
**Solution:** 
1. Edit `config.yaml` and set `ai.enabled: true`
2. Set `OPENAI_API_KEY` environment variable
3. Install OpenAI library: `pip install openai`

**Problem:** API Error  
**Solution:**
1. Verify your OpenAI API key is valid
2. Check you have API credits available
3. Ensure internet connection is working

### Focus Timer Issues

**Problem:** Timer not displaying properly  
**Solution:** Ensure your terminal supports Unicode and has sufficient width (minimum 80 columns)

**Problem:** Timer stops unexpectedly  
**Solution:** Don't resize terminal window during countdown. Press Ctrl+C if you need to stop.

### Export Issues

**Problem:** "Directory does not exist" error  
**Solution:** Create the output directory first or use an existing path

**Problem:** File permission error  
**Solution:** Check write permissions for the output directory

---

## 📝 Development

### Project Structure

```
zenflow/
├── zenflow/                  # Main package
│   ├── __init__.py
│   ├── cli.py               # CLI commands
│   ├── core/                # Core business logic
│   │   ├── task_manager.py
│   │   ├── habit_tracker.py
│   │   ├── focus_timer.py
│   │   └── gamification.py
│   ├── database/            # Database layer
│   │   ├── db.py
│   │   └── models.py
│   ├── ai/                  # AI integration
│   │   └── insights.py
│   ├── ui/                  # UI formatting
│   │   ├── formatters.py
│   │   ├── tables.py
│   │   └── charts.py
│   └── utils/               # Utilities
│       ├── config_loader.py
│       ├── logger.py
│       ├── xp_calculator.py
│       ├── streak_calculator.py
│       ├── exporter.py
│       └── exceptions.py
├── zenflow.py               # Entry point
├── config.yaml              # Configuration
├── requirements.txt         # Dependencies
├── setup.py                 # Package setup
└── README.md               # This file
```

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linter
ruff check zenflow/

# Run type checker
mypy zenflow/ --strict

# Format code
black zenflow/
```

---

## 📄 License

This project is provided as-is for educational and personal use.

---

## 🙏 Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [OpenAI](https://openai.com/) - AI insights
- [SQLite](https://www.sqlite.org/) - Local database

---

## 📧 Support

For issues, questions, or suggestions:
1. Check this README for solutions
2. Review the troubleshooting section
3. Check the command help: `zenflow COMMAND --help`

---

**Happy productivity! 🚀**
