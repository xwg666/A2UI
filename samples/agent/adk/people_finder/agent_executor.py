import json
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part, Task, TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_parts_message, new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from a2ui.extension.a2ui_extension import create_a2ui_part, try_activate_a2ui_extension
from agent import PeopleFinderAgent

logger = logging.getLogger(__name__)


class PeopleFinderAgentExecutor(AgentExecutor):
    def __init__(self, ui_agent: PeopleFinderAgent, text_agent: PeopleFinderAgent):
        self.ui_agent = ui_agent
        self.text_agent = text_agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = ""
        ui_event_part = None

        logger.info(f"--- Client extensions: {context.requested_extensions} ---")
        use_ui = try_activate_a2ui_extension(context)

        agent = self.ui_agent if use_ui else self.text_agent
        logger.info(f"--- Using {'UI' if use_ui else 'Text'} agent ---")

        if context.message and context.message.parts:
            for part in context.message.parts:
                if isinstance(part.root, DataPart):
                    if "userAction" in part.root.data:
                        ui_event_part = part.root.data["userAction"]
                elif isinstance(part.root, TextPart):
                    query = part.root.text

        if ui_event_part:
            action = ui_event_part.get("actionName")
            ctx = ui_event_part.get("context", {})
            query = f"用户操作: {action}, 数据: {ctx}"

        if not query:
            query = context.get_user_input() or ""

        logger.info(f"--- Query: '{query}' ---")

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        async for item in agent.stream(query, task.context_id):
            if not item["is_task_complete"]:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(item["updates"], task.context_id, task.id),
                )
                continue

            content = item["content"]
            final_parts = []

            if "---a2ui_JSON---" in content:
                text_content, json_string = content.split("---a2ui_JSON---", 1)

                if text_content.strip():
                    final_parts.append(Part(root=TextPart(text=text_content.strip())))

                if json_string.strip():
                    try:
                        json_cleaned = (
                            json_string.strip()
                            .lstrip("```json")
                            .rstrip("```")
                            .strip()
                        )
                        json_data = json.loads(json_cleaned)

                        if isinstance(json_data, list):
                            for msg in json_data:
                                final_parts.append(create_a2ui_part(msg))
                        else:
                            final_parts.append(create_a2ui_part(json_data))

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parse error: {e}")
                        final_parts.append(Part(root=TextPart(text=json_string)))
            else:
                final_parts.append(Part(root=TextPart(text=content.strip())))

            logger.info(f"--- Final parts: {len(final_parts)} ---")

            await updater.update_status(
                TaskState.input_required,
                new_agent_parts_message(final_parts, task.context_id, task.id),
                final=False,
            )
            break

    async def cancel(self, request: RequestContext, event_queue: EventQueue) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
