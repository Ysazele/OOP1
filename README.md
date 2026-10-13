# AZSYL Gadget Management System — Render deployment

## Render Web Service settings
- Runtime / Language: Python
- Root Directory: leave blank (these files are at repository root)
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Add environment variable `SECRET_KEY` with a long random value before using the app publicly.

## Files
- `app.py`: Flask application (renamed from the uploaded `ze.py`)
- `requirements.txt`: Python dependencies

## Important limitation
This version stores users, gadgets, and orders in Python memory. They reset when the service restarts or redeploys, and multiple service instances will not share data. It is suitable for a demo, but use a persistent database before relying on it for real orders or accounts.

## Demo login accounts
- Administrator: `admin` / `admin123`
- Staff: `staff` / `staff123`
- Customer: `customer` / `customer123`

Change/remove demo credentials and add persistent storage/security before public production use.
