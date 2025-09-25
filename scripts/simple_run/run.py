import asyncio
import json
import os
from dotenv import load_dotenv

from gensee_agent.controller.controller import Controller

def main():

    load_dotenv()

    task = "How many r's are there in the word 'fshuewrrrrruadarkjabsrrrr'?"

    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = json.load(open(config_path, "r"))

    controller = Controller(config)
    asyncio.run(controller.run(task))
    print("Controller run completed.")

if __name__ == "__main__":
    main()