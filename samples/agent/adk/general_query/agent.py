"""
General Query Agent - 通用查询 Agent 主模块

这个模块实现了通用数据查询 Agent 的核心逻辑，包括：
1. Agent 初始化和配置
2. 与 LLM 的交互
3. A2UI JSON 的生成和验证

处理流程：
1. 先获取 tools 的数据
2. 根据用户问题和数据判断是否需要 UI 展示
3. 如果不需要 UI 展示，直接以固定 A2UI 文本格式返回
4. 如果需要 UI 展示，才调用大模型生成 A2UI
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
from tools import get_data, query_data
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
        if use_ui:
            self._schema_manager = A2uiSchemaManager(
                "0.8",
                schema_modifiers=[remove_strict_validation],
            )
        else:
            self._schema_manager = None
        
        # 构建 LLM Agent
        self._agent = self._build_agent()
        self._user_id = "remote_agent"
        
        # 初始化 Runner
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
        
        Returns:
            AgentCard: Agent 能力卡片
        """
        capabilities = AgentCapabilities(
            streaming=True,
            extensions=[self._schema_manager.get_agent_extension()] if self.use_ui and self._schema_manager else [],
        )
        
        skill = AgentSkill(
            id="general_query",
            name="通用查询",
            description="根据用户查询返回相应的数据展示界面",
            tags=["query", "search", "data"],
            examples=["查询员工", "查看菜品", "搜索人员", "查询生日"],
        )
        
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
        
        Returns:
            LlmAgent: 配置好的 LLM Agent 实例
        """
        LITELLM_MODEL = os.getenv("LITELLM_MODEL", "dashscope/qwen-turbo")

        instruction = get_ui_prompt() if self.use_ui else get_text_prompt()
        logger.info(f"提示词: {instruction[:200]}...")

        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name="general_query_agent",
            description="通用AI助手",
            instruction=instruction,
            tools=[get_data],
        )

    def _extract_json_from_text(self, text: str) -> list | None:
        """
        从文本中提取 JSON 数据
        
        Args:
            text: 用户输入文本
            
        Returns:
            list | None: 提取的 JSON 数据（统一返回列表），如果没有则返回 None
        """
        # 尝试匹配 JSON 数组 [{...}, {...}]
        brace_count = 0
        bracket_count = 0
        start_idx = -1
        in_array = False
        
        for i, char in enumerate(text):
            if char == '[':
                if bracket_count == 0 and brace_count == 0:
                    start_idx = i
                    in_array = True
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0 and in_array and start_idx >= 0:
                    json_str = text[start_idx:i+1]
                    try:
                        data = json.loads(json_str)
                        if isinstance(data, list) and len(data) > 0:
                            return data
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1
                    in_array = False
            elif char == '{' and not in_array:
                brace_count += 1
            elif char == '}' and not in_array:
                brace_count -= 1
        
        # 尝试匹配单个 JSON 对象 {...}
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx >= 0:
                    json_str = text[start_idx:i+1]
                    try:
                        data = json.loads(json_str)
                        if isinstance(data, dict) and len(data) > 0:
                            # 检查是否包含数据字段（排除场景分类的 JSON）
                            data_keys = set(data.keys())
                            if not data_keys.issubset({'scene_type', 'scene_data'}):
                                # 单个对象转换为列表
                                return [data]
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1
        
        return None

    def _get_data_directly(self, query: str) -> list:
        """
        直接获取数据（不通过 LLM 工具调用）
        
        Args:
            query: 用户查询
            
        Returns:
            list: 查询结果
        """
        try:
            script_dir = os.path.dirname(__file__)
            file_path = os.path.join(script_dir, "data.json")
            
            with open(file_path, "r", encoding="utf-8") as f:
                all_data = json.load(f)
            
            return query_data(all_data, query)
            
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return []

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """
        流式处理用户查询
        
        处理流程：
        1. 检查用户输入是否包含 JSON 数据 → 提取数据，调用 LLM 生成 UI
        2. 调用 LLM 判断场景类型
        3. 场景1（闲聊）→ 直接返回固定文本 A2UI
        4. 场景2（需要查询数据）→ 获取数据，调用 LLM 生成 UI
        5. 场景3（纯文本）→ 直接返回固定文本 A2UI
        
        Args:
            query: 用户查询内容
            session_id: 会话 ID
            
        Yields:
            dict: 包含响应状态的字典
        """
        logger.info(f"=== 入参 ===")
        logger.info(f"  query: {query}")
        logger.info(f"  session_id: {session_id}")
        
        # 步骤 1：检查用户输入是否包含 JSON 数据
        embedded_data = self._extract_json_from_text(query)
        if embedded_data:
            logger.info(f"=== 检测到用户输入包含 JSON 数据，共 {len(embedded_data)} 条 ===")
            async for result in self._generate_ui_with_data(query, embedded_data, session_id):
                yield result
            return
        
        # 步骤 2：调用 LLM 判断场景类型
        logger.info("=== 步骤 2：调用 LLM 判断场景类型 ===")
        yield {"is_task_complete": False, "updates": "正在分析请求..."}
        
        scene_type, scene_data = await self._classify_scene_with_llm(query)
        logger.info(f"  场景类型: {scene_type}")
        
        # 步骤 3：根据场景类型处理
        if scene_type == "data_query":
            # 场景1：需要查询数据 → 获取数据，调用 LLM 生成 UI
            logger.info("=== 场景1：需要查询数据 ===")
            yield {"is_task_complete": False, "updates": "正在查询数据..."}
            
            data = self._get_data_directly(query)
            logger.info(f"  获取数据结果: {len(data)} 条")
            
            if not data:
                # 数据为空，生成空数据提示 UI
                logger.info("=== 数据为空，生成提示 UI ===")
                async for result in self._generate_ui_without_data(query, "没有找到相关数据", session_id):
                    yield result
                return
            
            # 有数据，调用 LLM 生成 UI
            async for result in self._generate_ui_with_data(query, data, session_id):
                yield result
            return
        
        else:
            # 场景2：需要生成 UI 组件 → 直接调用 LLM 生成 UI
            logger.info("=== 场景2：需要生成 UI 组件 ===")
            async for result in self._generate_ui_without_data(query, scene_data, session_id):
                yield result
            return

    async def _generate_ui_without_data(self, query: str, ui_description: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """
        使用 LLM 生成 UI（不需要数据查询）
        
        Args:
            query: 用户查询
            ui_description: UI 类型描述
            session_id: 会话 ID
            
        Yields:
            dict: 包含响应状态的字典
        """
        logger.info("=== 调用 LLM 生成 UI（无数据）===")
        
        # 获取或创建会话
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

        # 构建提示
        if ui_description and "没有找到" in ui_description:
            current_query = f"""用户请求：{query}

