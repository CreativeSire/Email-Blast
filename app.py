from flask import Flask, render_template, request, jsonify
import requests
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_ACCOUNT_URL = "https://api.brevo.com/v3/account"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
DB_PATH = os.environ.get("DB_PATH", "email_blast.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email_type TEXT,
            subject TEXT,
            sender_email TEXT,
            from_name TEXT,
            total_contacts INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            recipient_email TEXT NOT NULL,
            recipient_name TEXT,
            status TEXT NOT NULL,
            error_message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );
    """)
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/test-connection", methods=["POST"])
def test_connection():
    data = request.get_json()
    api_key = BREVO_API_KEY or data.get("api_key", "").strip()
    if not api_key:
        return jsonify({"success": False, "message": "No API key configured"}), 400

    try:
        r = requests.get(BREVO_ACCOUNT_URL, headers={"api-key": api_key, "accept": "application/json"}, timeout=10)
        if r.ok:
            info = r.json()
            return jsonify({"success": True, "email": info.get("email", "Account verified")})
        else:
            try:
                err = r.json()
                return jsonify({"success": False, "message": err.get("message", f"Brevo error {r.status_code}")}), 400
            except:
                return jsonify({"success": False, "message": f"Brevo error {r.status_code}: {r.text}"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/send-batch", methods=["POST"])
def send_batch():
    data = request.get_json()
    api_key = BREVO_API_KEY or data.get("api_key", "").strip()
    sender_email = data.get("sender_email", "").strip()
    from_name = data.get("from_name", "Gateway to East Africa").strip()
    reply_to = data.get("reply_to", sender_email).strip()
    subject = data.get("subject", "").strip()
    body_template = data.get("body", "").strip()
    contacts = data.get("contacts", [])
    campaign_id = data.get("campaign_id")

    if not api_key or not sender_email or not subject or not body_template or not contacts:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    sent = []
    failed = []
    conn = get_db()

    for contact in contacts:
        email = contact.get("email", "").strip()
        name = contact.get("name", "Valued Investor").strip()
        first_name = name.split()[0] if name else "Valued Investor"

        body = body_template.replace("{{name}}", first_name)
        html_body = "<pre style='font-family:Georgia,serif;font-size:15px;line-height:1.8;white-space:pre-wrap;max-width:600px;'>" + body.replace("\n", "<br>") + "</pre>"

        payload = {
            "sender": {"name": from_name, "email": sender_email},
            "to": [{"email": email, "name": name}],
            "replyTo": {"email": reply_to},
            "subject": subject,
            "htmlContent": html_body
        }

        try:
            r = requests.post(
                BREVO_API_URL,
                json=payload,
                headers={"api-key": api_key, "content-type": "application/json"},
                timeout=15
            )
            if r.ok:
                sent.append(email)
                if campaign_id:
                    conn.execute(
                        "INSERT INTO sends (campaign_id, recipient_email, recipient_name, status) VALUES (?, ?, ?, ?)",
                        (campaign_id, email, name, "sent")
                    )
            else:
                try:
                    err = r.json()
                    reason = err.get("message", str(r.status_code))
                except:
                    reason = f"Brevo error {r.status_code}: {r.text}"
                failed.append({"email": email, "reason": reason})
                if campaign_id:
                    conn.execute(
                        "INSERT INTO sends (campaign_id, recipient_email, recipient_name, status, error_message) VALUES (?, ?, ?, ?, ?)",
                        (campaign_id, email, name, "failed", reason)
                    )
        except Exception as e:
            failed.append({"email": email, "reason": str(e)})
            if campaign_id:
                conn.execute(
                    "INSERT INTO sends (campaign_id, recipient_email, recipient_name, status, error_message) VALUES (?, ?, ?, ?, ?)",
                    (campaign_id, email, name, "failed", str(e))
                )

    conn.commit()
    conn.close()
    return jsonify({"success": True, "sent": len(sent), "failed": failed})


@app.route("/api/campaign", methods=["POST"])
def create_campaign():
    data = request.get_json()
    name = data.get("name", "Untitled Campaign").strip()
    email_type = data.get("email_type", "").strip()
    subject = data.get("subject", "").strip()
    sender_email = data.get("sender_email", "").strip()
    from_name = data.get("from_name", "").strip()
    total_contacts = data.get("total_contacts", 0)

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO campaigns (name, email_type, subject, sender_email, from_name, total_contacts) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email_type, subject, sender_email, from_name, total_contacts)
    )
    campaign_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"success": True, "campaign_id": campaign_id})


@app.route("/api/campaign/<int:campaign_id>", methods=["PATCH"])
def update_campaign(campaign_id):
    data = request.get_json()
    sent_count = data.get("sent_count")
    failed_count = data.get("failed_count")
    completed = data.get("completed", False)

    conn = get_db()
    if sent_count is not None:
        conn.execute("UPDATE campaigns SET sent_count = ? WHERE id = ?", (sent_count, campaign_id))
    if failed_count is not None:
        conn.execute("UPDATE campaigns SET failed_count = ? WHERE id = ?", (failed_count, campaign_id))
    if completed:
        conn.execute("UPDATE campaigns SET completed_at = ? WHERE id = ?", (datetime.utcnow().isoformat(), campaign_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/history")
def get_history():
    conn = get_db()
    campaigns = conn.execute(
        "SELECT * FROM campaigns ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify({
        "success": True,
        "campaigns": [dict(row) for row in campaigns]
    })


@app.route("/api/history/<int:campaign_id>")
def get_campaign_details(campaign_id):
    conn = get_db()
    campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    sends = conn.execute(
        "SELECT * FROM sends WHERE campaign_id = ? ORDER BY sent_at DESC",
        (campaign_id,)
    ).fetchall()
    conn.close()
    if not campaign:
        return jsonify({"success": False, "message": "Campaign not found"}), 404
    return jsonify({
        "success": True,
        "campaign": dict(campaign),
        "sends": [dict(row) for row in sends]
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
