"""
General Query Agent Executor - Agent 执行器模块

这个模块负责处理前端请求，协调 Agent 执行，并返回结果。
主要功能：
1. 解析前端请求（文本、数据、用户操作）
2. 调用 Agent 处理请求
3. 构建返回结果（文本、A2UI JSON）
"""

import json
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part, Task, TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_parts_message, new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from a2ui.extension.a2ui_extension import create_a2ui_part, try_activate_a2ui_extension

from agent import GeneralQueryAgent

logger = logging.getLogger(__name__)


class GeneralQueryAgentExecutor(AgentExecutor):
    """
    Agent 执行器
    
    负责处理 A2A 协议请求，协调 Agent 执行，并返回结果。
    
    属性：
        ui_agent: UI 模式的 Agent（生成 A2UI 界面）
        text_agent: 文本模式的 Agent（返回纯文本）
    """

    def __init__(self, ui_agent: GeneralQueryAgent, text_agent: GeneralQueryAgent):
        """
        初始化执行器
        
        Args:
            ui_agent: UI 模式的 Agent
            text_agent: 文本模式的 Agent
        """
        self.ui_agent = ui_agent
        self.text_agent = text_agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        执行 Agent 请求
        
        这是 A2A 协议的主要入口方法，处理流程：
        1. 检查客户端是否支持 A2UI
        2. 提取用户查询
        3. 创建或获取任务
        4. 调用 Agent 处理
        5. 构建并返回结果
        
        Args:
            context: 请求上下文，包含请求信息和状态
            event_queue: 事件队列，用于发送响应和状态更新
        """
        logger.info(f"=== 前端请求入参 ===")
        logger.info(f"  requested_extensions: {context}")
        
        # 检查客户端是否支持 A2UI
        # 如果支持，使用 UI Agent；否则使用文本 Agent
        use_ui = try_activate_a2ui_extension(context)
        agent = self.ui_agent if use_ui else self.text_agent
        logger.info(f"  use_ui: {use_ui}")

        # 提取用户查询
        query = self._extract_query(context)
        logger.info(f"  query: {query}")

        # 创建或获取任务
        # 任务用于跟踪请求状态和进度
        task = context.current_task or new_task(context.message)
        await event_queue.enqueue_event(task)
        
        # 创建任务更新器，用于发送状态更新
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # 调用 Agent 处理请求
        async for item in agent.stream(query, task.context_id):
            # 检查任务是否完成
            if not item["is_task_complete"]:
                # 发送进度更新
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(item["updates"], task.context_id, task.id),
                )
                continue

            # 构建最终结果
            final_parts = self._build_final_parts(item["content"])
            
            logger.info(f"=== 返回结果 ===")
            for i, part in enumerate(final_parts):
                logger.info(f"  Part {i}: {type(part.root).__name__}")

            # 发送完成状态
            await updater.update_status(
                TaskState.completed,
                new_agent_parts_message(final_parts, task.context_id, task.id),
                final=True,
            )
            break

    def _extract_query(self, context: RequestContext) -> str:
        """
        从请求上下文中提取用户查询
        
        支持多种输入格式：
        1. 文本输入（TextPart）
        2. 用户操作（DataPart 中的 userAction）
        3. JSON 数据（DataPart 中的其他数据）
        
        Args:
            context: 请求上下文
            
        Returns:
            str: 提取的用户查询字符串
        """
        logger.info(f"=== _extract_query 开始 ===")
        
        # 检查是否有消息
        if not context.message or not context.message.parts:
            logger.info(f"  context.message 或 parts 为空，使用 get_user_input")
            return context.get_user_input() or ""

        # 遍历消息部分，提取查询
        for part in context.message.parts:
            logger.info(f"  part type: {type(part.root)}")
            
            # 处理文本输入
            if isinstance(part.root, TextPart):
                logger.info(f"  TextPart: {part.root.text}")
                return part.root.text
            
            # 处理数据输入
            elif isinstance(part.root, DataPart):
                data = part.root.data
                logger.info(f"  DataPart.data type: {type(data)}")
                logger.info(f"  DataPart.data keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
                logger.info(f"  DataPart.data: {json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else data}")
                
                # 处理字典数据
                if isinstance(data, dict):
                    # 检查是否为用户操作（如按钮点击）
                    if "userAction" in data:
                        ui_event_part = data["userAction"]
                        logger.info(f"  userAction type: {type(ui_event_part)}")
                        logger.info(f"  userAction: {json.dumps(ui_event_part, ensure_ascii=False) if isinstance(ui_event_part, dict) else ui_event_part}")
                        
                        # 获取 actionName 和 context
                        # 注意：前端使用 "name" 而不是 "actionName"
                        action_name = ui_event_part.get("name") or ui_event_part.get("actionName", "unknown")
                        action_context = ui_event_part.get("context", {})
                        
                        # 如果 actionName 为空或 None，尝试从其他字段获取
                        if not action_name or action_name == "unknown":
                            # 可能是直接的 context 数据
                            if action_context:
                                logger.info(f"  使用 context 作为数据: {action_context}")
                                return f"USER_PROVIDED_DATA: {json.dumps(action_context)}"
                            # 或者返回整个数据
                            logger.info(f"  使用整个 data 作为数据")
                            return f"USER_PROVIDED_DATA: {json.dumps(data)}"
                        
                        return f"User submitted: {action_name}, data: {action_context}"
                    
                    # 其他字典数据
                    return f"USER_PROVIDED_DATA: {json.dumps(data)}"
                
                # 处理列表数据
                elif isinstance(data, list):
                    logger.info(f"  DataPart.data is list, length: {len(data)}")
                    return f"USER_PROVIDED_DATA: {json.dumps(data)}"

        # 如果没有找到有效输入，使用默认方法
        logger.info(f"  没有找到有效输入，使用 get_user_input")
        return context.get_user_input() or ""

    def _build_final_parts(self, content: str) -> list[Part]:
        """
        构建最终返回的消息部分
        
        根据内容格式构建不同的消息部分：
        1. 包含 A2UI JSON：分离文本和 JSON，分别创建 TextPart 和 DataPart
        2. 纯文本：创建 TextPart
        
        Args:
            content: Agent 返回的内容
            
        Returns:
            list[Part]: 消息部分列表
        """
        parts = []

        # 检查是否包含 A2UI JSON
        if "---a2ui_JSON---" in content:
            # 分离文本和 JSON 部分
            text_content, json_string = content.split("---a2ui_JSON---", 1)

            # 添加文本部分（如果有）
            if text_content.strip():
                parts.append(Part(root=TextPart(text=text_content.strip())))

            # 解析并添加 JSON 部分
            json_data = self._parse_json(json_string)
            if json_data:
                # A2UI JSON 是数组，每个元素创建一个 DataPart
                if isinstance(json_data, list):
                    for message in json_data:
                        parts.append(create_a2ui_part(message))
                else:
                    parts.append(create_a2ui_part(json_data))
        else:
            # 纯文本内容
            parts.append(Part(root=TextPart(text=content.strip())))

        return parts

    def _parse_json(self, json_string: str) -> list | dict | None:
        """
        解析 JSON 字符串
        
        处理可能的格式问题：
        1. 移除 Markdown 代码块标记
        2. 处理解析错误
        
        Args:
            json_string: JSON 字符串
            
        Returns:
            list | dict | None: 解析后的 JSON 对象，失败返回 None
        """
        # 清理 JSON 字符串
        json_str = json_string.strip().lstrip("```json").rstrip("```").strip()
        
        # 空字符串返回 None
        if not json_str:
            return None

        # 尝试解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return None

    async def cancel(self, request: RequestContext, event_queue: EventQueue) -> Task | None:
        """
        取消任务
        
        当前实现不支持取消操作。
        
        Args:
            request: 请求上下文
            event_queue: 事件队列
            
        Raises:
            ServerError: 总是抛出，表示不支持取消操作
        """
        raise ServerError(error=UnsupportedOperationError())
