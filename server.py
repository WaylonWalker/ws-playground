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
from fastapi.responses import HTMLResponse
import json
from redis import asyncio as redis

from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Redis connection
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

new_button = """

            <div id='after_chat_wrapper'>
                <div
                    id='after_chat'
                    class='h-12'
                    _="
                    on load
                      wait 10ms
                    on intersection(intersecting) having threshold 0.5
                      if #go_to_bottom exists and intersecting
                      then remove #go_to_bottom
                      

                      "
                >
                </div>
            </div>
            <div id="after_form" class='mb-24 flex gap-2'>
                <button
                    id="go_to_bottom"
                    class="fixed bottom-0 right-0 px-2 py-1 rounded font-bold m-4 invisible"
                    hx-get="/null"
                    hx-swap="outerHTML"
                    hx-trigger="intersect from:#after_chat"
                    _="
                    on load
                       wait 10ms
                       remove .invisible
                    on click
                       go to bottom of the body
                       "
                    >
                    go to bottom
                </button>
                <button
                    class="fixed bottom-0 left-0 px-2 py-1 rounded font-bold m-4 bg-red-500 text-white"
                    hx-get="/clear-chat"
                    hx-swap="none"
                    _="on click
                       add .opacity-50 to me
                       wait 200ms
                       remove .opacity-50 from me"
                    >
                    clear chat
                </button>
            </div>

"""
reset_form = """

            <form
                id="form"
                ws-send class="flex gap-2 fixed bottom-0 w-full p-4 bg-gray-900"
                _="on load focus() the first <input/> in me"

            >
                <input
                    id="chatInput"
                    name="chat_message"
                    class='w-124 min-h-24 rounded-lg px-2 py-1 mx-auto bg-gray-800 border border-gray-600 rounded'
                    type="text"
                >
            </form>
"""
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
        print(message)
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
                html_data = ""

                if "chat_message" in data:
                    if data.get("name") == name:
                        html_data += f'<div id="chat_room" hx-swap-oob="beforeend" hx-swap="scroll:bottom"><li class="px-4 py-2 h-12 w-124 rounded bg-green-{color_level} ml-8 my-4">{data.get("name")}: {data.get("chat_message")}</li></div>'
                    else:
                        html_data += f'<div id="chat_room" hx-swap-oob="beforeend" hx-swap="scroll:bottom"><li class="px-4 py-2 h-12 w-124 rounded bg-blue-{color_level} my-4">{data.get("name")}: {data.get("chat_message")}</li></div>'
                if "notification" in data:
                    html_data += f'<div id="notifications" hx-swap-oob="beforeend"><li class="px-4 py-2 h-12 w-64 rounded bg-blue-{color_level} my-4" _="on click remove me on load wait 3s remove me" hx-trigger="click, load delay:3s" hx-swap="outerHTML">{data.get("notification")}</li></div>'
                await websocket.send_text(html_data + new_button)


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
    data = {
        "name": name,
        "notification": f"{name} joined the chat",
    }

    data_str = json.dumps(data)

    await redis_client.publish(WEBSOCKET_CHANNEL, data_str)

    # Send previous messages to the new client
    messages = await redis_client.lrange(REDIS_MESSAGE_LIST, 0, -1)
    for msg in messages:
        msg_data = json.loads(msg)
        color_level = color_levels[0]  # Use first color level for old messages
        html_data = ""
        if "chat_message" in msg_data:
            if msg_data.get("name") == name:
                html_data += f'<div id="chat_room" hx-swap-oob="beforeend"><li class="px-4 py-2 h-12 w-124 rounded bg-green-{color_level} ml-8 my-4" _="">{msg_data.get("name")}: {msg_data.get("chat_message")}</li></div>'

            else:
                html_data += f'<div id="chat_room" hx-swap-oob="beforeend"><li class="px-4 py-2 h-12 w-124 rounded bg-blue-{color_level} my-4" _="">{msg_data.get("name")}: {msg_data.get("chat_message")}</li></div>'
        if "notification" in msg_data:
            html_data += f'<div id="notifications" hx-swap-oob="beforeend"><li class="px-4 py-2 h-12 w-64 rounded bg-blue-{color_level} my-4">{msg_data.get("notification")}</li></div>'
        await websocket.send_text(html_data + new_button)

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
            await websocket.send_text(reset_form)
    except WebSocketDisconnect:
        connected_clients.pop(name)


@app.get("/clear-chat")
async def clear_chat():
    await redis_client.delete(REDIS_MESSAGE_LIST)
    return """
        <div id="chat_room" hx-swap-oob="innerHTML"></div>
        <div id="notifications" hx-swap-oob="innerHTML"></div>
    """


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/null")
async def root(request: Request):
    return HTMLResponse("")


if __name__ == "__main__":
    import uvicorn

    import sys

    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    uvicorn.run("server:app", host="0.0.0.0", port=port, workers=6)
