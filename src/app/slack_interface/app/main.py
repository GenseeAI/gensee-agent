import asyncio
from contextlib import asynccontextmanager
import json
import logging
from dotenv import load_dotenv
import os
from fastapi import FastAPI
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

from gensee_agent.controller.controller import Controller

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

bolt_app = AsyncApp(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)
gensee_agent_controller = None

@bolt_app.event("app_mention")
async def on_mention(body, say):
    print("Received app_mention event: ", body)
    user = body["event"]["user"]
    await say(f"hey <@{user}>, FastAPI is still in the mix!")

# IMPORTANT: subscribe to message.im in app config (not app_mention)
@bolt_app.event("message")
async def on_dm_events(body, event, say, client, logger):
    # Only handle real user DMs (not bot echoes, not channels)
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id"):  # ignore bot messages
        return
    if event.get("subtype"):  # message_changed, message_deleted, etc.
        return

    print(f"✅ DM body: {body}")
    text = event.get("text", "")
    show_text = await say(f"Working on your request: “{text}”")
    assert gensee_agent_controller is not None
    async for chunk in gensee_agent_controller.run(text):
        logging.info(f"🔄 Chunk: {chunk}")
        if len(chunk) > 40000:
            chunk = chunk[:39997] + "..."
        await client.chat_update(
            channel=show_text["channel"],
            ts=show_text["ts"],
            text=chunk,
        )

@bolt_app.command("/hello")
async def on_hello(ack, respond, command):
    print("Received /hello command: ", command)
    await ack()
    await respond(f"Hello from Bolt-in-FastAPI, <@{command['user_id']}>!")

async def _run_socket(handler: AsyncSocketModeHandler):
    # Start and keep the websocket alive until cancelled
    await handler.start_async()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global socket_handler, socket_task
    socket_handler = AsyncSocketModeHandler(bolt_app, app_token=os.environ["SLACK_APP_TOKEN"])
    socket_task = asyncio.create_task(_run_socket(socket_handler))
    logging.info("✅ Socket Mode started")

    global gensee_agent_controller
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = json.load(open(config_path, "r"))
    gensee_agent_controller = await Controller.create(config)
    logging.info("✅ Gensee Agent Controller initialized")

    try:
        yield
    finally:
        logging.info("🛑 Shutting down Socket Mode…")
        # 1) Cancel the running task
        if socket_task and not socket_task.done():
            socket_task.cancel()
            try:
                await socket_task
            except asyncio.CancelledError:
                pass
        # 2) Close the handler (and underlying client/session)
        #    close_async() exists for the async handler
        if socket_handler:
            await socket_handler.close_async()
        logging.info("✅ Clean shutdown complete")

app = FastAPI(title="Gensee Agent for Slack", lifespan=lifespan)

@app.get("/healthz")
async def healthz():
    return {"ok": True}