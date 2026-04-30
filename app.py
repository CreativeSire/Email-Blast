from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_ACCOUNT_URL = "https://api.brevo.com/v3/account"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")


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

    if not api_key or not sender_email or not subject or not body_template or not contacts:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    sent = []
    failed = []

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
            else:
                try:
                    err = r.json()
                    failed.append({"email": email, "reason": err.get("message", str(r.status_code))})
                except:
                    failed.append({"email": email, "reason": f"Brevo error {r.status_code}: {r.text}"})
        except Exception as e:
            failed.append({"email": email, "reason": str(e)})

    return jsonify({"success": True, "sent": len(sent), "failed": failed})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
