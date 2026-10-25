
import asyncio
import http
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from websockets.asyncio.server import serve

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_webhook(brainrot, config):
    for group in config.get("webhooks", {}).values():
        names = group.get("brainrots", [])
        if brainrot.casefold() in (name.casefold() for name in names):
            env_name = group.get("environment_variable", "")
            return os.environ.get(env_name)
    return None


def send_discord_webhook(url, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return response.status


async def handle(websocket):
    expected_token = os.environ.get("WS_TOKEN", "")
    supplied_token = websocket.request.headers.get("Authorization", "")

    if expected_token and supplied_token != f"Bearer {expected_token}":
        await websocket.close(code=1008, reason="Unauthorized")
        return

    async for message in websocket:
        try:
            event = json.loads(message)
            brainrot = event.get("brainrot")

            if not isinstance(brainrot, str) or not brainrot.strip():
                await websocket.send(json.dumps({
                    "ok": False,
                    "error": "Missing brainrot field"
                }))
                continue

            config = load_config()
            webhook_url = find_webhook(brainrot.strip(), config)

            if not webhook_url:
                await websocket.send(json.dumps({
                    "ok": False,
                    "error": "No webhook configured for this Brainrot"
                }))
                continue

            discord_payload = {
                "content": f"**Brainrot détecté :** {brainrot[:200]}"
            }

            try:
                await asyncio.to_thread(
                    send_discord_webhook,
                    webhook_url,
                    discord_payload,
                )
                await websocket.send(json.dumps({"ok": True}))
            except (URLError, HTTPError, TimeoutError) as error:
                print(f"Discord webhook error: {error}")
                await websocket.send(json.dumps({
                    "ok": False,
                    "error": "Discord delivery failed"
                }))

        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "ok": False,
                "error": "Invalid JSON"
            }))
        except Exception as error:
            print(f"Event processing error: {error}")
            await websocket.send(json.dumps({
                "ok": False,
                "error": "Event processing failed"
            }))


def health_check(connection, request):
    if request.path == "/healthz":
        return connection.respond(http.HTTPStatus.OK, "OK\n")


async def main():
    port = int(os.environ.get("PORT", "10000"))

    async with serve(
        handle,
        "0.0.0.0",
        port,
        process_request=health_check,
    ):
        print(f"MiawHub WebSocket lancé sur le port {port}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
