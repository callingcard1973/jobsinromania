# Flask Dashboard MVP

Unified management dashboard for InterJob European Recruitment Network — 28 job sites, email campaigns, scrapers, CV processing.

## Setup

### Prerequisites

- Python 3.12+
- Windows 10+ or Linux

### Installation

1. Clone the repository or navigate to D:\MEMORY\CODE\WEB

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings:
   # - SSH credentials for raspibig (192.168.100.21)
   # - FTP credentials for Gazduire
   # - cPanel API token for A2 Hosting
   # - WordPress REST API credentials (Phase 2+)
   ```

5. Run the dashboard:
   ```bash
   python app.py
   ```

   Dashboard will be available at `http://localhost:5055` (or custom PORT in .env)

## Project Structure

```
D:\MEMORY\CODE\WEB\
├── app.py                 — Main Flask application (Phase 1+)
├── dashboard/
│   ├── __init__.py       — Package initialization
│   ├── models.py         — Peewee ORM models (Phase 1+)
│   ├── routes.py         — Flask route handlers (Phase 1+)
│   └── templates/        — Jinja2 HTML templates (Phase 1+)
├── requirements.txt      — Python dependencies
├── .env.example          — Environment template
└── README.md             — This file
```

## Configuration

All settings are loaded from `.env` file using `python-dotenv`:

- **DEBUG**: Enable Flask debug mode (False for production)
- **PORT**: Server port (default 5055)
- **DATABASE_PATH**: SQLite database location
- **SSH_HOST/USER/KEY_PATH**: Remote execution on raspibig
- **FTP_HOST/USER/PASS**: File uploads to Gazduire
- **CPANEL_HOST/USER/TOKEN**: A2 Hosting cPanel API (Phase 2+)
- **A2_REST_USER/PASSWORD**: WordPress REST API (Phase 2+)

## Development

Phase 1 focuses on:
- Site status dashboard
- SSH command execution to raspibig
- FTP file management
- Local SQLite database for audit logs

Phase 2+ adds:
- cPanel DNS management
- WordPress REST API integration
- Advanced campaign scheduling

## Support

Contact: tudor@oipa.ro (OIPA) or manpower.dristor@gmail.com (InterJob)
