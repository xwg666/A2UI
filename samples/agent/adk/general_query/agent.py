
import json
import logging
import os
from collections.abc import AsyncIterable
from typing import Any

import jsonschema
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from prompt_builder import get_ui_prompt, get_text_prompt
from tools import get_data, text_response
from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

logger = logging.getLogger(__name__)


class GeneralQueryAgent:
    """通用数据查询 Agent"""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, base_url: str, use_ui: bool = False):
        self.base_url = base_url
        self.use_ui = use_ui
        self._schema_manager = (
            A2uiSchemaManager(
                "0.8",
                basic_examples_path="../restaurant_finder/examples/",
                schema_modifiers=[remove_strict_validation],
            )
            if use_ui
            else None
        )
        self._agent = self._build_agent(use_ui)
        logger.info(f"Agent 结果 : {self._agent}")
        self._user_id = "remote_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_agent_card(self) -> AgentCard:
        capabilities = AgentCapabilities(
            streaming=True,
            extensions=[self._schema_manager.get_agent_extension()] if self.use_ui and self._schema_manager else [],
        )
        skill = AgentSkill(
            id="general_query",
            name="通用查询",
            description="根据用户查询返回相应的数据展示界面",
            tags=["query", "search", "data"],
            examples=["查询员工", "查看菜品", "搜索人员","查询生日"],
        )
        print('skills',skill)
        return AgentCard(
            name="通用查询助手",
            description="通用数据查询助手，支持多种数据类型",
            url=self.base_url,
            version="1.0.0",
            default_input_modes=self.SUPPORTED_CONTENT_TYPES,
            default_output_modes=self.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

    def get_processing_message(self) -> str:
        return "正在查询数据..."

    def _build_agent(self, use_ui: bool) -> LlmAgent:
        LITELLM_MODEL = os.getenv("LITELLM_MODEL", "dashscope/qwen-turbo")
        # 使用 modelscope 的 GLM 模型
        # os.environ["MODELSCOPE_API_KEY"] = os.getenv("GLM_API_KEY", "")
        # LITELLM_MODEL = os.getenv("LITELLM_MODEL", "modelscope/ZhipuAI/GLM-4-Flash")

        instruction = get_ui_prompt() if use_ui else get_text_prompt()
        logger.info(f"提示词: {instruction}...")

        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name="general_query_agent",
            description="通用AI助手",
            instruction=instruction,
            tools=[get_data],
        )

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        session_state = {"base_url": self.base_url}

        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state=session_state,
                session_id=session_id,
            )
        elif "base_url" not in session.state:
            session.state["base_url"] = self.base_url

        max_retries = 1
        attempt = 0
        current_query = query

        while attempt <= max_retries:
            attempt += 1
            logger.info(f"--- GeneralQueryAgent: 第 {attempt}/{max_retries + 1} 次尝试 ---")

            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=current_query)],
            )
            
            full_messages = [
                types.Content(
                    role="system",
                    parts=[types.Part.from_text(text=self._agent.instruction)]
                ),
                message
            ]
            # logger.info(f"=== 发送给 LLM 的完整消息 ===")
            # for i, msg in enumerate(full_messages):
            #     logger.info(f"消息 {i}: role={msg.role}, parts={msg.parts}")
            # logger.info(f"========================")
            
            final_content = None

            async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                new_message=message,
            ):
                if event.is_final_response():
                    final_content = "\n".join(
                            p.text for p in event.content.parts if p.text)
                    break
                else:
                    yield {
                        "is_task_complete": False,
                        "updates": self.get_processing_message(),
                    }

            if final_content is None:
                if attempt <= max_retries:
                    current_query = f"请重试: {query}"
                    continue
                else:
                    yield {
                        "is_task_complete": True,
                        "content": "抱歉，查询失败，请稍后重试。",
                    }
                    return

            logger.info(f"=== LLM 最终响应内容 ===\n{final_content}\n========================")

            is_valid = False
            error_msg = ""

            if self.use_ui and self._schema_manager:
                try:
                    if "---a2ui_JSON---" not in final_content:
                        raise ValueError("缺少分隔符 ---a2ui_JSON---")

                    _, json_str = final_content.split("---a2ui_JSON---", 1)
                    json_cleaned = json_str.strip().lstrip("```json").rstrip("```").strip().replace("---a2ui_JSON---", "")

                    logger.info(f"LLM 生成的 A2UI JSON: {json_cleaned}")

                    if not json_cleaned or json_cleaned == "[]":
                        is_valid = True
                    else:
                        try:
                            parsed = json.loads(json_cleaned)
                        except json.JSONDecodeError as e:
                            try:
                                json_cleaned_fixed = json_cleaned[:e.pos] + json_cleaned[e.pos+1:]
                                parsed = json.loads(json_cleaned_fixed)
                            except:
                                json_cleaned = "[" + json_cleaned + "]"
                                parsed = json.loads(json_cleaned)

                        catalog = self._schema_manager.get_selected_catalog()
                        if catalog and catalog.validator:
                            catalog.validator.validate(parsed)
                        is_valid = True

                except (ValueError, json.JSONDecodeError, jsonschema.exceptions.ValidationError) as e:
                    logger.warning(f"验证失败: {e}")
                    error_msg = str(e)
            else:
                is_valid = True

            if is_valid:
                yield {
                    "is_task_complete": True,
                    "content": final_content,
                }
                return

            if attempt <= max_retries:
                current_query = f"上次响应格式错误: {error_msg}。请重新生成: {query}"

        yield {
            "is_task_complete": True,
            "content": "抱歉，生成界面失败，请稍后重试。",
        }
