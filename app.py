"""Servidor Flask para webhooks do WhatsApp Cloud API."""

import hashlib
import hmac
import os

import requests
from dotenv import load_dotenv
from flask import Flask, abort, request

load_dotenv()

import bot
import database

database.initialize_database()
app = Flask(__name__)


def allowed_senders():
    raw = os.getenv("ALLOWED_PHONE_NUMBERS", "")
    return {number.strip() for number in raw.split(",") if number.strip()}


def valid_signature(raw_body):
    secret = os.getenv("META_APP_SECRET", "")
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not secret:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def send_whatsapp_message(recipient, text):
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = os.getenv("PHONE_NUMBER_ID", "")
    api_version = os.getenv("GRAPH_API_VERSION", "")
    if not all((token, phone_number_id, api_version)):
        app.logger.error("Faltam WHATSAPP_ACCESS_TOKEN, PHONE_NUMBER_ID ou GRAPH_API_VERSION")
        return

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        },
        timeout=20,
    )
    response.raise_for_status()


def handle_webhook_event(payload):
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                sender = message.get("from", "")
                if sender not in allowed_senders():
                    app.logger.warning("Mensagem ignorada de número não autorizado")
                    continue
                if message.get("type") != "text":
                    send_whatsapp_message(sender, "Por enquanto, consigo ler mensagens de texto. Envie `ajuda` para ver exemplos.")
                    continue
                reply = bot.handle_message(
                    sender,
                    message.get("text", {}).get("body", ""),
                    message.get("id"),
                )
                send_whatsapp_message(sender, reply)


@app.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge", "")
    expected = os.getenv("VERIFY_TOKEN", "")
    if mode == "subscribe" and expected and hmac.compare_digest(token or "", expected):
        return challenge, 200
    abort(403)


@app.post("/webhook")
def receive_webhook():
    raw_body = request.get_data()
    if not valid_signature(raw_body):
        abort(401)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400)
    if payload.get("object") != "whatsapp_business_account":
        return "ignored", 200
    try:
        handle_webhook_event(payload)
    except requests.RequestException:
        app.logger.exception("Falha ao enviar resposta pelo WhatsApp")
        # Retorna sucesso para o evento não ser reenviado em loop; revise os logs.
    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
