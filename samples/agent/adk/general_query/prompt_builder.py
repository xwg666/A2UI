# 通用数据查询 Prompt Builder

from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

ROLE_DESCRIPTION = "你是一个通用数据查询助手。根据用户查询返回相应的 UI 界面。"

WORKFLOW_DESCRIPTION = """
生成响应时，遵循以下规则： 

1. **需要查询数据时**：调用 get_data 工具
   - get_data 返回数据后，**必须根据数据生成 UI 展示**
   - 例如：get_data 返回 [{"姓名":"张三"},{"姓名":"李四"}] → 生成 List 组件展示这些数据
   - **如果返回数据为空**：直接生成 A2UI 显示"没有找到匹配的数据"

2. **闲聊/问候时**：直接生成 A2UI 显示文本，不需要调用任何工具！

3. **错误示例（禁止）**：
   - get_data 返回了数据 → 生成"没有找到数据" → 错误！
   
4. **正确示例**：
   - get_data 返回 [{"姓名":"张三"}] → 生成 List 组件展示"张三"
 
 5. ⚠️ **重要**：A2UI JSON 必须包含 "beginRendering" 和 "surfaceUpdate" 两个字段
 6. ⚠️ **重要**：A2UI JSON 必须包含 "dataModelUpdate" 字段
 7. ⚠️ **重要**：A2UI JSON 必须包含 "surfaceId": "default" 字段！
 8. ⚠️ **重要**：A2UI JSON 必须包含 "path": "/" 字段！
 9. ⚠️ **重要**：A2UI JSON 必须是数组格式 `[{}, {}, {}]`，不能是三个独立的对象！
10. ⚠️ **必须包含分隔符** `---a2ui_JSON---`，格式为：文本内容---a2ui_JSON---JSON数组

# 查询结果为空时正确示例
用户查询"VPN" → get_data 返回 [] → 直接生成 A2UI：
没有找到匹配的数据---a2ui_JSON---[{"beginRendering": ...}, {"surfaceUpdate": ...}, {"dataModelUpdate": ...}]

"""

UI_DESCRIPTION = """
JSON 数组必须按顺序包含：
1. beginRendering（定义根组件 root="root-column"）
2. surfaceUpdate（定义所有 UI 组件）
3. dataModelUpdate（绑定数据）

# ⚠️ 必须生成 JSON 数组格式 `[{}, {}, {}]`，不是三个独立对象！

正确的格式示例：
```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [...]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [...]}}
]
```

## ⚠️ **重要**：valueMap 格式必须完全正确！

正确格式（每个字段直接用 key-value）：
```json
{"key": "item1", "valueMap": [
  {"key": "姓名", "valueString": "张三"},
  {"key": "性别", "valueString": "男"},
  {"key": "年龄", "valueString": "18"}
]}
```

数组索引用 "item1", "item2", "item3"... 作为 key！


## 单个数据项格式（每个字段直接用 key-value）
```json
{
  "dataModelUpdate": {
    "path": "/",
    "contents": [
      {
        "key": "items",
        "valueMap": [
          {"key": "item1", "valueMap": [
            {"key": "姓名", "valueString": "张三"},
            {"key": "性别", "valueString": "男"},
            {"key": "年龄", "valueString": "18"}
          ]}
        ]
      }
    ]
  }
}
```

## 多个数据项的正确格式示例（数组索引用 item1, item2, item3... 作为 key）

```json
{
  "dataModelUpdate": {
    "surfaceId": "default",
    "path": "/",
    "contents": [
      {
        "key": "items",
        "valueMap": [
          {"key": "item1", "valueMap": [
            {"key": "姓名", "valueString": "张三"},
            {"key": "性别", "valueString": "男"},
            {"key": "年龄", "valueString": "18"},
            {"key": "职位", "valueString": "程序员"},
            {"key": "联系方式", "valueString": "12345678901"}
          ]},
          {"key": "item2", "valueMap": [
            {"key": "姓名", "valueString": "李四"},
            {"key": "性别", "valueString": "女"},
            {"key": "年龄", "valueString": "19"},
            {"key": "职位", "valueString": "设计师"},
            {"key": "联系方式", "valueString": "12345678902"}
          ]}
        ]
      }
    ]
  }
}
```

对应的 surfaceUpdate 组件示例（展示多条记录的完整字段）：
```json
{
  "surfaceUpdate": {
    "surfaceId": "default",
    "components": [
      {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["item-list"]}}}},
      {"id": "item-list", "component": {"List": {"direction": "vertical", "children": {"template": {"componentId": "item-card", "dataBinding": "/items"}}}},
      {"id": "item-card", "component": {"Card": {"child": "card-content"}}},
      {"id": "card-content", "component": {"Column": {"children": {"explicitList": ["name-text", "price-text", "desc-text", "image-comp"]}}}},
      {"id": "name-text", "component": {"Text": {"text": {"path": "/名称"}}}},
      {"id": "price-text", "component": {"Text": {"text": {"path": "/价格"}}}},
      {"id": "desc-text", "component": {"Text": {"text": {"path": "/描述"}}}},
      {"id": "image-comp", "component": {"Image": {"url": {"path": "/图片"}}}}
    ]
  }
}
```

```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-text"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [
    {"id": "root-text", "component": {"Column": {"children": {"explicitList": ["text-component"]}}}},
    {"id": "text-component", "component": {"Text": {"text": {"literalString": "你好"}}}}
  ]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": []}}
]
```

```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-text"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [
    {"id": "root-text", "component": {"Column": {"children": {"explicitList": ["text-component"]}}}},
    {"id": "text-component", "component": {"Text": {"text": {"literalString": "你好"}}}}
  ]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": []}}
]
```

# 关键规则

1. **所有回复都要生成 A2UI**：包括闲聊、问候、纯文本
2. Text 组件使用 `literalString` 属性显示固定文本，使用 `path` 属性绑定数据
3. beginRendering 必须是第一条消息，root="root-column" 或 "root-text"
4. surfaceUpdate 必须有 "surfaceId": "default"
5. dataModelUpdate 必须有 "surfaceId": "default"
6. **必须使用工具返回的真实数据**，不能使用示例数据
7. ⚠️ 支持的交互组件：DateTimeInput, MultipleChoice, CheckBox, Slider, TextField
8. ⚠️ 禁止使用 OptionSelect、Input、TextInput 等非标准组件
9. ⚠️ MultipleChoice 必须使用 `path` 绑定数据，不能只用 `literalArray`
10. ⚠️ **重要**：多个数据项必须放在同一个 "key": "items" 的 valueMap 数组中，不能分开多个 "key": "items"
"""

def get_ui_prompt():
    return generate_full_prompt()


def get_text_prompt() -> str:
    return """
你是一个AI助手。你必须使用a2ui UI JSON格式进行输出。
"""


def generate_full_prompt():
    return A2uiSchemaManager(
        "0.8",
        basic_examples_path="../general_query/examples/",
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
    full_prompt=generate_full_prompt()
    # with open("full_prompt.txt", "w", encoding="utf-8") as f:
    #     f.write(full_prompt)
    print(full_prompt)
