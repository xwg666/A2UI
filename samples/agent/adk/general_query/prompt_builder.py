"""
通用数据查询 Prompt Builder

这个模块负责生成 Agent 的提示词。
由于数据获取逻辑已移到 agent.py，LLM 只需要专注于生成 UI。
"""

from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

ROLE_DESCRIPTION = "你是一个智能的文本格式转换器，只对输入的内容进行UI渲染判断，选择合适的一个或者多个A2UI组件进行UI页面设计，只输出符合A2UI格式的JSON数组。"

WORKFLOW_DESCRIPTION = """
## 任务说明

你收到的消息格式如下：
```
用户查询：xxx
已获取的数据（共 N 条）：
[数据列表]

请根据以上数据生成 A2UI 界面展示。
```

## ⚠️ 重要：响应格式

响应只能包含一个分隔符 `---a2ui_JSON---`，格式为：
```
文本内容---a2ui_JSON---[JSON数组]
```

## 生成规则

1. **数据已获取**：你收到的消息中已包含查询结果数据，不需要再调用工具
2. **生成 UI**：根据数据内容生成合适的 A2UI 界面
3. **数据绑定**：使用 `path` 绑定数据，不要用 `literalString`
   - 例如：`"text": {"path": "/姓名"}` 而不是 `"text": {"literalString": "张三"}`
4. **数组数据**：使用 List 组件的 `dataBinding` 绑定数组
   - 例如：`"dataBinding": "/items"`
5. **⚠️ 禁止使用的属性**：`fit`、`usageHint`、`OptionSelect`、`Input`、`TextInput`
6. **⚠️ 禁止使用的组件**：`FileUpload`、`VideoPlayer`、`AudioPlayer`、`WebFrame`
   - 这些属性会导致验证失败，不要在 JSON 中使用

## ⚠️ 多条数据展示必须使用 List 组件

展示多条数据时，必须使用以下结构：

```json
{"id": "item-list", "component": {"List": {
  "direction": "vertical",
  "children": {"template": {"componentId": "item-card", "dataBinding": "/items"}}
}}}
```

关键点：
- `dataBinding`: 必须设置为 `"/items"`
- `template.componentId`: 指向模板组件的 ID
- 模板组件内部使用 `path` 绑定字段，如 `"/姓名"`、`"/价格"`

## ⚠️ 单条数据展示

如果只有一条数据，**也必须使用 List 组件**：

```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [
    {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["item-list"]}}}},
    {"id": "item-list", "component": {"List": {"direction": "vertical", "children": {"template": {"componentId": "item-card", "dataBinding": "/items"}}}}},
    {"id": "item-card", "component": {"Card": {"child": "card-content"}}},
    {"id": "card-content", "component": {"Column": {"children": {"explicitList": ["name-text", "price-text"]}}}},
    {"id": "name-text", "component": {"Text": {"text": {"path": "/商品名称"}}}},
    {"id": "price-text", "component": {"Text": {"text": {"path": "/价格"}}}}
  ]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [
    {"key": "items", "valueMap": [
      {"key": "item1", "valueMap": [
        {"key": "商品名称", "valueString": "电脑"},
        {"key": "价格", "valueString": "2000"}
      ]}
    ]}
  ]}}
]
```

## ⚠️ 必须生成 3 条消息

JSON 数组必须按顺序包含：
1. **beginRendering**（定义根组件 root="root-column"）
2. **surfaceUpdate**（定义所有 UI 组件）
3. **dataModelUpdate**（绑定数据）

## 正确格式示例

```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [...]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [...]}}
]
```

## valueMap 格式

单个数据项：
```json
{"key": "item1", "valueMap": [
  {"key": "姓名", "valueString": "张三"},
  {"key": "性别", "valueString": "男"}
]}
```

多个数据项（使用 item1, item2, item3... 作为 key）：
```json
{"key": "items", "valueMap": [
  {"key": "item1", "valueMap": [{"key": "姓名", "valueString": "张三"}]},
  {"key": "item2", "valueMap": [{"key": "姓名", "valueString": "李四"}]}
]}
```

## 组件示例

展示多条记录：
```json
{"id": "item-list", "component": {"List": {
  "direction": "vertical",
  "children": {"template": {"componentId": "item-card", "dataBinding": "/items"}}
}}}
```

展示单个字段：
```json
{"id": "name-text", "component": {"Text": {"text": {"path": "/姓名"}}}}
```

## 展示形式选择

根据数据特点选择合适的展示形式：

1. **卡片列表**（默认）：适合有图片、描述性文字的数据
   - 菜品、商品、人员信息等

2. **表格形式**：适合对比数据、多字段属性数据
   - 产品对比、属性列表、多列数据
   - 使用 Row 组件作为表头和数据行
   - 表头使用 `literalString`，数据行使用 `path` 绑定

3. **纯文本**：适合单条简单数据或提示信息
"""