说明：{ui_description}

请生成一个提示界面，显示"没有找到相关数据"的信息。"""
        else:
            current_query = f"""用户请求：{query}

UI 类型：{ui_description if ui_description else "根据用户请求生成合适的UI界面"}

请生成相应的 A2UI 界面。"""

        # 重试机制
        max_retries = 2
        attempt = 0

        while attempt <= max_retries:
            attempt += 1
            logger.info(f"--- 第 {attempt}/{max_retries + 1} 次尝试 ---")

            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=current_query)],
            )
            
            logger.info(f"=== 模型入参 ===")
            logger.info(f"  query 长度: {len(current_query)}")

            # 运行 Agent
            final_content = None
            async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                new_message=message,
            ):
                if event.is_final_response():
                    final_content = "\n".join(p.text for p in event.content.parts if p.text)
                    break
                else:
                    yield {"is_task_complete": False, "updates": "正在生成界面..."}

            if final_content is None:
                if attempt <= max_retries:
                    current_query = f"生成失败，请重试。{current_query}"
                    continue
                else:
                    yield {"is_task_complete": True, "content": "抱歉，生成界面失败，请稍后重试。"}
                    return

            logger.info(f"=== 模型返回结果 ===")
            logger.info(f"  content: {final_content}..." if len(final_content) > 500 else f"  content: {final_content}")

            # 验证 A2UI JSON
            is_valid = True
            error_msg = ""
            cleaned_content = final_content
            if self.use_ui and self._schema_manager:
                is_valid, cleaned_content, error_msg = self._validate_and_clean_a2ui_json(final_content)
            
            if is_valid:
                yield {"is_task_complete": True, "content": cleaned_content}
                return
            
            # 验证失败，准备重试
            if attempt <= max_retries:
                logger.warning(f"验证失败: {error_msg}，准备重试...")
                current_query = f"""上次响应格式错误: {error_msg}

