from flask import Flask, request, jsonify, Response
from openai import OpenAI
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import time

app = Flask(__name__)

# 🔐 Variables d’environnement
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
ASSISTANT_ID = "asst_xffFyDt65Kdt70BfqGzjdnjf"  # Ton assistant OpenAI

# 🔧 Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# 💾 Mémoire temporaire : {numéro: thread_id}
threads = {}

# 🔁 Envoi du premier SMS depuis Airtable
@app.route("/send-initial-sms", methods=["POST"])
def send_initial_sms():
    data = request.json
    phone_number = data.get("phone_number")

    if not phone_number:
        return jsonify({"error": "phone_number is required"}), 400

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
        return jsonify({"status": "Message envoyé", "thread_id": thread.id}), 200
    except Exception as e:
        print("❌ Erreur Twilio :", str(e))
        return jsonify({"error": str(e)}), 500

# 🤖 Réception et réponse IA via Twilio
@app.route("/reply-sms", methods=["POST"])
def reply_sms():
    try:
        from_number = request.form.get("From")
        user_message = request.form.get("Body")

        print(f"🔁 Message reçu de {from_number} : {user_message}")

        if not from_number or not user_message:
            return Response("Missing data", status=400)

        # Récupère ou crée un thread
        thread_id = threads.get(from_number)
        if not thread_id:
            print("⚠️ Aucun thread trouvé, création d’un nouveau.")
            thread = openai_client.beta.threads.create()
            thread_id = thread.id
            threads[from_number] = thread_id
        else:
            print(f"✅ Thread existant : {thread_id}")

        # Envoie le message utilisateur
        openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Lance le run
        run = openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Attend la complétion
        for _ in range(10):
            run_status = openai_client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                print("❌ Run failed")
                return Response("Erreur assistant", status=500)
            time.sleep(1)

        # Lecture de la réponse de l'assistant
        messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
        full_text = "Je n'ai pas compris, peux-tu reformuler ?"
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                try:
                    full_text = msg.content[0].text.value
                    break
                except Exception as e:
                    print("⚠️ Erreur lecture IA :", str(e))

        # ✂️ Limite à 600 caractères max
        reply_text = full_text[:597] + "..." if len(full_text) > 600 else full_text

        print(f"🤖 Réponse IA tronquée : {reply_text}")

        # Réponse à Twilio en XML
        response = MessagingResponse()
        response.message(reply_text)
        print("📤 XML renvoyé à Twilio :")
        print(str(response))
        return Response(str(response), mimetype="application/xml")

    except Exception as e:
        print("❌ Erreur dans /reply-sms :", str(e))
        return Response("Erreur serveur", status=500)


# 🚀 Port dynamique pour Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