UI_DESCRIPTION = """
## A2UI JSON 结构

JSON 数组必须按顺序包含三个对象：

### 1. beginRendering
```json
{"beginRendering": {"surfaceId": "default", "root": "root-column"}}
```

### 2. surfaceUpdate
定义所有 UI 组件，包括：
- 根容器（Column）
- 列表容器（List）
- 卡片容器（Card）
- 文本组件（Text）
- 图片组件（Image）

### 3. dataModelUpdate
绑定数据到组件：
- `path`: 数据路径
- `contents`: 数据内容
- `valueMap`: 键值对映射

## 组件属性

### Text 组件
- `text`: 文本内容
  - `literalString`: 固定文本
  - `path`: 数据绑定路径
- `usageHint`: 文本样式（h1, h2, h3, h4, h5, caption, body）

### Image 组件
- `url`: 图片地址
  - `literalString`: 固定 URL
  - `path`: 数据绑定路径
- `fit`: 图片适配方式（contain, cover, fill, none, scale-down）
- `usageHint`: 图片大小和样式（icon, avatar, smallFeature, mediumFeature, largeFeature, header）

### List 组件
- `direction`: 方向（"vertical" 或 "horizontal"）
- `children`: 子组件
  - `explicitList`: 固定子组件列表
  - `template`: 模板（用于数据绑定）

### Card 组件
- `child`: 子组件 ID

### Column 组件
- `children`: 子组件列表
  - `explicitList`: 固定子组件 ID 数组

### Row 组件
- `children`: 子组件列表
  - `explicitList`: 固定子组件 ID 数组

## 关键规则

1. **所有回复都要生成 A2UI**
2. Text 组件使用 `literalString` 显示固定文本，使用 `path` 绑定数据
3. beginRendering 必须是第一条消息
4. surfaceUpdate 必须有 "surfaceId": "default"
5. dataModelUpdate 必须有 "surfaceId": "default"
6. **必须使用提供的数据**，不能使用示例数据
7. ⚠️ 支持的交互组件：DateTimeInput, MultipleChoice, CheckBox, Slider, TextField
8. ⚠️ 禁止使用 OptionSelect、Input、TextInput 等非标准组件

## 完整示例

### 人员数据展示
```json
[
  {
    "beginRendering": {
      "surfaceId": "default",
      "root": "root-column"
    }
  },
  {
    "surfaceUpdate": {
      "surfaceId": "default",
      "components": [
        {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["item-list"]}}}},
        {"id": "item-list", "component": {"List": {"direction": "vertical", "children": {"template": {"componentId": "item-card-template", "dataBinding": "/items"}}}}},
        {"id": "item-card-template", "component": {"Card": {"child": "card-layout"}}},
        {"id": "card-layout", "component": {"Column": {"children": {"explicitList": ["template-name", "template-job"]}}}},
        {"id": "template-name", "component": {"Text": {"text": {"path": "/姓名"}}}},
        {"id": "template-job", "component": {"Text": {"text": {"path": "/职位"}}}}
      ]
    }
  },
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
              {"key": "职位", "valueString": "程序员"}
            ]},
            {"key": "item2", "valueMap": [
              {"key": "姓名", "valueString": "李四"},
              {"key": "职位", "valueString": "设计师"}
            ]}
          ]
        }
      ]
    }
  }
]
```

### 菜品数据展示
```json
[
  {
    "beginRendering": {
      "surfaceId": "default",
      "root": "root-column"
    }
  },
  {
    "surfaceUpdate": {
      "surfaceId": "default",
      "components": [
        {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["item-list"]}}}},
        {"id": "item-list", "component": {"List": {"direction": "vertical", "children": {"template": {"componentId": "item-card-template", "dataBinding": "/items"}}}}},
        {"id": "item-card-template", "component": {"Card": {"child": "card-layout"}}},
        {"id": "card-layout", "component": {"Column": {"children": {"explicitList": ["template-name", "template-price", "template-image"]}}}},
        {"id": "template-name", "component": {"Text": {"text": {"path": "/菜品名称"}}}},
        {"id": "template-price", "component": {"Text": {"text": {"path": "/价格"}}}},
        {"id": "template-image", "component": {"Image": {"url": {"path": "/图片"}}}}
      ]
    }
  },
  {
    "dataModelUpdate": {
      "surfaceId": "default",
      "path": "/",
      "contents": [
        {
          "key": "items",
          "valueMap": [
            {"key": "item1", "valueMap": [
              {"key": "菜品名称", "valueString": "火锅"},
              {"key": "价格", "valueString": "30"},
              {"key": "图片", "valueString": "https://img95.699pic.com/photo/50086/0799.jpg_wh860.jpg"}
            ]}
          ]
        }
      ]
    }
  }
]
```

### 纯文本回复
```json
[
  {
    "beginRendering": {
      "surfaceId": "default",
      "root": "root-text"
    }
  },
  {
    "surfaceUpdate": {
      "surfaceId": "default",
      "components": [
        {"id": "root-text", "component": {"Column": {"children": {"explicitList": ["text-component"]}}}},
        {"id": "text-component", "component": {"Text": {"text": {"literalString": "你好！有什么可以帮你的？"}}}}
      ]
    }
  },
  {
    "dataModelUpdate": {
      "surfaceId": "default",
      "path": "/",
      "contents": []
    }
  }
]
```

### 表格形式展示（使用 Row + Column 模拟表格）
适用于：对比数据、多字段数据、属性列表等

**带边框表格** - 使用 Card 组件包裹每行：
```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [
    {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["header-row", "data-list"]}}}},
    {"id": "header-row", "component": {"Row": {"children": {"explicitList": ["header-name", "header-gender", "header-age"]}}}},
    {"id": "header-name", "component": {"Text": {"text": {"literalString": "姓名"}, "style": "font-weight: bold"}}},
    {"id": "header-gender", "component": {"Text": {"text": {"literalString": "性别"}, "style": "font-weight: bold"}}},
    {"id": "header-age", "component": {"Text": {"text": {"literalString": "年龄"}, "style": "font-weight: bold"}}},
    {"id": "data-list", "component": {"List": {"direction": "vertical", "children": {"template": {"componentId": "row-card", "dataBinding": "/items"}}}}},
    {"id": "row-card", "component": {"Card": {"child": "row-content", "style": "margin: 4px 0; padding: 8px"}}},
    {"id": "row-content", "component": {"Row": {"children": {"explicitList": ["template-name", "template-gender", "template-age"]}}}},
    {"id": "template-name", "component": {"Text": {"text": {"path": "/姓名"}}}},
    {"id": "template-gender", "component": {"Text": {"text": {"path": "/性别"}}}},
    {"id": "template-age", "component": {"Text": {"text": {"path": "/年龄"}}}}
  ]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [
    {"key": "items", "valueMap": [
      {"key": "item1", "valueMap": [
        {"key": "姓名", "valueString": "张三"},
        {"key": "性别", "valueString": "男"},
        {"key": "年龄", "valueString": "25"}
      ]},
      {"key": "item2", "valueMap": [
        {"key": "姓名", "valueString": "李四"},
        {"key": "性别", "valueString": "女"},
        {"key": "年龄", "valueString": "30"}
      ]}
    ]}
  ]}}
]
```
 
 **简单表格（无边框）**：
 ```json
 [
   {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
   {"surfaceUpdate": {"surfaceId": "default", "components": [
     {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["header-row", "data-list"]}}}},
     {"id": "header-row", "component": {"Row": {"children": {"explicitList": ["header-name", "header-gender", "header-age"]}}}},
     {"id": "header-name", "component": {"Text": {"text": {"literalString": "姓名"}}}},
     {"id": "header-gender", "component": {"Text": {"text": {"literalString": "性别"}}}},
     {"id": "header-age", "component": {"Text": {"text": {"literalString": "年龄"}}}},
     {"id": "data-list", "component": {"List": {"direction": "vertical", "children": {"template": {"componentId": "row-template", "dataBinding": "/items"}}}}},
     {"id": "row-template", "component": {"Row": {"children": {"explicitList": ["template-name", "template-gender", "template-age"]}}}},
     {"id": "template-name", "component": {"Text": {"text": {"path": "/姓名"}}}},
     {"id": "template-gender", "component": {"Text": {"text": {"path": "/性别"}}}},
     {"id": "template-age", "component": {"Text": {"text": {"path": "/年龄"}}}}
   ]}},
   {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [
     {"key": "items", "valueMap": [
       {"key": "item1", "valueMap": [
         {"key": "姓名", "valueString": "张三"},
         {"key": "性别", "valueString": "男"},
         {"key": "年龄", "valueString": "25"}
       ]}
     ]}
   ]}}
 ]
 ```
 
### 对比表格展示（适合产品对比、属性对比）
```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [
    {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["title", "compare-list"]}}}},
    {"id": "title", "component": {"Text": {"text": {"literalString": "产品对比"}}}},
    {"id": "compare-list", "component": {"List": {"direction": "vertical", "children": {"template": {"componentId": "compare-row", "dataBinding": "/items"}}}}},
    {"id": "compare-row", "component": {"Card": {"child": "compare-row-content"}}},
    {"id": "compare-row-content", "component": {"Row": {"children": {"explicitList": ["template-name", "template-price", "template-rating"]}}}},
    {"id": "template-name", "component": {"Text": {"text": {"path": "/名称"}}}},
    {"id": "template-price", "component": {"Text": {"text": {"path": "/价格"}}}},
    {"id": "template-rating", "component": {"Text": {"text": {"path": "/评分"}}}}
  ]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [
    {"key": "items", "valueMap": [
      {"key": "item1", "valueMap": [
        {"key": "名称", "valueString": "产品A"},
        {"key": "价格", "valueString": "免费"},
        {"key": "评分", "valueString": "4星"}
      ]},
      {"key": "item2", "valueMap": [
        {"key": "名称", "valueString": "产品B"},
        {"key": "价格", "valueString": "付费"},
        {"key": "评分", "valueString": "5星"}
      ]}
    ]}
  ]}}
]
```
"""


