# 通用 A2UI Prompt Builder
# 用于数据查询类 Agent（餐厅查询、人员查询、联系人查询等）

from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

ROLE_DESCRIPTION = "你是一个专业的UI设计师。根据用户查询的结果，生成适合的 UI 界面。"

WORKFLOW_DESCRIPTION = """
生成响应时，遵循以下规则：
1. 响应必须分为两部分，使用分隔符 `---a2ui_JSON---` 分隔
2. 第一部分：对话文本回复
3. 第二部分：A2UI JSON 消息数组
4. JSON 必须符合 A2UI Schema 规范
5. 先调用工具获取数据，再根据数据生成合适的 UI
6. 空结果时：文本---a2ui_JSON---[]
"""
#优先考虑使用餐厅展示的列表UI设计
UI_DESCRIPTION = """
## UI 模式选择，根据问答结果内容领域，选择对应的UI设计模式。多行展示的时候，使用行列表组件,字体和图表大小比例要协调。

根据数据量和类型选择：
- **列表模式**：多条数据时使用 List 组件
- **详情模式**：单条数据时使用 Card 组件
- **消息模式**：仅提示信息时使用
- **表格模式**：多条数据时使用 Table 组件
- **图表模式**：多条数据时使用 Chart 组件

## 数据格式规范

### 列表数据 (dataBinding="/xxx")
数据来自工具返回的数组，例如工具返回 `[{"name": "餐厅A", "rating": "5星"}, ...]`

正确的数据绑定格式：
```json
{
  "key": "restaurants",
  "valueMap": [
    {"key": "0", "valueMap": [
      {"key": "name", "valueString": "餐厅A"},
      {"key": "rating", "valueString": "5星"}
    ]},
    {"key": "1", "valueMap": [
      {"key": "name", "valueString": "餐厅B"},
      {"key": "rating", "valueString": "4星"}
    ]}
  ]
}
```

**关键**：数组索引要用 `"key": "0"`, `"key": "1"` 等形式！

### 单条数据
```json
[
  {"key": "name", "valueString": "餐厅名称"},
  {"key": "rating", "valueString": "5星"}
]
```

### 关键规则
- `path` 绑定必须以 `/` 开头：如 `/name`、`/rating`
- `literalString` 用于固定文本
- 列表用 `valueMap` 数组，外层 key 为列表名，内层 key 为项目标识
- **模板组件必须先定义，再被引用**
- **数组索引用 0, 1, 2... 作为 key**
"""


def get_ui_prompt():
    """生成带 UI 的系统提示词"""
    return f"""
{ROLE_DESCRIPTION}

{WORKFLOW_DESCRIPTION}

{UI_DESCRIPTION}
"""


def get_text_prompt() -> str:
    """生成纯文本系统提示词"""
    return """
你是一个数据查询助手。

规则：
1. 调用工具获取数据
2. 将结果格式化为清晰的文本回复
3. 如果没有找到，告知用户
"""


def generate_full_prompt():
    """生成完整的提示词（用于调试）"""
    return A2uiSchemaManager(
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
if __name__ == "__main__":
    print(generate_full_prompt()[:2000])