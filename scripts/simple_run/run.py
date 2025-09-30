import asyncio
import json
import os
from dotenv import load_dotenv

from gensee_agent.controller.controller import Controller

async def main():

    load_dotenv()

    # task = "How many r's are there in the word 'fshuewrrrrruadarkjabsrrrr'?"
    # task = "List all channels in the Slack workspace."
    task = "Summarize recent conversations in channel 'random' since the beginning of August, and count the number of messages."

    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = json.load(open(config_path, "r"))

    controller = Controller(config)
    async for chunk in controller.run(task):
        print(chunk)
    print("Controller run completed.")

if __name__ == "__main__":
    asyncio.run(main())
