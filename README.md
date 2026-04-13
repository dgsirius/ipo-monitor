# IPO Monitor

Weekly US IPO tracker with AI analysis. Auto-updated every Monday 06:00 BJT.

**Live page:** https://dgsirius.github.io/ipo-monitor

## Setup

### Prerequisites
- Python 3.11
- Claude Code CLI installed and logged in (`claude --version`)
- Git

### Install
```bash
git clone https://github.com/dgsirius/ipo-monitor.git
cd ipo-monitor
pip install -r requirements.txt
```

### Configure notifications (GitHub Secrets)
Go to repo Settings → Secrets → New repository secret:
- `FEISHU_WEBHOOK_URL` (recommended) — Feishu bot webhook URL
- or `GMAIL_USER` + `GMAIL_APP_PASSWORD` — Gmail app password

### Enable GitHub Pages
Repo Settings → Pages → Source: Deploy from branch → Branch: `main` → Folder: `/docs`

## Usage

### Manual scrape (run locally)
```bash
python scripts/scrape.py      # fetch IPO data
python scripts/build.py --mode basic   # build HTML
```

### Generate AI analysis (after notification)
```bash
python scripts/generate.py    # calls Claude Code CLI per company, then pushes
```

## Architecture
See [design spec](docs/superpowers/specs/2026-04-10-ipo-monitor-design.md).
