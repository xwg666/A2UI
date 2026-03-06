import logging
import os

import click
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from agent import GeneralQueryAgent
from agent_executor import GeneralQueryAgentExecutor
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10002)
def main(host, port):
    base_url = f"http://{host}:{port}"

    ui_agent = GeneralQueryAgent(base_url=base_url, use_ui=True)
    text_agent = GeneralQueryAgent(base_url=base_url, use_ui=False)

    agent_executor = GeneralQueryAgentExecutor(ui_agent, text_agent)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=ui_agent.get_agent_card(), http_handler=request_handler
    )

    import uvicorn

    app = server.build()

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    import pathlib
    images_dir = pathlib.Path("images")
    if images_dir.exists():
        app.mount("/static", StaticFiles(directory="images"), name="static")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