请重新生成。{current_query}"""
            else:
                logger.error(f"验证失败且已达到最大重试次数: {error_msg}")
                yield {"is_task_complete": True, "content": f"抱歉，生成界面失败: {error_msg}"}
                return

    async def _classify_scene_with_llm(self, query: str) -> tuple[str, str]:
        """
        使用 LLM 判断场景类型
        
        Args:
            query: 用户查询
            
        Returns:
            tuple[str, str]: (场景类型, 场景数据)
                - 场景类型: "data_query" | "ui_generation"
                - 场景数据: 对于 ui_generation 场景，返回要生成的 UI 类型描述
        """
        classify_prompt = f"""请判断以下用户输入属于哪种场景：

用户输入：{query}

场景类型：
1. data_query - 需要查询已有数据（如：查询员工、查看菜品、搜索人员）
2. ui_generation - 需要生成 UI 组件（如：生成一个性别选择器、创建一个输入框、显示一个日期选择器）

请只返回一个 JSON 对象，格式如下：
{{"scene_type": "场景类型", "scene_data": "对于ui_generation场景，返回要生成的UI类型描述；其他场景返回空字符串"}}

示例：
- 用户输入"查询员工" → {{"scene_type": "data_query", "scene_data": ""}}
- 用户输入"生成一个日期选择器" → {{"scene_type": "ui_generation", "scene_data": "日期选择器，使用DatePicker组件"}}
- 用户输入"创建一个输入框" → {{"scene_type": "ui_generation", "scene_data": "文本输入框，使用TextField组件"}}
"""

        try:
            # 创建临时 session 用于场景分类
            classify_session_id = f"classify_{abs(hash(query)) % 1000000}"
            
            session = await self._runner.session_service.get_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=classify_session_id,
            )
            if session is None:
                session = await self._runner.session_service.create_session(
                    app_name=self._agent.name,
                    user_id=self._user_id,
                    session_id=classify_session_id,
                )
            
            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=classify_prompt)],
            )
            
            final_response = None
            async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                new_message=message,
            ):
                if event.is_final_response():
                    final_response = "\n".join(p.text for p in event.content.parts if p.text)
                    break
            
            if final_response:
                # 解析 JSON
                import re
                json_match = re.search(r'\{[^{}]*\}', final_response)
                if json_match:
                    result = json.loads(json_match.group())
                    return result.get("scene_type", "ui_generation"), result.get("scene_data", "")
        
        except Exception as e:
            logger.error(f"场景分类失败: {e}")
        
        # 默认返回 UI 生成场景
        return "ui_generation", ""

    async def _generate_ui_with_data(self, query: str, data: list, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """
        使用 LLM 根据数据生成 UI
        
        Args:
            query: 用户查询
            data: 数据列表
            session_id: 会话 ID
            
        Yields:
            dict: 包含响应状态的字典
        """
        logger.info("=== 调用 LLM 生成 UI ===")
        
        # 获取或创建会话
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

        # 重试机制
        max_retries = 1
        attempt = 0
        current_query = f"""用户查询：{query}

            已获取的数据（共 {len(data)} 条）：
            {json.dumps(data, ensure_ascii=False, indent=2)}

            请根据以上数据生成 A2UI 界面展示。"""

        while attempt <= max_retries:
            attempt += 1
            logger.info(f"--- 第 {attempt}/{max_retries + 1} 次尝试 ---")

            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=current_query)],
            )
            
            logger.info(f"=== 模型入参 ===")
            logger.info(f"  query 长度: {len(current_query)}")
            logger.info(f"  message: {message}")

            # 运行 Agent
            final_content = None
            async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                new_message=message,
            ):
                if event.is_final_response():
                    final_content = "\n".join(p.text for p in event.content.parts if p.text)
                    break
                else:
                    yield {"is_task_complete": False, "updates": "正在生成界面..."}

            if final_content is None:
                if attempt <= max_retries:
                    current_query = f"生成失败，请重试。{current_query}"
                    continue
                else:
                    yield {"is_task_complete": True, "content": "抱歉，生成界面失败，请稍后重试。"}
                    return

            logger.info(f"=== 模型返回结果 ===")
            logger.info(f"  content: {final_content}..." if len(final_content) > 500 else f"  content: {final_content}")

            # 验证 A2UI JSON
            is_valid = True
            error_msg = ""
            cleaned_content = final_content
            if self.use_ui and self._schema_manager:
                is_valid, cleaned_content, error_msg = self._validate_and_clean_a2ui_json(final_content)
            
            if is_valid:
                yield {"is_task_complete": True, "content": cleaned_content}
                return
            
            # 验证失败，准备重试
            if attempt <= max_retries:
                logger.warning(f"验证失败: {error_msg}，准备重试...")
                current_query = f"""上次响应格式错误: {error_msg}

