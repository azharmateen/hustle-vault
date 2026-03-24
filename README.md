# Hustle Vault

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue?logo=anthropic&logoColor=white)](https://claude.ai/code)


> Side project organizer: track multiple projects, capture ideas, and context-switch like a pro.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**We all have too many side projects.** Hustle Vault helps you track them all, capture ideas on the fly, time your work, and seamlessly switch between projects without losing context.

## Features

- **Project tracking** with status (active/paused/archived)
- **Context switching** - save and restore project state
- **Idea bank** - quick-capture ideas with tags, link to projects later
- **Time tracking** - start/stop timers per project
- **Todo lists** and notes per project
- **Rich dashboard** with stale project detection
- **SQLite storage** - everything local in `~/.hustle-vault/`

## Install

```bash
pip install hustle-vault
```

## Quick Start

```bash
# Add projects
hustle-vault add my-saas --description "SaaS for developers" --path ./my-saas
hustle-vault add side-game --description "Indie game prototype"

# Capture ideas (no project needed)
hustle-vault idea "AI-powered code review tool" --tags ai,saas
hustle-vault idea "Pixel art generator" --tags game,art

# Switch between projects
hustle-vault switch my-saas    # saves current context, restores my-saas

# Track time
hustle-vault timer-start my-saas
# ... do some work ...
hustle-vault timer-stop my-saas

# Add todos and notes
hustle-vault todo my-saas "Set up Stripe integration"
hustle-vault note my-saas "Use webhook approach for payments"

# View everything
hustle-vault dashboard
hustle-vault status my-saas
hustle-vault time-report
hustle-vault ideas --search "ai"
```

## Dashboard

The rich dashboard shows all your projects at a glance, with stale project warnings, running timers, and recent ideas.

```bash
hustle-vault dashboard
```

## Commands

| Command | Description |
|---------|-------------|
| `add <name>` | Add a new project |
| `switch <name>` | Switch to a project (saves/restores context) |
| `list` | List all projects |
| `status <name>` | Detailed project status |
| `idea <text>` | Capture a quick idea |
| `ideas` | List/search ideas |
| `archive <name>` | Archive a project |
| `todo <project> <text>` | Add a todo |
| `note <project> <text>` | Add a note |
| `timer-start <project>` | Start time tracking |
| `timer-stop <project>` | Stop time tracking |
| `time-report` | Show time across all projects |
| `dashboard` | Rich visual dashboard |

## License

MIT
