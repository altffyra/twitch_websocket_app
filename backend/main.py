import asyncio
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    async def send_periodic():
        while True:
            await asyncio.sleep(5)
            await ws.send_text("Periodic message from backend")

    periodic_task = asyncio.create_task(send_periodic())

    try:
        while True:
            data = await ws.receive_text()
            await ws.send_text(f"You said: {data}")
    except Exception:
        periodic_task.cancel()