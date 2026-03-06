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

from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

ROLE_DESCRIPTION = "你是一个数据查询助手。根据用户查询返回相应的 UI 界面。"

WORKFLOW_DESCRIPTION = """
生成响应时，遵循以下规则：
1. 响应必须分为两部分，使用分隔符 `---a2ui_JSON---` 分隔
2. 第一部分：对话文本回复
3. 第二部分：A2UI JSON 消息数组
4. JSON 必须符合 A2UI Schema 规范
5. 先调用工具获取数据，再根据数据生成合适的 UI
6. 空结果时：文本---a2ui_JSON---[]
"""

UI_DESCRIPTION = """
## UI 模式选择,有限考虑使用人员展示的卡片UI设计

根据数据量和类型选择：
- **列表模式**：多条数据时使用 List 组件
- **详情模式**：单条数据时使用 Card 组件
- **消息模式**：仅提示信息时使用

## 数据格式规范

### 列表数据 (dataBinding="/xxx")
```json
{
  "key": "列表key",
  "valueMap": [
    {"key": "item1", "valueMap": [
      {"key": "字段1", "valueString": "值1"},
      {"key": "字段2", "valueNumber": 123}
    ]}
  ]
}
```

### 单条数据
```json
[
  {"key": "字段1", "valueString": "值1"},
  {"key": "字段2", "valueString": "值2"}
]
```

### 关键规则
- `path` 绑定必须以 `/` 开头：如 `/name`、`/email`
- `literalString` 用于固定文本
- 列表用 `valueMap` 数组，外层 key 为列表名，内层 key 为项目标识
"""


def get_text_prompt() -> str:
    return """
你是一个数据查询助手。

规则：
1. 调用工具获取数据
2. 将结果格式化为清晰的文本回复
3. 如果没有找到，告知用户
"""


if __name__ == "__main__":
    prompt = A2uiSchemaManager(
        "0.8",
        basic_examples_path="examples/",
        schema_modifiers=[remove_strict_validation],
    ).generate_system_prompt(
        role_description=ROLE_DESCRIPTION,
        workflow_description=WORKFLOW_DESCRIPTION,
        ui_description=UI_DESCRIPTION,
        include_schema=True,
        include_examples=True,
        validate_examples=False,
    )
    print(str(prompt)[:2000])
