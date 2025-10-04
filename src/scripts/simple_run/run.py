import asyncio
import json
import os
from dotenv import load_dotenv

from gensee_agent.controller.controller import Controller

async def ainput(prompt: str = "") -> str:
    return await asyncio.to_thread(input, prompt)

async def interactive_callback(question: str) -> str:
    print(f"User interaction requested. Question: {question}")
    return await ainput("Your answer: ")

async def main():

    load_dotenv()

    # task = "How many r's are there in the word 'fshuewrrrrruadarkjabsrrrr'?"
    # task = "List all channels in the Slack workspace."
    # task = "Summarize recent conversations in channel 'random' since the beginning of August, and count the number of messages."
    # task = "Summarize recent conversations in channel 'random', and count the number of messages."
    task = "Tell me the current time and what's the weather like today in Fremont, CA?"

    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = json.load(open(config_path, "r"))

    controller = await Controller.create(config, interactive_callback=interactive_callback)
    async for chunk in controller.run(task):
        print(chunk)
    print("Controller run completed.")

if __name__ == "__main__":
    asyncio.run(main())
