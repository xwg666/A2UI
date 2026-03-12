"""
General Query Agent - 通用查询 Agent 启动入口

这个模块是 Agent 的启动入口，负责：
1. 初始化 Agent 和执行器
2. 配置 A2A 服务器
3. 启动 HTTP 服务

启动方式：
    python __main__.py --host localhost --port 10002
"""

import sys
import os
# 添加 a2ui 模块路径
A2UI_AGENT_PATH = r'g:\python\项目文件\A2UI\a2a_agents\python\a2ui_agent\src'
sys.path.insert(0, A2UI_AGENT_PATH)

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

# 加载环境变量（从 .env 文件）
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", help="服务器监听地址")
@click.option("--port", default=10002, help="服务器监听端口")
def main(host: str, port: int):
    """
    启动 General Query Agent 服务器
    
    Args:
        host: 服务器监听地址，默认 localhost
        port: 服务器监听端口，默认 10002
    """
    # 构建基础 URL
    base_url = f"http://{host}:{port}"
    logger.info(f"启动 Agent，基础 URL: {base_url}")

    # 初始化 Agent
    # 创建两个 Agent 实例：
    # 1. UI Agent：支持 A2UI 界面生成
    # 2. Text Agent：仅返回纯文本
    ui_agent = GeneralQueryAgent(base_url=base_url, use_ui=True)
    text_agent = GeneralQueryAgent(base_url=base_url, use_ui=False)

    # 创建执行器
    # 执行器负责根据客户端能力选择合适的 Agent
    agent_executor = GeneralQueryAgentExecutor(ui_agent, text_agent)

    # 创建请求处理器
    # DefaultRequestHandler 处理 A2A 协议请求
    # InMemoryTaskStore 用于存储任务状态（内存存储，重启后丢失）
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )

    # 创建 A2A 服务器应用
    # A2AStarletteApplication 是基于 Starlette 的 A2A 协议服务器
    server = A2AStarletteApplication(
        agent_card=ui_agent.get_agent_card(),  # Agent 能力卡片
        http_handler=request_handler,  # 请求处理器
    )

    import uvicorn

    # 构建应用
    app = server.build()

    # 添加 CORS 中间件
    # 允许来自 localhost 的跨域请求
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+",  # 允许 localhost 的所有端口
        allow_credentials=True,
        allow_methods=["*"],  # 允许所有 HTTP 方法
        allow_headers=["*"],  # 允许所有请求头
    )

    # 挂载静态文件目录
    # 用于提供图片等静态资源
    import pathlib
    images_dir = pathlib.Path("images")
    if images_dir.exists():
        app.mount("/static", StaticFiles(directory="images"), name="static")
        logger.info(f"静态文件目录已挂载: /static -> {images_dir.absolute()}")

    # 启动服务器
    logger.info(f"服务器启动在 {base_url}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