def get_ui_prompt():
    return generate_full_prompt()


def get_text_prompt() -> str:
    return """
你是一个AI助手。你必须使用a2ui UI JSON格式进行输出。
"""


def get_check_params_prompt(query: str) -> str:
    """
    生成检查必填参数的 prompt
    
    Args:
        query: 用户查询
        
    Returns:
        str: 用于 LLM 判断必填参数的 prompt
    """
    return f"""分析用户问题，判断是否缺少必填参数。

用户问题：{query}

判断规则：
1. 如果问题中已经包含具体的人名（如"张三"、"李四"），则 name 参数已提供
2. 如果问题是通用查询（如"账号密码是多少"、"查询员工信息"），则缺少 name 参数
3. 只返回真正缺少的参数，不要返回已提供的参数

返回 JSON 格式：
{{"missing_params": ["缺少的参数"], "need_more_info": true/false}}

示例：
- "张三的账号密码是多少？" → {{"missing_params": [], "need_more_info": false}}  （已有姓名）
- "账号密码是多少？" → {{"missing_params": ["name"], "need_more_info": true}}  （缺少姓名）
- "查询员工信息" → {{"missing_params": ["name"], "need_more_info": true}}  （缺少姓名）
- "查询张三的工资" → {{"missing_params": [], "need_more_info": false}}  （已有姓名）
- "李四的电话是多少" → {{"missing_params": [], "need_more_info": false}}  （已有姓名）

只返回 JSON，不要其他内容。"""


