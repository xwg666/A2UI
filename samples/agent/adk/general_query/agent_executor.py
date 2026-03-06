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
    def __init__(self, ui_agent: GeneralQueryAgent, text_agent: GeneralQueryAgent):
        self.ui_agent = ui_agent
        self.text_agent = text_agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.info(f"=== 前端请求入参 ===")
        logger.info(f"  requested_extensions: {context.requested_extensions}")
        
        use_ui = try_activate_a2ui_extension(context)
        agent = self.ui_agent if use_ui else self.text_agent
        logger.info(f"  use_ui: {use_ui}")

        query = self._extract_query(context)
        logger.info(f"  query: {query}")

        task = context.current_task or new_task(context.message)
        await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        async for item in agent.stream(query, task.context_id):
            if not item["is_task_complete"]:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(item["updates"], task.context_id, task.id),
                )
                continue

            final_parts = self._build_final_parts(item["content"])
            
            logger.info(f"=== 返回结果 ===")
            for i, part in enumerate(final_parts):
                logger.info(f"  Part {i}: {type(part.root).__name__}")

            await updater.update_status(
                TaskState.completed,
                new_agent_parts_message(final_parts, task.context_id, task.id),
                final=True,
            )
            break

    def _extract_query(self, context: RequestContext) -> str:
        logger.info(f"=== _extract_query 开始 ===")
        
        if not context.message or not context.message.parts:
            logger.info(f"  context.message 或 parts 为空，使用 get_user_input")
            return context.get_user_input() or ""

        for part in context.message.parts:
            logger.info(f"  part type: {type(part.root)}")
            if isinstance(part.root, TextPart):
                logger.info(f"  TextPart: {part.root.text}")
                return part.root.text
            elif isinstance(part.root, DataPart):
                logger.info(f"  DataPart.data: {part.root.data}")
                if "userAction" in part.root.data:
                    ui_event_part = part.root.data["userAction"]
                    logger.info(f"  userAction: {ui_event_part}")
                    return f"User submitted: {ui_event_part.get('actionName')}, data: {ui_event_part.get('context', {})}"
                else:
                    data = part.root.data
                    if isinstance(data, dict):
                        return f"USER_PROVIDED_DATA: {json.dumps(data)}"
                    elif isinstance(data, list):
                        return f"USER_PROVIDED_DATA: {json.dumps(data)}"

        logger.info(f"  没有找到有效输入，使用 get_user_input")
        return context.get_user_input() or ""

    def _build_final_parts(self, content: str) -> list[Part]:
        parts = []

        if "---a2ui_JSON---" in content:
            text_content, json_string = content.split("---a2ui_JSON---", 1)

            if text_content.strip():
                parts.append(Part(root=TextPart(text=text_content.strip())))

            json_data = self._parse_json(json_string)
            if json_data:
                if isinstance(json_data, list):
                    for message in json_data:
                        parts.append(create_a2ui_part(message))
                else:
                    parts.append(create_a2ui_part(json_data))
        else:
            parts.append(Part(root=TextPart(text=content.strip())))

        return parts

    def _parse_json(self, json_string: str) -> list | dict | None:
        json_str = json_string.strip().lstrip("```json").rstrip("```").strip()
        if not json_str:
            return None

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return None

    async def cancel(self, request: RequestContext, event_queue: EventQueue) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
