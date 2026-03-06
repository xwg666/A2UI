import logging
import os

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from agent import PeopleFinderAgent
from agent_executor import PeopleFinderAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = "localhost"
PORT = int(os.getenv("PORT", "10010"))


def create_app():
    base_url = f"http://{HOST}:{PORT}"
    
    ui_agent = PeopleFinderAgent(base_url, use_ui=True)
    text_agent = PeopleFinderAgent(base_url, use_ui=False)
    
    agent_executor = PeopleFinderAgentExecutor(ui_agent, text_agent)
    
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )
    
    server = A2AStarletteApplication(
        agent_card=ui_agent.get_agent_card(),
        http_handler=request_handler,
    )
    
    app = server.build()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


app = create_app()

if __name__ == "__main__":
    logger.info(f"Starting server at http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
