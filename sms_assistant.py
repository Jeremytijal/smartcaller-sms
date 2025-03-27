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


from twilio.twiml.messaging_response import MessagingResponse
import time

@app.route("/reply-sms", methods=["POST"])
def reply_sms():
    from_number = request.form.get("From")
    user_message = request.form.get("Body")

    if not from_number or not user_message:
        return "Missing data", 400

    # Vérifie si un thread existe pour ce numéro
    thread_id = threads.get(from_number)
    if not thread_id:
        # Si aucun thread, on en crée un nouveau
        thread = openai_client.beta.threads.create()
        thread_id = thread.id
        threads[from_number] = thread_id

    # 1. Ajoute le message utilisateur au thread
    openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # 2. Lance une interaction avec l’assistant
    run = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id="asst_xffFyDt65Kdt70BfqGzjdnjf"
    )

    # 3. Attendre que le run soit terminé (petit polling simple)
    for _ in range(10):
        run_status = openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status == "failed":
            return "Erreur assistant", 500
        time.sleep(1)

    # 4. Récupère la dernière réponse de l’assistant
    messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            reply_text = msg.content[0].text.value
            break
    else:
        reply_text = "Je n'ai pas compris, peux-tu reformuler ?"

    # 5. Répond via Twilio
    response = MessagingResponse()
    response.message(reply_text)
    return str(response)


