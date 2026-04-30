# Gateway to East Africa — Email Blast System

A production-grade email campaign manager built with Flask and the Brevo API. Upload contacts from Excel, compose up to 4 customised emails, schedule automatic sends, and blast to 800+ contacts at once.

## Features

- Excel contact upload (.xlsx / .xls)
- 4-email campaign flow: Confirmation, 6-Hour, 1-Hour, 30-Min reminders
- `{{name}}` personalisation per email
- Server-side scheduling (works even with browser closed)
- Live log and delivery counters
- Brevo API integration for reliable bulk delivery

## Deploy to Railway

1. Fork or clone this repo
2. Connect to Railway at [railway.app](https://railway.app)
3. Select this repo and deploy — Railway auto-detects Python
4. No environment variables needed (API key entered in the UI)

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`

## Usage

1. **Contacts** — Upload your Excel file (needs an `Email` column)
2. **Compose** — Edit all 4 email templates
3. **Schedule** — Set send times or use auto-fill
4. **Launch** — Activate the campaign

## Built By

Dewale Consulting Limited | [consultdewale.com](https://consultdewale.com)
