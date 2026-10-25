
import asyncio
import http
import os
import json
import urllib.request
import urllib.error
from websockets.asyncio.server import serve

WEBHOOK_URL = os.environ.get("https://discord.com/api/webhooks/1564010073452445736/VjxJADgw0NHYuIFgIKGCp3qJTSLXGJFoBfK1S3KL9VZhNHCgkALGk9Vxm-kOQNk_GOd3", "")
WS_TOKEN = os.environ.get("WS_TOKEN", "")


async def send_to_discord(message):
    if not WEBHOOK_URL:
        print("Webhook Discord non configuré.")
        return

    payload = json.dumps({
        "content": message[:2000]
    }).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    def send():
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status

    try:
        status = await asyncio.to_thread(send)
        print(f"Discord a répondu : {status}")
    except Exception as error:
        print(f"Erreur d'envoi Discord : {error}")


async def handle(websocket):
    try:
        if WS_TOKEN:
            supplied_token = websocket.request.headers.get(
                "Authorization", ""
            )
            if supplied_token != f"Bearer {WS_TOKEN}":
                await websocket.close(
                    code=1008,
                    reason="Authentification requise"
                )
                return

        async for message in websocket:
            print(f"Message reçu : {message[:500]}")

            try:
                data = json.loads(message)
                name = data.get("name", "Événement")
                category = data.get("category", "")
                text = f"**{name}**"
                if category:
                    text += f" — {category}"
            except (json.JSONDecodeError, AttributeError):
                text = message

            await send_to_discord(text)
            await websocket.send("Événement traité")

    except Exception as error:
        print(f"Erreur WebSocket : {error}")


def health_check(connection, request):
    if request.path == "/healthz":
        return connection.respond(http.HTTPStatus.OK, "OK\n")


async def main():
    port = int(os.environ.get("PORT", "10000"))

    async with serve(
        handle,
        "0.0.0.0",
        port,
        process_request=health_check
    ):
        print(f"MiawHub WebSocket lancé sur le port {port}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
