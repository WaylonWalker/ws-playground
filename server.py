#!/usr/bin/env -S uv run --quiet --locked --script --no-cache
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastapi",
#     "redis",
#     "asyncio",
#     "uvicorn[standard]",
#     "jinja2",
# ]
# ///

import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
import json
from redis import asyncio as redis

from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Redis connection
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Constants
REDIS_MESSAGE_LIST = "chat_messages"
WEBSOCKET_CHANNEL = "websocket_channel"

# Store connected WebSockets
connected_clients = {}

color_levels = [400, 500, 600, 700, 800, 900]


async def listen_to_redis():
    level = 0
    level_increment = 1
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(WEBSOCKET_CHANNEL)

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"]
            data = json.loads(data)
            if level == len(color_levels) - 1:
                level_increment = -1
            elif level == 0:
                level_increment = 1
            level += level_increment
            color_level = color_levels[level]
            # Send message to all connected clients
            for name, websocket in connected_clients.items():
                if data.get("name") == name:
                    html_data = f'<div id="chat_room" hx-swap-oob="beforeend"><li class="px-4 py-2 h-12 w-64 rounded bg-green-{color_level} ml-8 my-4">{data.get("name")}: {data.get("chat_message")}</li></div>'
                else:
                    html_data = f'<div id="chat_room" hx-swap-oob="beforeend"><li class="px-4 py-2 h-12 w-64 rounded bg-blue-{color_level} my-4">{data.get("name")}: {data.get("chat_message")}</li></div>'
                await websocket.send_text(html_data)


@app.on_event("startup")
async def startup():
    asyncio.create_task(listen_to_redis())


chat_names = [
    "Gregory",
    "Waylon",
    "John",
    "Jane",
    "Bob",
    "Alice",
    "Charlie",
    "Diana",
    "Ethan",
    "Fiona",
    "Grace",
    "Henry",
    "Isabella",
    "Jack",
    "Katherine",
    "Liam",
    "Mia",
    "Noah",
    "Olivia",
    "Oscar",
    "Penelope",
    "Quinn",
    "Riley",
    "Sophia",
    "Theo",
    "Uma",
    "Violet",
    "Walter",
    "Xavier",
    "Yvonne",
    "Zachary",
]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    import random

    name = random.choice(chat_names)
    connected_clients[name] = websocket
    
    # Send previous messages to the new client
    messages = await redis_client.lrange(REDIS_MESSAGE_LIST, 0, -1)
    for msg in messages:
        msg_data = json.loads(msg)
        color_level = color_levels[0]  # Use first color level for old messages
        if msg_data.get("name") == name:
            html_data = f'<div id="chat_room" hx-swap-oob="beforeend"><li class="px-4 py-2 h-12 w-64 rounded bg-green-{color_level} ml-8 my-4">{msg_data.get("name")}: {msg_data.get("chat_message")}</li></div>'
        else:
            html_data = f'<div id="chat_room" hx-swap-oob="beforeend"><li class="px-4 py-2 h-12 w-64 rounded bg-blue-{color_level} my-4">{msg_data.get("name")}: {msg_data.get("chat_message")}</li></div>'
        await websocket.send_text(html_data)
    
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            data["name"] = name
            data_str = json.dumps(data)
            
            # Store message in Redis list
            await redis_client.rpush(REDIS_MESSAGE_LIST, data_str)
            
            # Publish message to Redis
            await redis_client.publish(WEBSOCKET_CHANNEL, data_str)
    except WebSocketDisconnect:
        connected_clients.pop(name)


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    import sys

    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    uvicorn.run("server:app", host="0.0.0.0", port=port, workers=6)
