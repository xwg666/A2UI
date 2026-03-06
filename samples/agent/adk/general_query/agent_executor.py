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

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_parts_message,
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError
from a2ui.extension.a2ui_extension import create_a2ui_part, try_activate_a2ui_extension
from agent import GeneralQueryAgent

logger = logging.getLogger(__name__)


class GeneralQueryAgentExecutor(AgentExecutor):
    """通用查询 AgentExecutor"""

    def __init__(self, ui_agent: GeneralQueryAgent, text_agent: GeneralQueryAgent):
        self.ui_agent = ui_agent
        self.text_agent = text_agent

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = ""
        ui_event_part = None

        logger.info(f"--- Client requested extensions: {context.requested_extensions} ---")
        use_ui = try_activate_a2ui_extension(context)

        if use_ui:
            agent = self.ui_agent
            logger.info("--- AGENT_EXECUTOR: 使用 UI agent ---")
        else:
            agent = self.text_agent
            logger.info("--- AGENT_EXECUTOR: 使用 text agent ---")

        if context.message and context.message.parts:
            for part in context.message.parts:
                if isinstance(part.root, TextPart):
                    query = part.root.text
                elif isinstance(part.root, DataPart):
                    if "userAction" in part.root.data:
                        ui_event_part = part.root.data["userAction"]

        if ui_event_part:
            action = ui_event_part.get("actionName")
            ctx = ui_event_part.get("context", {})
            query = f"User submitted: {action}, data: {ctx}"
        else:
            query = context.get_user_input()

        logger.info(f"--- AGENT_EXECUTOR: Query = '{query}' ---")

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        async for item in agent.stream(query, task.context_id):
            is_task_complete = item["is_task_complete"]
            if not is_task_complete:
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
                        json_cleaned = json_string.strip().lstrip("```json").rstrip("```").strip().replace("---a2ui_JSON---", "")
                        json_data = json.loads(json_cleaned)

                        if isinstance(json_data, list):
                            for message in json_data:
                                final_parts.append(create_a2ui_part(message))
                        else:
                            final_parts.append(create_a2ui_part(json_data))

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON 解析失败: {e}")
                        final_parts.append(Part(root=TextPart(text=json_string)))
            else:
                final_parts.append(Part(root=TextPart(text=content.strip())))

            logger.info("--- FINAL PARTS ---")
            for i, part in enumerate(final_parts):
                logger.info(f"  Part {i}: {type(part.root)}")
            logger.info("-------------------")

            await updater.update_status(
                TaskState.completed,
                new_agent_parts_message(final_parts, task.context_id, task.id),
                final=True,
            )
            break

    async def cancel(self, request: RequestContext, event_queue: EventQueue) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
