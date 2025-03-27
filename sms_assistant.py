from flask import Flask, request, jsonify, Response
from openai import OpenAI
from twilio.rest import Client
import os
import time

app = Flask(__name__)

# 🔐 Clés API depuis variables d’environnement
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
ASSISTANT_ID = "asst_xffFyDt65Kdt70BfqGzjdnjf"  # Ton assistant OpenAI

# ⚙️ Clients API
openai_client = OpenAI(api_key=OPENAI_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# 🧠 Mémoire simple : numéro => thread_id
threads = {}

# ✅ 1. Endpoint déclenché depuis Airtable
@app.route("/send-initial-sms", methods=["POST"])
def send_initial_sms():
    data = request.json
    phone_number = data.get("phone_number")

    if not phone_number:
        return jsonify({"error": "phone_number is required"}), 400

    # Crée un thread pour ce numéro
    thread = openai_client.beta.threads.create()
    threads[phone_number] = thread.id
    print(f"📥 Thread créé pour {phone_number} : {thread.id}")

    message_text = (
        "Salut ! C’est l’assistant Smart Caller AI 🤖\n"
        "Tu as pu tester l’outil ? Dis-moi ce que tu en as pensé ! Tu as des questions ?"
    )

    try:
        message = twilio_client.messages.create(
            body=message_text,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"✅ SMS initial envoyé à {phone_number} : {message.sid}")
        return jsonify({
            "status": "Message envoyé",
            "sid": message.sid,
            "thread_id": thread.id
        }), 200
    except Exception as e:
        print("❌ Erreur envoi Twilio :", str(e))
        return jsonify({"error": str(e)}), 500

# ✅ 2. Endpoint déclenché par Twilio quand l’utilisateur répond
@app.route("/reply-sms", methods=["POST"])
def reply_sms():
    try:
        from_number = request.form.get("From")
        user_message = request.form.get("Body")

        print(f"🔁 Réponse reçue de {from_number} : {user_message}")

        # ✅ TEST TEMPORAIRE : Réponse simple à Twilio
        xml_test = """<?xml version="1.0" encoding="UTF-8"?><Response><Message>Réponse test simple !</Message></Response>"""
        print("📤 Réponse test à Twilio :")
        print(xml_test)
        return Response(xml_test, mimetype="application/xml")

    except Exception as e:
        print("❌ Erreur dans /reply-sms :", str(e))
        return Response("Erreur serveur", status=500)

# ✅ Pour Railway : port dynamique
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

