"""
General Query Agent - 通用查询 Agent 主模块

这个模块实现了通用数据查询 Agent 的核心逻辑，包括：
1. Agent 初始化和配置
2. 与 LLM 的交互
3. A2UI JSON 的生成和验证
"""

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
from tools import get_data
from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

logger = logging.getLogger(__name__)


class GeneralQueryAgent:
    """
    通用数据查询 Agent
    
    功能：
    - 根据用户查询返回相应的 UI 界面
    - 支持多种数据类型（人员、菜品、IT产品等）
    - 支持闲聊和问候
    
    属性：
        SUPPORTED_CONTENT_TYPES: 支持的内容类型
        base_url: Agent 的基础 URL
        use_ui: 是否使用 UI 模式
        _schema_manager: A2UI Schema 管理器
        _agent: LLM Agent 实例
        _user_id: 用户 ID
        _runner: Agent 运行器
    """

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, base_url: str, use_ui: bool = False):
        """
        初始化 Agent
        
        Args:
            base_url: Agent 的基础 URL，用于生成 Agent Card
            use_ui: 是否使用 UI 模式，True 则生成 A2UI 界面，False 则返回纯文本
        """
        self.base_url = base_url
        self.use_ui = use_ui
        
        # 初始化 Schema 管理器（仅 UI 模式需要）
        # Schema 管理器负责：
        # 1. 加载组件库定义
        # 2. 生成包含组件规范的 Prompt
        # 3. 验证生成的 A2UI JSON
        if use_ui:
            self._schema_manager = A2uiSchemaManager(
                "0.8",  # A2UI 版本
                basic_examples_path="../general_query/examples/",  # 示例文件路径
                schema_modifiers=[remove_strict_validation],  # 移除严格验证
            )
        else:
            self._schema_manager = None
        
        # 构建 LLM Agent
        self._agent = self._build_agent()
        self._user_id = "remote_agent"
        
        # 初始化 Runner（负责运行 Agent）
        # Runner 需要：
        # - artifact_service: 用于存储文件等资源
        # - session_service: 用于管理会话状态
        logger.info(f"agent name: {self._agent.name}")
        # - memory_service: 用于管理对话记忆
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_agent_card(self) -> AgentCard:
        """
        获取 Agent Card（Agent 能力卡片）
        
        Agent Card 用于向 A2A 协议客户端描述这个 Agent 的能力，
        包括：
        - Agent 名称和描述
        - 支持的能力（如 streaming, extensions）
        - 技能列表（用于搜索和匹配）
        
        Returns:
            AgentCard: Agent 能力卡片
        """
        # 定义 Agent 能力
        capabilities = AgentCapabilities(
            streaming=True,  # 支持流式响应
            # 如果使用 UI 模式，添加 A2UI 扩展
            # 扩展中包含 supportedCatalogIds，告诉前端支持哪些组件库
            extensions=[self._schema_manager.get_agent_extension()] if self.use_ui and self._schema_manager else [],
        )
        
        # 定义 Agent 技能
        # 技能用于描述 Agent 能做什么，帮助用户了解如何使用
        skill = AgentSkill(
            id="general_query",
            name="通用查询",
            description="根据用户查询返回相应的数据展示界面",
            tags=["query", "search", "data"],
            examples=["查询员工", " 查看菜品", "搜索人员", "查询生日"],
        )
        
        # 返回 Agent Card
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

    def _build_agent(self) -> LlmAgent:
        """
        构建 LLM Agent
        
        LLM Agent 是与语言模型交互的核心组件，负责：
        1. 接收用户输入
        2. 调用 LLM 生成响应
        3. 执行工具调用
        
        Returns:
            LlmAgent: 配置好的 LLM Agent 实例
        """
        # 从环境变量获取模型配置
        # 默认使用阿里云的 qwen-turbo 模型
        LITELLM_MODEL = os.getenv("LITELLM_MODEL", "dashscope/qwen-turbo")

        # 获取提示词
        # UI 模式使用包含组件规范的完整提示词
        # 文本模式使用简单的文本提示词
        instruction = get_ui_prompt() if self.use_ui else get_text_prompt()
        logger.info(f"提示词: {instruction[:200]}...")

        # 创建 LLM Agent
        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),  # 使用 LiteLlm 包装模型
            name="general_query_agent",
            description="通用AI助手",
            instruction=instruction,  # 系统提示词
            tools=[get_data],  # 可用的工具列表
        )

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """
        流式处理用户查询
        
        这是 Agent 的主要入口方法，负责：
        1. 获取或创建会话
        2. 调用 LLM 生成响应
        3. 验证和修复 A2UI JSON
        4. 返回结果
        
        Args:
            query: 用户查询内容
            session_id: 会话 ID，用于保持对话上下文
            
        Yields:
            dict: 包含响应状态的字典
                - is_task_complete: 任务是否完成
                - updates: 进度更新消息
                - content: 最终响应内容
        """
        logger.info(f"=== 入参 ===")
        logger.info(f"  query: {query}")
        logger.info(f"  session_id: {session_id}")
        
        # 获取或创建会话
        # 会话用于保持对话上下文和状态
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={"base_url": self.base_url},
                session_id=session_id,
            )

        # 构建消息
        # 消息包含用户角色和内容
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)],
        )
        
        logger.info(f"=== 模型入参 message ===")
        logger.info(f"  role: user")
        logger.info(f"  text: {query}")

        # 运行 Agent 并收集响应
        final_content = None
        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=message,
        ):
            # 检查是否为最终响应
            if event.is_final_response():
                # 提取文本内容
                final_content = "\n".join(p.text for p in event.content.parts if p.text)
                break
            else:
                # 返回进度更新
                yield {"is_task_complete": False, "updates": "正在查询数据..."}

        # 检查是否有响应
        if final_content is None:
            yield {"is_task_complete": True, "content": "抱歉，查询失败，请稍后重试。"}
            return

        logger.info(f"=== 模型返回结果 ===")
        logger.info(f"  content: {final_content[:500]}..." if len(final_content) > 500 else f"  content: {final_content}")

        # 验证和修复 A2UI JSON（仅 UI 模式）
        if self.use_ui and self._schema_manager:
            final_content = self._validate_and_fix_json(final_content)

        yield {"is_task_complete": True, "content": final_content}

    def _validate_and_fix_json(self, content: str) -> str:
        """
        验证和修复 A2UI JSON
        
        这个方法负责：
        1. 提取 JSON 部分（使用分隔符 ---a2ui_JSON---）
        2. 解析 JSON
        3. 验证 JSON 是否符合 A2UI Schema
        4. 尝试修复常见的 JSON 错误
        
        Args:
            content: LLM 生成的原始响应内容
            
        Returns:
            str: 验证后的内容（可能已修复）
        """
        # 检查分隔符
        if "---a2ui_JSON---" not in content:
            logger.warning("缺少分隔符 ---a2ui_JSON---")
            return content

        # 分离文本和 JSON 部分
        text_part, json_part = content.split("---a2ui_JSON---", 1)
        json_str = json_part.strip().lstrip("```json").rstrip("```").strip()

        # 空 JSON 直接返回
        if not json_str or json_str == "[]":
            return content

        # 尝试解析 JSON
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            # 尝试修复：删除错误位置的字符
            try:
                json_str = json_str[:e.pos] + json_str[e.pos+1:]
                parsed = json.loads(json_str)
            except:
                # 尝试修复：移除控制字符
                try:
                    import re
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
                    parsed = json.loads(json_str)
                except:
                    return content

        # 验证 JSON 是否符合 A2UI Schema
        try:
            catalog = self._schema_manager.get_selected_catalog()
            if catalog and catalog.validator:
                catalog.validator.validate(parsed)
        except jsonschema.exceptions.ValidationError as e:
            logger.warning(f"JSON 验证失败: {e}")
            return content

        return content
