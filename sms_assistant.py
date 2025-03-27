from flask import Flask, request, jsonify
from openai import OpenAI
from twilio.rest import Client
import os

app = Flask(__name__)

# ⚙️ Clés API depuis ton environnement
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# ⚙️ Instances clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# 🧠 Mémoire simple : numéro => thread_id
threads = {}

# 📤 Endpoint pour envoyer le 1er SMS (appelé par Airtable)
@app.route("/send-initial-sms", methods=["POST"])
def send_initial_sms():
    data = request.json
    phone_number = data.get("phone_number")

    if not phone_number:
        return jsonify({"error": "phone_number is required"}), 400

    # 🔁 Créer un thread pour ce numéro
    thread = openai_client.beta.threads.create()
    threads[phone_number] = thread.id

    # 💬 Message initial
    message_text = (
        "Salut ! C’est l’assistant Smart Caller AI 🤖\n"
        "Tu as pu tester l’outil ? Dis-moi ce que tu en as pensé ! Tu as des questions ?"
    )

    # ✉️ Envoi du SMS via Twilio
    try:
        message = twilio_client.messages.create(
            body=message_text,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        return jsonify({
            "status": "Message envoyé",
            "sid": message.sid,
            "thread_id": thread.id
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

