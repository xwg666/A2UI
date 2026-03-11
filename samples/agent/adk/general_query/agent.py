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
import re
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
    get_ui_prompt,
    get_text_prompt,
    get_check_params_prompt,
    get_form_generation_prompt,
)
from tools import get_data, query_data
from test_demo import *
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
        DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

        instruction = get_ui_prompt() if self.use_ui else get_text_prompt()
        logger.info(f"提示词: {instruction[:200]}...")

        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name="general_query_agent",
            description="通用AI助手",
            instruction=instruction,
            tools=[get_data],
        )

    async def _check_missing_params_with_llm(self, query: str, session_id: str) -> tuple[bool, list[str]]:
        """
        使用大模型判断用户问题是否缺少必填参数
        
        Args:
            query: 用户输入文本
            session_id: 会话 ID
            
        Returns:
            tuple[bool, list[str]]: (是否缺少参数, 缺少的参数列表)
        """
        check_prompt = get_check_params_prompt(query)

        try:
            # 创建临时 session
            check_session_id = f"check_params_{abs(hash(query)) % 1000000}"
            
            session = await self._runner.session_service.get_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=check_session_id,
            )
            if session is None:
                session = await self._runner.session_service.create_session(
                    app_name=self._agent.name,
                    user_id=self._user_id,
                    session_id=check_session_id,
                )
            
            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=check_prompt)],
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
                json_match = re.search(r'\{[^}]+\}', final_response)
                if json_match:
                    result = json.loads(json_match.group())
                    need_more = result.get("need_more_info", False)
                    missing = result.get("missing_params", [])
                    logger.info(f"  LLM 判断结果: need_more_info={need_more}, missing_params={missing}")
                    return need_more, missing
        except Exception as e:
            logger.warning(f"  LLM 判断参数失败: {e}")
        
        return False, []

    async def _generate_form_ui_with_llm(self, query: str, required_params: list[str], session_id: str, filled_data: dict = None) -> AsyncIterable[dict[str, Any]]:
        """
        使用大模型生成表单 UI 让用户填写必填参数
        
        Args:
            query: 用户原始查询
            required_params: 所有必填参数列表
            session_id: 会话 ID
            filled_data: 已填写的参数值（可选）
            
        Yields:
            dict: 包含响应状态的字典
        """
        if filled_data is None:
            filled_data = {}
            
        # 计算未填写的参数
        missing_params = [p for p in required_params if not filled_data.get(p) or not str(filled_data.get(p)).strip()]
        
        logger.info(f"=== 使用大模型生成表单 UI ===")
        logger.info(f"  所有必填参数: {required_params}")
        logger.info(f"  已填写: {filled_data}")
        logger.info(f"  未填写: {missing_params}")
        
        # 构建已填写参数的提示
        filled_info = ""
        if filled_data:
            filled_info = "\n已填写的参数（需要在表单中保留这些值）：\n"
            for param, value in filled_data.items():
                if value and str(value).strip():
                    filled_info += f"- {param}: {value}\n"
        
        # 判断是否是部分填写（需要提示）
        is_partial_fill = len(missing_params) > 0 and len(missing_params) < len(required_params)
        
        form_prompt = get_form_generation_prompt(query, required_params, filled_info)

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

        # 调用大模型生成表单
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=form_prompt)],
        )
        
        final_content = None
        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=message,
        ):
            if event.is_final_response():
                final_content = "\n".join(p.text for p in event.content.parts if p.text)
                break
        
        if final_content:
            logger.info(f"=== LLM 生成的表单 ===")
            logger.info(f"  {final_content[:500]}...")
            
            # 验证并清理 JSON
            is_valid, cleaned_content, error_msg = self._validate_and_clean_a2ui_json(final_content)
            if is_valid:
                yield {"is_task_complete": True, "content": cleaned_content}
                return
        
        # LLM 生成失败，使用默认表单
        logger.warning("  LLM 生成失败，使用默认表单")
        yield {"is_task_complete": True, "content": self._create_default_form(required_params, filled_data)}

    def _infer_required_params_from_query(self, query: str) -> list[str]:
        """
        从用户查询中提取必填参数
        
        从原始查询中提取 "必填参数：["name", "age"]" 格式
        
        Args:
            query: 用户查询字符串
            
        Returns:
            list[str]: 必填参数列表
        """
        # 匹配 "必填参数：[...]" 格式
        import re
        pattern = r'必填参数：\s*\[(.*?)\]'
        match = re.search(pattern, query)
        
        if match:
            params_str = match.group(1)
            # 提取参数名
            params = re.findall(r'"(\w+)"', params_str)
            if params:
                logger.info(f"  从查询中提取的必填参数: {params}")
                return params
        
        # 如果没有匹配到，默认返回空列表
        return []

    def _extract_required_params_from_context(self, query: str) -> list[str]:
        """
        从表单提交的 context 中提取必填参数列表
        
        表单提交时，context 中应该包含 _required_params 字段，记录所有必填参数
        
        Args:
            query: 用户查询字符串（包含表单提交数据）
            
        Returns:
            list[str]: 必填参数列表
        """
        import re
        
        # 尝试从 data 中提取 _required_params
        # 使用更宽松的正则，匹配 data: 后面的内容直到结束
        form_submit_match = re.search(r"data:\s*(\{.*\})", query, re.DOTALL)
        if form_submit_match:
            try:
                data_str = form_submit_match.group(1)
                # 处理 Python 的字典格式（单引号）
                # 先尝试直接解析
                try:
                    form_data = json.loads(data_str.replace("'", '"'))
                except json.JSONDecodeError:
                    # 如果失败，尝试使用 ast.literal_eval 解析 Python 字典
                    import ast
                    form_data = ast.literal_eval(data_str)
                
                # 检查是否有 _required_params 字段
                if "_required_params" in form_data:
                    params_str = form_data["_required_params"]
                    params = [p.strip() for p in params_str.split(",") if p.strip()]
                    logger.info(f"  从 context._required_params 提取: {params}")
                    return params
                
                # 如果没有 _required_params，从 data 的 keys 中推断（排除内部字段）
                params = [k for k in form_data.keys() if not k.startswith("_")]
                logger.info(f"  从 context data keys 推断: {params}")
                return params
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"  从 context 提取参数失败: {e}")
        
        return []

    def _create_default_form(self, required_params: list[str], filled_data: dict = None) -> str:
        """
        创建默认表单 UI（当大模型生成失败时使用）
        
        Args:
            required_params: 必填参数列表
            filled_data: 已填写的参数值（可选）
            
        Returns:
            str: 完整的 A2UI 响应
        """
        logger.info(f"=== 创建默认表单，参数: {required_params}，已填: {filled_data} ===")
        
        if filled_data is None:
            filled_data = {}
        
        # 根据参数名生成表单组件
        components = []
        form_fields = []
        
        # 标签名称映射
        param_labels = {
            "name": "姓名",
            "age": "年龄",
            "sex": "性别",
            "gender": "性别",
            "phone": "电话",
            "email": "邮箱",
        }
        
        for param in required_params:
            field_id = f"field-{param}"
            input_id = f"input-{param}"
            label_id = f"label-{param}"
            
            param_label = param_labels.get(param, param)
            # 获取已填写的值
            filled_value = filled_data.get(param, "")
            
            components.extend([
                {"id": field_id, "component": {"Column": {"children": {"explicitList": [label_id, input_id]}}}},
                {"id": label_id, "component": {"Text": {"text": {"literalString": f"请输入{param_label}："}}}},
                {"id": input_id, "component": {"TextField": {"value": {"path": f"/formData/{param}"}}}}
            ])
            form_fields.append(field_id)
        
        # 提交按钮 - context 需要是数组格式
        submit_id = "submit-button"
        button_text_id = "button-text"
        
        # 构建 context 数组：
        # 1. 每个字段对应一个 key-value
        # 2. 添加必填参数列表（用于后续验证）
        context_array = [{"key": param, "value": {"path": f"/formData/{param}"}} for param in required_params]
        # 添加必填参数列表标记
        context_array.append({"key": "_required_params", "value": {"literalString": ",".join(required_params)}})
        
        components.extend([
            {"id": submit_id, "component": {"Button": {"child": button_text_id, "action": {"name": "submit_form", "context": context_array}}}},
            {"id": button_text_id, "component": {"Text": {"text": {"literalString": "提交"}}}}
        ])
        
        # 构建 A2UI JSON
        a2ui_json = [
            {"beginRendering": {"surfaceId": "default", "root": "form-column"}},
            {"surfaceUpdate": {"surfaceId": "default", "components": [
                {"id": "form-column", "component": {"Column": {"children": {"explicitList": form_fields + [submit_id]}}}}
            ] + components}},
            {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [
                {"key": "formData", "valueMap": [
                    {"key": param, "valueString": filled_data.get(param, "")} for param in required_params
                ]}
            ]}}
        ]
        
        param_names = [param_labels.get(p, p) for p in required_params]
        text_content = f"请补充必填信息：{', '.join(param_names)}"
        return f"{text_content}---a2ui_JSON---{json.dumps(a2ui_json, ensure_ascii=False)}"

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
        
        # 检查是否是修改密码场景
        # if "修改密码" in query or "修改账户密码" in query or "改密码" in query:
        #     logger.info("=== 检测到修改密码场景，直接返回固定 A2UI ===")
        #     a2ui_json = json.dumps(CHANGE_PASSWORD_A2UI, ensure_ascii=False)
        #     yield {"is_task_complete": True, "content": f"请在下面的列表中勾选您需要修改密码的账号---a2ui_JSON---{a2ui_json}"}
        #     return
        # if '表格' in query:
        #     logger.info("=== 检测到表格场景，直接返回固定 A2UI ===")
        #     a2ui_json = json.dumps(table_result, ensure_ascii=False)
        #     yield {"is_task_complete": True, "content": f"请在下面的表格中查看数据---a2ui_JSON---{a2ui_json}"}
        #     return
        
        if '会议室预定' in query:
            logger.info("=== 检测到会议室预定场景，直接返回固定 A2UI ===")
            a2ui_json = json.dumps(meeting_result, ensure_ascii=False)
            yield {"is_task_complete": True, "content": f"请在下面的表单中填写会议室预定信息---a2ui_JSON---{a2ui_json}"}
            return
        # 检查是否需要生成必填参数表单
        # 两种情况需要处理：1. 包含"必填参数"标记  2. 表单提交（用户已填写部分参数）
        is_form_submit = "User submitted: submit_form" in query
        has_required_params_mark = '必填参数' in query
        
        if has_required_params_mark or is_form_submit:
            logger.info(f"=== 检测到必填参数场景（标记:{has_required_params_mark}, 表单提交:{is_form_submit}）===")
            yield {"is_task_complete": False, "updates": "正在分析请求..."}
            
            # 从查询中提取必填参数列表
            required_params = self._infer_required_params_from_query(query)
            logger.info(f"  提取的必填参数: {required_params}")
            
            # 如果是表单提交但没有提取到参数，尝试从 context 中提取
            if is_form_submit and not required_params:
                required_params = self._extract_required_params_from_context(query)
                logger.info(f"  从 context 提取的必填参数: {required_params}")
            
            if required_params:
                # 提取表单提交的数据（如果有）
                filled_data = {}
                form_submit_match = re.search(r"data:\s*(\{.*\})", query, re.DOTALL)
                
                if form_submit_match:
                    try:
                        data_str = form_submit_match.group(1)
                        # 处理 Python 的字典格式（单引号）
                        try:
                            filled_data = json.loads(data_str.replace("'", '"'))
                        except json.JSONDecodeError:
                            # 如果失败，尝试使用 ast.literal_eval 解析 Python 字典
                            import ast
                            filled_data = ast.literal_eval(data_str)
                        logger.info(f"  表单提交数据: {filled_data}")
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"  解析表单数据失败: {e}")
                
                # 清理表单数据（处理对象值的情况）
                cleaned_filled_data = {}
                for param in required_params:
                    value = filled_data.get(param, "")
                    # 如果值是字典或对象，说明是空的或未正确填写
                    if isinstance(value, dict):
                        # 尝试从字典中提取实际值（如 vals 字段）
                        if "vals" in value and value["vals"]:
                            # 如果有 vals 字段且不为空
                            vals = value["vals"]
                            if isinstance(vals, dict) and vals:
                                # 取第一个值
                                value = list(vals.values())[0] if vals else ""
                            else:
                                value = str(vals) if vals else ""
                        else:
                            value = ""
                    elif isinstance(value, str):
                        value = value.strip()
                    cleaned_filled_data[param] = value
                
                filled_data = cleaned_filled_data
                
                # 检查哪些参数已填写，哪些还未填写
                missing_params = []
                for param in required_params:
                    value = filled_data.get(param, "")
                    if not value:
                        missing_params.append(param)
                
                logger.info(f"  已填写参数: {filled_data}")
                logger.info(f"  未填写参数: {missing_params}")
                
                if missing_params:
                    # 有未填写的参数，生成表单（保留已填写的值）
                    logger.info(f"=== 缺少必填参数: {missing_params}，生成表单（保留已填值）===")
                    async for result in self._generate_form_ui_with_llm(
                        query, 
                        required_params,  # 传递所有必填参数
                        session_id,
                        filled_data  # 传递已填写的数据
                    ):
                        yield result
                    return
                else:
                    # 所有参数都已填写，构建查询继续处理
                    params_str = ", ".join([f"{k}={v}" for k, v in filled_data.items() if k in required_params])
                    new_query = f"查询 {params_str} 的信息"
                    logger.info(f"=== 所有必填参数已完整，转换为新查询: {new_query} ===")
                    query = new_query
            else:
                logger.info("=== 未提取到必填参数，继续正常处理 ===")
        
        
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
            # 尝试自动修复 JSON
            repaired = self._try_repair_json(json_str)
            if repaired:
                logger.info("JSON 自动修复成功")
                parsed = repaired
            else:
                return False, content, f"JSON 解析失败: {e}"

        # 先清理不允许的属性
        cleaned_parsed = self._remove_forbidden_props(parsed)
        logger.info(f"=== 清理后的 JSON ===")
        logger.info(f"  {json.dumps(cleaned_parsed, ensure_ascii=False)}")

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

    def _try_repair_json(self, json_str: str) -> list | None:
        """
        尝试自动修复损坏的 JSON

        Args:
            json_str: 损坏的 JSON 字符串

        Returns:
            修复后的 JSON 数据，如果修复失败则返回 None
        """
        import re

        # 尝试修复常见的 JSON 错误
        repaired = json_str

        # 1. 移除可能的前后空白和不可见字符
        repaired = repaired.strip()

        # 2. 移除 markdown 代码块标记
        repaired = re.sub(r'^```json\s*', '', repaired)
        repaired = re.sub(r'\s*```$', '', repaired)
        repaired = re.sub(r'^```\s*', '', repaired)

        # 3. 尝试找到有效的 JSON 数组范围
        # 找到第一个 [ 和最后一个 ]
        start_idx = repaired.find('[')
        end_idx = repaired.rfind(']')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            repaired = repaired[start_idx:end_idx+1]

        # 4. 尝试解析
        try:
            parsed = json.loads(repaired)
            return parsed
        except json.JSONDecodeError:
            pass

        # 5. 尝试更激进的修复：移除所有非 JSON 字符
        # 只保留 JSON 有效字符
        json_chars = set('{}[]",:0123456789+-.,eE true false null \t\n\r')
        cleaned = ''.join(c for c in repaired if c in json_chars or ord(c) < 128)

        try:
            parsed = json.loads(cleaned)
            return parsed
        except json.JSONDecodeError:
            pass

        return None

    def _remove_forbidden_props(self, data):
        """
        递归移除不允许的属性和组件
        
        Args:
            data: JSON 数据
            
        Returns:
            清理后的数据
        """
        # 不允许的属性列表
        forbidden_props = {'fit', 'usageHint', 'OptionSelect', 'Input', 'TextInput'}
        # 不允许的组件类型
        forbidden_components = {'FileUpload', 'VideoPlayer', 'AudioPlayer', 'WebFrame'}
        
        if isinstance(data, dict):
            # 检查是否是禁止的组件
            if 'component' in data:
                component_keys = set(data['component'].keys())
                if component_keys & forbidden_components:
                    # 替换为空的 Text 组件
                    return {"id": data.get('id', 'removed'), "component": {"Text": {"text": {"literalString": ""}}}}
            
            result = {}
            for k, v in data.items():
                if k in forbidden_props:
                    continue
                result[k] = self._remove_forbidden_props(v)
            return result
        elif isinstance(data, list):
            # 过滤掉包含禁止组件的列表项
            filtered = []
            for item in data:
                cleaned_item = self._remove_forbidden_props(item)
                # 如果清理后是空文本，则跳过
                if isinstance(cleaned_item, dict) and cleaned_item.get('component', {}).get('Text', {}).get('text', {}).get('literalString') == '':
                    continue
                filtered.append(cleaned_item)
            return filtered
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