请重新生成。{current_query}"""
            else:
                logger.error(f"验证失败且已达到最大重试次数: {error_msg}")
                yield {"is_task_complete": True, "content": f"抱歉，生成界面失败: {error_msg}"}
                return

    def _validate_and_clean_a2ui_json(self, content: str) -> tuple[bool, str, str]:
        """
        验证并清理 A2UI JSON
        
        Args:
            content: LLM 生成的原始响应内容
            
        Returns:
            tuple[bool, str, str]: (是否有效, 清理后的内容, 错误信息)
        """
        if "---a2ui_JSON---" not in content:
            return False, content, "缺少分隔符 ---a2ui_JSON---"

        # 分割内容，取第一个 JSON 部分
        parts = content.split("---a2ui_JSON---")
        if len(parts) < 2:
            return False, content, "缺少 JSON 内容"
        
        # 取文本部分和第一个 JSON 部分
        text_part = parts[0].strip()
        json_part = parts[1].strip()
        
        # 如果有第二个分隔符，截取到那里
        if "---a2ui_JSON---" in json_part:
            json_part = json_part.split("---a2ui_JSON---")[0].strip()
        
        # 移除可能的 markdown 代码块标记
        json_str = json_part.lstrip("```json").rstrip("```").strip()

        # 空数据，生成默认 UI
        if not json_str or json_str == "[]" or json_str == "{}":
            default_a2ui = self._generate_default_a2ui(text_part or "暂无数据")
            return True, default_a2ui, ""

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            logger.warning(f"JSON 内容: {json_str[:500]}...")
            return False, content, f"JSON 解析失败: {e}"

        # 先清理不允许的属性
        cleaned_parsed = self._remove_forbidden_props(parsed)
        logger.info(f"=== 清理后的 JSON ===")
        logger.info(f"  {json.dumps(cleaned_parsed, ensure_ascii=False)[:500]}...")

        # 尝试验证
        try:
            catalog = self._schema_manager.get_selected_catalog()
            if catalog and catalog.validator:
                catalog.validator.validate(cleaned_parsed)
        except (jsonschema.exceptions.ValidationError, ValueError) as e:
            logger.warning(f"JSON 验证失败: {e}")
            # 验证失败，生成默认 UI
            default_a2ui = self._generate_default_a2ui(text_part or "数据格式错误")
            return True, default_a2ui, ""

        # 返回清理后的内容
        cleaned_content = f"{text_part}---a2ui_JSON---{json.dumps(cleaned_parsed, ensure_ascii=False)}"
        return True, cleaned_content, ""

    def _remove_forbidden_props(self, data):
        """
        递归移除不允许的属性
        
        Args:
            data: JSON 数据
            
        Returns:
            清理后的数据
        """
        # 不允许的属性列表
        forbidden_props = {'fit', 'usageHint', 'OptionSelect', 'Input', 'TextInput'}
        
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if k in forbidden_props:
                    continue
                result[k] = self._remove_forbidden_props(v)
            return result
        elif isinstance(data, list):
            return [self._remove_forbidden_props(item) for item in data]
        else:
            return data

    def _generate_default_a2ui(self, text: str) -> str:
        """
        生成默认的 A2UI 响应
        
        Args:
            text: 要显示的文本
            
        Returns:
            str: 完整的 A2UI 响应
        """
        a2ui_json = [
            {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
            {"surfaceUpdate": {"surfaceId": "default", "components": [
                {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["text-component"]}}}},
                {"id": "text-component", "component": {"Text": {"text": {"literalString": text}}}}
            ]}},
            {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": []}}
        ]
        
        return f"{text}---a2ui_JSON---{json.dumps(a2ui_json, ensure_ascii=False)}"
