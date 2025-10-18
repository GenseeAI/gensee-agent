import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
import json_repair
from pydantic import BaseModel
from typing import Optional
import json
import re

from gensee_agent.controller.controller import Controller

logger = logging.getLogger("uvicorn.error")
logging.basicConfig(level=logging.INFO)


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    global gensee_agent_controller
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = json.load(open(config_path, "r"))
    gensee_agent_controller = await Controller.create(config)
    logger.info("✅ Gensee Agent Controller initialized")

    try:
        yield
    finally:
        logger.info("🛑 Shutting down Socket Mode…")
        logger.info("✅ Clean shutdown complete")

app = FastAPI(title="Deep Search", lifespan=lifespan)
gensee_agent_controller = None

class AgentRequest(BaseModel):
    task: str

class AgentResponse(BaseModel):
    status: str
    result: Optional[str] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Gensee Agent API is running"}

async def run_agent(request: AgentRequest):
    try:
        chunks = []
        assert gensee_agent_controller is not None
        async for chunk in gensee_agent_controller.run(request.task):
            chunks.append(chunk)

        result = "\n".join(chunks)
        return AgentResponse(
            status="completed",
            result=result
        )

    except Exception as e:
        logger.error(f"Error running agent: {e}.  Error class: {e.__class__} ", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class DeepSearchRequest(BaseModel):
    query: str

@app.post("/agent/deep-search")
async def deep_search(request: DeepSearchRequest):
    task = f"""You are an expert web search agent.  Your goal is to find the most relevant and accurate information from the web based on the user's query.

    You can use the `gensee.search` tool to perform web searches.  You can also breakdown the task into multiple sub-queries if needed to find the best information.

    The user's query is: {request.query}

    Please return the results in the following format:
    ```
    <answer>
    A short sentence or paragraph to answer the user's query.
    </answer>
    <explanation>
    A brief explanation of how you arrived at the results, including any reasoning steps or sub-queries you used.
    </explanation>
    <references>
    [
        {{
            "title": "Title of the web page",
            "url": "URL of the web page",
            "snippet": "A short snippet or summary from the web page"
        }},
        ...
    ]
    </references>
    <visited_urls>
    [
        "List of URLs you visited during your search",
        ...
    ]
    </visited_urls>
    ```

    Requirements:
    - Be concise and to the point in the <answer> section.  It should directly answer the user's query.  Do not include any process, reasoning or explanations in this section.
    - If you don't know the answer, just say "I don't know." in the <answer> section, and leave other sections empty.
    - Briefly explain your reasoning in the <explanation> section.
    - List references useful to answer the query in the <references> section.  Each reference should include the title, URL, and a short snippet which directly come from existing `gensee.search` tool result.
    - Do not list irrelevant references in the <references> section, even if you visited those pages.
    - List all URLs you visited during your search in the <visited_urls> section, even if they don't lead to the final answer.
    - The <references> and <visited_urls> sections should be in JSON format.
    """

    results = await run_agent(AgentRequest(task=task))

    if results.status != "completed" or results.result is None:
        raise HTTPException(status_code=500, detail="Agent failed to complete the task.")

    # Look for <answer>, <references>, <visited_urls> in the results.result
    answer_match = re.search(r"<answer>(.*?)</answer>", results.result, re.DOTALL)
    references_match = re.search(r"<references>(.*?)</references>", results.result, re.DOTALL)
    visited_urls_match = re.search(r"<visited_urls>(.*?)</visited_urls>", results.result, re.DOTALL)
    explanation_match = re.search(r"<explanation>(.*?)</explanation>", results.result, re.DOTALL)

    response = {
        "status": results.status,
        "answer": answer_match.group(1) if answer_match else "No answer found.",
        "references": json_repair.loads(references_match.group(1)) if references_match else [],
        "visited_urls": json_repair.loads(visited_urls_match.group(1)) if visited_urls_match else [],
        "explanation": explanation_match.group(1) if explanation_match else "No explanation found.",
        "error": results.error
    }
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("deep_search.app.main:app", host="0.0.0.0", port=7000, reload=True, log_level="debug")