def get_form_generation_prompt(query: str, required_params: list[str], filled_info: str = "") -> str:
    """
    生成表单 UI 的 prompt
    
    Args:
        query: 用户原始查询
        required_params: 必填参数列表
        filled_info: 已填写参数的信息（可选）
        
    Returns:
        str: 用于 LLM 生成表单 UI 的 prompt
    """
    return f"""用户询问：{query}

必填参数列表：{required_params}
{filled_info}
请生成一个 A2UI 表单界面，让用户填写参数。

响应格式：文本---a2ui_JSON---[JSON数组]

要求：
1. 必须生成 3 条消息（beginRendering, surfaceUpdate, dataModelUpdate）
2. ⚠️ 重要：在表单顶部添加一个提示文本组件，显示"⚠️ 所有参数必填，请完整填写"
3. 每个参数使用 TextField 组件，标签使用中文
4. ⚠️ 重要：已填写的参数需要在 TextField 中显示当前值（通过 value 绑定）
5. 添加一个提交按钮，action.name 为 "submit_form"
6. ⚠️ 重要：button 的 context 必须是数组格式，包含所有必填参数：
   - 格式：[{{"key": "字段名", "value": {{"path": "/formData/字段名"}}}}]
   - 必须包含所有必填参数，不只是未填写的
   - 例如：context: [{{"key": "name", "value": {{"path": "/formData/name"}}}}, {{"key": "age", "value": {{"path": "/formData/age"}}}}]
7. dataModelUpdate 中初始化数据，路径为 /formData，包含所有参数（已填写的显示值，未填写的为空字符串）

参数中文映射：
- name → 姓名
- age → 年龄  
- sex/gender → 性别
- phone → 电话
- email → 邮箱

示例结构：
- root-column 包含：提示文本、name-field、email-field、submit-button
- 提示文本显示"⚠️ 所有参数必填，请完整填写"
- name 的 TextField 显示已填写的值
- email 的 TextField 显示空
- context 包含 name 和 email 两个参数"""


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
    full_prompt = generate_full_prompt()
    print(full_prompt)
