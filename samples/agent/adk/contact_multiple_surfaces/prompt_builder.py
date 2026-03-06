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
from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

ROLE_DESCRIPTION = (
    "你是一个联系人查询助手。你的最终输出必须是 A2UI UI JSON 响应格式。"
)

WORKFLOW_DESCRIPTION = """
生成响应时，你必须遵循以下规则：
1. 响应必须分为两部分，使用分隔符 `---a2ui_JSON---` 分隔。
2. 第一部分是对话文本回复。
3. 第二部分是一个 JSON 对象数组，表示 A2UI 消息列表。
4. JSON 部分必须符合 A2UI JSON SCHEMA 规范。
5. 按钮（如"关注"、"发送邮件"、"搜索"等主操作）应包含 `"primary": true` 属性。
"""

UI_DESCRIPTION = """
- **查找联系人（如"Who is Alex Jordan?"）：**
  a. 你必须调用 `get_contact_info` 工具。
  b. 如果返回单个联系人，你必须使用 `MULTI_SURFACE_EXAMPLE` 模板。同时显示联系人卡片和组织架构图。
  c. 如果返回多个联系人，你必须使用 `CONTACT_LIST_EXAMPLE` 模板。
  d. 如果返回空列表，只返回文本和空 JSON 列表："未找到该联系人---a2ui_JSON---[]"

- **查看个人资料（如"WHO_IS: Alex Jordan..."）：**
  a. 你必须调用 `get_contact_info` 工具。
  b. 返回单个联系人时，使用 `CONTACT_CARD_EXAMPLE` 模板。

- **处理操作（如"USER_WANTS_TO_EMAIL: ..."）：**
  a. 使用 `ACTION_CONFIRMATION_EXAMPLE` 模板。
  b. 填充确认标题和消息（如标题："邮件已起草"、"正在给 Alex Jordan 起草邮件..."）。
"""


def get_text_prompt() -> str:
    return """
你是一个联系人查询助手。你的最终输出必须是文本响应。

生成响应时，遵循以下规则：
1. **查找联系人：**
   a. 你必须调用 `get_contact_info` 工具。从用户查询中提取姓名和部门。
   b. 收到数据后，将联系人格式化为清晰、易读的文本响应。
   c. 如果找到多个联系人，列出他们的姓名和职位。
   d. 如果找到一个联系人，列出其所有详细信息。

2. **处理操作（如"USER_WANTS_TO_EMAIL: ..."）：**
   a. 返回简单的文本确认（如"正在给...起草邮件..."）。
"""


if __name__ == "__main__":
  # Example of how to use the A2UI Schema Manager to generate a system prompt
  my_base_url = "http://localhost:8000"
  schema_manager = A2uiSchemaManager(
      "0.8",
      basic_examples_path="examples",
      accepts_inline_catalogs=True,
      schema_modifiers=[remove_strict_validation],
  )
  contact_prompt = schema_manager.generate_system_prompt(
      role_description=ROLE_DESCRIPTION,
      workflow_description=WORKFLOW_DESCRIPTION,
      ui_description=UI_DESCRIPTION,
      include_schema=True,
      include_examples=True,
      validate_examples=True,
  )
  print(contact_prompt)
  with open("generated_prompt.txt", "w") as f:
    f.write(contact_prompt)
  print("\nGenerated prompt saved to generated_prompt.txt")

  client_ui_capabilities_str = (
      '{"inlineCatalogs":[{"catalogId": "inline_catalog",'
      ' "components":{"OrgChart":{"type":"object","properties":{"chain":{"type":"array","items":{"type":"object","properties":{"title":{"type":"string"},"name":{"type":"string"}},"required":["title","name"]}},"action":{"$ref":"#/definitions/Action"}},"required":["chain"]},"WebFrame":{"type":"object","properties":{"url":{"type":"string"},"html":{"type":"string"},"height":{"type":"number"},"interactionMode":{"type":"string","enum":["readOnly","interactive"]},"allowedEvents":{"type":"array","items":{"type":"string"}}}}}}]}'
  )
  client_ui_capabilities = json.loads(client_ui_capabilities_str)
  inline_catalog = schema_manager.get_selected_catalog(
      client_ui_capabilities=client_ui_capabilities,
  )
  request_prompt = inline_catalog.render_as_llm_instructions()
  print(request_prompt)
  with open("request_prompt.txt", "w") as f:
    f.write(request_prompt)
  print("\nGenerated request prompt saved to request_prompt.txt")

  basic_catalog = schema_manager.get_selected_catalog()
  examples = schema_manager.load_examples(
      basic_catalog,
      validate=True,
  )
  print(examples)
  with open("examples.txt", "w") as f:
    f.write(examples)
  print("\nGenerated examples saved to examples.txt")
