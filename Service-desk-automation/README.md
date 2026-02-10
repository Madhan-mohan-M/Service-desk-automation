# Service Desk Automation (MVP)

Automates IT service desk operations by converting emails into ITSM tickets with classification, auto-resolution, SLA tracking, and notifications.

## Features

| Feature | Description |
|---------|-------------|
| **Email Ingestion** | Reads from file (demo) or Microsoft Graph API (O365) |
| **Issue Classification** | Rule-based categorization and priority assignment |
| **Auto-Resolution** | Low priority tickets auto-closed, High escalated |
| **SLA Tracking** | Monitors response/resolution times, breach warnings |
| **Auto-Assignment** | Routes tickets to teams by category |
| **Email Notifications** | Sends confirmations and escalation alerts |
| **Background Scheduler** | Automatic polling and SLA checks |
| **REST API** | JSON endpoints for integration |

## Quickstart

```powershell
# 1. Create virtualenv and install deps
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Run the app
python app.py
```

Open http://127.0.0.1:5000/ in your browser.

## Configuration

Edit `config.py` or set environment variables:

```bash
# Microsoft Graph API (O365)
GRAPH_CLIENT_ID=your-app-id
GRAPH_CLIENT_SECRET=your-secret
GRAPH_TENANT_ID=your-tenant
GRAPH_USER_EMAIL=servicedesk@yourdomain.com

# SMTP Notifications
SMTP_SERVER=smtp.office365.com
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-password

# Automation
AUTO_PROCESS=true          # Enable background polling
POLL_INTERVAL=60           # Seconds between checks
DEMO_MODE=true             # Use file input instead of O365
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard with stats and SLA |
| `GET /tickets` | All tickets with SLA status |
| `GET /analytics` | Charts and distributions |
| `GET /process` | Trigger email processing |
| `GET /api/status` | Automation health check |
| `GET /api/tickets` | Tickets as JSON |
| `GET /api/sla` | SLA summary |
| `POST /api/ticket/{id}/resolve` | Resolve a ticket |

## Email Format (Demo Mode)

Add emails to `data/emails.txt`:
```
sender@example.com|Subject text|Body text
```

## Tech Stack

- **Backend**: Python + Flask
- **Database**: SQLite
- **Frontend**: HTML + Jinja2 + CSS
- **Scheduling**: APScheduler
- **O365 Integration**: Microsoft Graph API
