# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
from prompt_builder import (
    get_text_prompt,
    ROLE_DESCRIPTION,
    WORKFLOW_DESCRIPTION,
    UI_DESCRIPTION,
)
from tools import get_restaurants
from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

logger = logging.getLogger(__name__)


class RestaurantAgent:
  """An agent that finds restaurants based on user criteria."""

  SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

  def __init__(self, base_url: str, use_ui: bool = False):
    self.base_url = base_url
    self.use_ui = use_ui
    self._schema_manager = (
        A2uiSchemaManager(
            "0.8",
            basic_examples_path="examples/",
            schema_modifiers=[remove_strict_validation],
        )
        if use_ui
        else None
    )
    self._agent = self._build_agent(use_ui)
    print(self._agent)
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
        extensions=[self._schema_manager.get_agent_extension()],
    )
    skill = AgentSkill(
        id="find_restaurants",
        name="餐厅搜索工具",
        description=(
            "根据用户条件（如菜系、地点）帮助查找餐厅。"
        ),
        tags=["restaurant", "finder"],
        examples=["查找前10家中餐馆", "找一些意大利餐厅"],
    )
    # skill=AgentSkill(
    #   id="查询员工",
    #   name="员工查询工具",
    #   description=(
    #         "根据用户条件（如姓名、部门）帮助查询员工信息。"
    #     ),
    #   tags=["employee", "lookup"],
    #   examples=["查询张三的信息", "找所有销售部门的员工"],
    # )
    # return AgentCard(
    #   name="查询员工",
    #   description="根据用户条件帮助查询员工信息。",
    #   url=self.base_url,
    #   version="1.0.0",
    #   default_input_modes=RestaurantAgent.SUPPORTED_CONTENT_TYPES,
    #   default_output_modes=RestaurantAgent.SUPPORTED_CONTENT_TYPES,
    #   capabilities=capabilities,
    #   skills=[skill],
    # )

    return AgentCard(
        name="餐厅助手",
        description="根据用户条件帮助查找餐厅并预订桌位。",
        url=self.base_url,
        version="1.0.0",
        default_input_modes=RestaurantAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=RestaurantAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )

  def get_processing_message(self) -> str:
    return "正在搜索符合条件的餐厅..."

  def _build_agent(self, use_ui: bool) -> LlmAgent:
    """Builds the LLM agent for the restaurant agent."""
    # LITELLM_MODEL = os.getenv("LITELLM_MODEL", "gemini/gemini-2.5-flash")
    #切换为qwen模型
    LITELLM_MODEL = os.getenv("LITELLM_MODEL", "dashscope/qwen-turbo")

    instruction = (
        self._schema_manager.generate_system_prompt(
            role_description=ROLE_DESCRIPTION,
            workflow_description=WORKFLOW_DESCRIPTION,
            ui_description=UI_DESCRIPTION,
            include_schema=True,
            include_examples=True,
            validate_examples=True,
        )
        if use_ui
        else get_text_prompt()
    )
    logger.info(f"提示词: {instruction}")

    return LlmAgent(
        model=LiteLlm(model=LITELLM_MODEL),
        name="restaurant_agent",
        description="An agent that finds restaurants and helps book tables.",
        instruction=instruction,
        tools=[get_restaurants],
    )

  async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
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

    # --- Begin: UI Validation and Retry Logic ---
    max_retries = 1  # Total 2 attempts
    attempt = 0
    current_query_text = query

    # Ensure schema was loaded
    selected_catalog = self._schema_manager.get_selected_catalog()
    if self.use_ui and not selected_catalog.catalog_schema:
      logger.error(
          "--- RestaurantAgent.stream: A2UI Schema 未加载。无法执行 UI 验证。 ---"
      )
      yield {
          "is_task_complete": True,
          "content": (
              "抱歉，我遇到了 UI 组件内部配置错误，请联系技术支持。"
          ),
      }
      return

    while attempt <= max_retries:
      attempt += 1
      logger.info(
          f"--- RestaurantAgent.stream: 第 {attempt}/{max_retries + 1} 次尝试，session: {session_id} ---"
      )

      current_message = types.Content(
          role="user", parts=[types.Part.from_text(text=current_query_text)]
      )
      final_response_content = None
      print('当前的current_message:',current_message)

      async for event in self._runner.run_async(
          user_id=self._user_id,
          session_id=session.id,
          new_message=current_message,
      ):
        logger.info(f"Event from runner: {event}")
        if event.is_final_response():
          if event.content and event.content.parts and event.content.parts[0].text:
            final_response_content = "\n".join(
                [p.text for p in event.content.parts if p.text]
            )
          break  # Got the final response, stop consuming events
        else:
          logger.info(f"Intermediate event: {event}")
          # Yield intermediate updates on every attempt
          yield {
              "is_task_complete": False,
              "updates": self.get_processing_message(),
          }

      if final_response_content is None:
        logger.warning(
            "--- RestaurantAgent.stream: Runner 未返回最终响应内容 (第 {attempt} 次尝试)。 ---".format(attempt=attempt)
        )
        if attempt <= max_retries:
          current_query_text = (
              "未收到响应，请重试。请重新处理原始请求: '{query}'".format(query=query)
          )
          continue  # Go to next retry
        else:
          # Retries exhausted on no-response
          final_response_content = (
              "抱歉，遇到错误无法处理您的请求。"
          )
          # Fall through to send this as a text-only error

      is_valid = False
      error_message = ""

      if self.use_ui:
        logger.info(
            "--- RestaurantAgent.stream: 验证 UI 响应 (第 {attempt} 次尝试)... ---".format(attempt=attempt)
        )
        try:
          if "---a2ui_JSON---" not in final_response_content:
            raise ValueError("Delimiter '---a2ui_JSON---' not found.")

          text_part, json_string = final_response_content.split("---a2ui_JSON---", 1)

          if not json_string.strip():
            raise ValueError("JSON part is empty.")

          json_string_cleaned = (
              json_string.replace("---a2ui_JSON---", "").strip().lstrip("```json").rstrip("```").strip()
          )

          if not json_string_cleaned:
            raise ValueError("Cleaned JSON string is empty.")

          # --- 验证步骤 ---
          # 1. 检查是否是可解析的 JSON
          parsed_json_data = json.loads(json_string_cleaned)

          # 2. 检查是否符合 A2UI Schema
          # 如果不符合会抛出 jsonschema.exceptions.ValidationError
          logger.info(
              "--- RestaurantAgent.stream: 正在验证 A2UI Schema... ---"
          )
          try:
            selected_catalog.validator.validate(parsed_json_data)
          except jsonschema.exceptions.ValidationError as ve:
            logger.warning(f"--- Schema 验证详细错误: {ve.message} ---")
            logger.warning(f"--- 失败的路径: {list(ve.absolute_path)} ---")
            logger.warning(f"--- 失败的值: {ve.instance} ---")
            raise ve
          # --- End New Validation Steps ---

          logger.info(
              "--- RestaurantAgent.stream: UI JSON 解析成功且通过 Schema 验证。验证通过 (第 {attempt} 次尝试)。 ---".format(attempt=attempt)
          )
          is_valid = True

        except (
            ValueError,
            json.JSONDecodeError,
            jsonschema.exceptions.ValidationError,
        ) as e:
          logger.warning(
              "--- RestaurantAgent.stream: A2UI 验证失败: {error} (第 {attempt} 次尝试) ---".format(error=e, attempt=attempt)
          )
          logger.warning(
              "--- 失败的响应内容: {content}... ---".format(content=final_response_content[:500])
          )
          error_message = "验证失败: {error}".format(error=e)

      else:  # Not using UI, so text is always "valid"
        is_valid = True

      if is_valid:
        logger.info(
            "--- RestaurantAgent.stream: 响应验证通过。发送最终响应 (第 {attempt} 次尝试)。 ---".format(attempt=attempt)
        )
        logger.info(f"Final response: {final_response_content}")
        yield {
            "is_task_complete": True,
            "content": final_response_content,
        }
        return  # We're done, exit the generator

      # --- If we're here, it means validation failed ---

      if attempt <= max_retries:
        logger.warning(
            f"--- RestaurantAgent.stream: 正在重试... ({attempt}/{max_retries + 1}) ---"
        )
        # Prepare the query for the retry
        current_query_text = (
            f"你之前的响应格式无效。错误信息: {error_message}\n\n"
            f"你之前生成的内容:\n{final_response_content}\n\n"
            "请修正上述错误，重新生成符合 A2UI JSON Schema 的有效响应。\n"
            "注意：\n"
            "1. 必须使用 '---a2ui_JSON---' 分隔符分隔文本和 JSON\n"
            "2. JSON 必须是有效的 A2UI 消息数组\n"
            "3. 每个消息只能包含一个动作属性(beginRendering/surfaceUpdate/dataModelUpdate/deleteSurface)\n"
            "4. 生成的 JSON 必须能通过 Schema 验证\n"
            f"\n请重新处理原始请求: '{query}'"
        )
        # Loop continues...

    # --- If we're here, it means we've exhausted retries ---
    logger.error(
        "--- RestaurantAgent.stream: 重试次数耗尽，发送纯文本错误信息。 ---"
    )
    yield {
        "is_task_complete": True,
        "content": (
            "抱歉，当前生成界面时遇到问题，请稍后重试。"
        ),
    }
    # --- End: UI Validation and Retry Logic ---
