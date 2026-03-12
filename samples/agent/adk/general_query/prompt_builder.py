"""
通用数据查询 Prompt Builder

这个模块负责生成 Agent 的提示词。
由于数据获取逻辑已移到 agent.py，LLM 只需要专注于生成 UI。
"""

from a2ui.inference.schema.manager import A2uiSchemaManager
from a2ui.inference.schema.common_modifiers import remove_strict_validation

ROLE_DESCRIPTION = "你是一个智能的文本格式转换器，只对输入的内容进行UI渲染判断，选择合适的一个或者多个A2UI组件进行UI页面设计，只输出符合A2UI格式的JSON数组。要求组件只能使用A2UI官方组件库中的组件（可以参考A2UI SCHEMA），不能自定义组件。"

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
6. **⚠️ 禁止使用的组件**：`VideoPlayer`、`AudioPlayer`、`WebFrame`
   - 这些属性会导致验证失败，不要在 JSON 中使用

## 支持的交互组件

支持以下交互组件用于用户输入：
- **TextField**：文本输入框
- **DateTimeInput**：日期时间选择
- **MultipleChoice**：多选
- **CheckBox**：复选框
- **Slider**：滑块
- **FileUpload**：文件上传

### FileUpload 文件上传组件

```json
{"id": "file-upload", "component": {"FileUpload": {
  "multiple": false,
  "accept": ".jpg,.png,.pdf",
  "action": {"name": "upload", "context": [{"key": "files", "value": {"path": "/files"}}]}
}}}
```

- `multiple`: 是否允许多文件选择
- `accept`: 接受的文件类型
- `action`: 用户选择文件后的动作

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
    {"id": "card-content", "component": {"Column": {"children": {"explicitList": ["name-row", "price-row"]}}}},
    // 每行使用 Row 组件，左侧显示 label，右侧显示 value
    {"id": "name-row", "component": {"Row": {"children": {"explicitList": ["name-label", "name-value"]}, "distribution": "start", "alignment": "center"}}},
    {"id": "name-label", "component": {"Text": {"text": {"literalString": "商品名称："}, "usageHint": "body"}}},
    {"id": "name-value", "component": {"Text": {"text": {"path": "/商品名称"}, "usageHint": "h4"}}},
    {"id": "price-row", "component": {"Row": {"children": {"explicitList": ["price-label", "price-value"]}, "distribution": "start", "alignment": "center"}}},
    {"id": "price-label", "component": {"Text": {"text": {"literalString": "价格："}, "usageHint": "body"}}},
    {"id": "price-value", "component": {"Text": {"text": {"path": "/价格"}, "usageHint": "h4"}}}
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

### ⚠️ 重要：用户明确要求"表格"时
**当用户问题中包含"表格"、"用表格"、"以表格形式"等关键词时，必须优先使用 Table 组件**

1. **表格形式（Table）**：
   - 产品对比、属性列表、多列数据
   - 使用 Table 组件，设置 headers 和 rows 属性
   - headers 是表头数组，rows 是二维数组（每行是单元格数组）
   - ⚠️ Table 组件的 rows 必须使用静态字符串，不支持 path 数据绑定
   - 示例：`"rows": [["张三", "程序员"], ["李四", "设计师"]]`

2. **卡片列表**：适合有图片、描述性文字的数据
   - 菜品、商品、人员信息等

3. **纯文本**：适合单条简单数据或提示信息

4. **动态表格（List + Row）**：仅当数据必须从 dataModelUpdate 动态绑定时使用
   - 使用 List 组件的 dataBinding 绑定数据
   - 表头使用 `literalString`，数据行使用 `path` 绑定

**完整示例 1 - 静态表格数据：**
```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [
    {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["data-table"]}}}},
    {"id": "data-table", "component": {"Table": {
      "headers": ["姓名", "职位", "账号到期时间"],
      "rows": [
        ["张三", "程序员", "2025-12-31"],
        ["李四", "设计师", "2025-06-30"]
      ]
    }}}
  ]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": []}}
]
```

**完整示例 2 - 动态数据表格（使用 List + Row）：**
```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [
    {"id": "root-column", "component": {"Column": {"children": {"explicitList": ["header-row", "data-list"]}}}},
    {"id": "header-row", "component": {"Row": {"children": {"explicitList": ["h1", "h2", "h3"]}}}},
    {"id": "h1", "component": {"Text": {"text": {"literalString": "姓名"}}}},
    {"id": "h2", "component": {"Text": {"text": {"literalString": "职位"}}}},
    {"id": "h3", "component": {"Text": {"text": {"literalString": "到期时间"}}}},
    {"id": "data-list", "component": {"List": {"direction": "vertical", "children": {"template": {"componentId": "row-template", "dataBinding": "/items"}}}}},
    {"id": "row-template", "component": {"Row": {"children": {"explicitList": ["c1", "c2", "c3"]}}}},
    {"id": "c1", "component": {"Text": {"text": {"path": "/姓名"}}}},
    {"id": "c2", "component": {"Text": {"text": {"path": "/职位"}}}},
    {"id": "c3", "component": {"Text": {"text": {"path": "/到期时间"}}}}
  ]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [
    {"key": "items", "valueMap": [
      {"key": "item1", "valueMap": [{"key": "姓名", "valueString": "张三"}, {"key": "职位", "valueString": "程序员"}, {"key": "到期时间", "valueString": "2025-12-31"}]},
      {"key": "item2", "valueMap": [{"key": "姓名", "valueString": "李四"}, {"key": "职位", "valueString": "设计师"}, {"key": "到期时间", "valueString": "2025-06-30"}]}
    ]}
  ]}}
]
```
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
- 行布局组件（Row）
- 列布局组件（Column）
- 组件容器（Container）
- 表单组件（Form）
- 表格组件（Table）

### 3. dataModelUpdate
绑定数据到组件：
- `path`: 数据路径
- `contents`: 数据内容
- `valueMap`: 键值对映射

## 重要：数据路径绑定规则

组件中的 `path` 必须与 dataModelUpdate 中的数据路径完全匹配：

**示例 1 - 数据在根路径：**
```json
// dataModelUpdate
{"path": "/", "contents": [{"key": "姓名", "valueString": "张三"}]}

// 组件绑定
{"path": "/姓名"}
```

**示例 2 - 数据在 items 下（使用 List template）：**
```json
// dataModelUpdate
{"path": "/", "contents": [{"key": "items", "valueMap": [...]}]}

// List 组件
dataBinding: "/items"

// template 中的组件绑定（相对路径）
{"path": "/姓名"}  // 实际解析为 /items/itemX/姓名
```

**示例 3 - 数据在 items/item1 下（静态展示）：**
```json
// dataModelUpdate
{"path": "/", "contents": [{"key": "items", "valueMap": [{"key": "item1", "valueMap": [...]}]}]}

// 静态组件绑定（必须使用完整路径）
{"path": "/items/item1/姓名"}
```

⚠️ **常见错误**：如果使用静态组件（不用 List template），但数据放在 items/item1 下，组件 path 必须用完整路径 `/items/item1/xxx`，不能用 `/xxx`。

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

只能选择下面A2UI SCHEMA中的组件，不能使用其他组件。
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

重要规则：
- 只生成必填参数列表中指定的字段，不要额外添加其他字段
- 如果必填参数只有 ["name"]，则只生成 name 字段，不要生成 email 字段

示例结构（假设必填参数为 ["name", "email"]）：
- root-column 包含：提示文本、name-field、email-field、submit-button
- 提示文本显示"⚠️ 所有参数必填，请完整填写"
- name 的 TextField 显示已填写的值
- email 的 TextField 显示空
- context 包含 name 和 email 两个参数

如果必填参数只有 ["name"]，则只生成：
- root-column 包含：提示文本、name-field、submit-button
- context 只包含 name 一个参数"""


def generate_full_prompt():
    prompt = A2uiSchemaManager(
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
    
    # 在 schema 后添加中文说明
    schema_section = "---BEGIN A2UI JSON SCHEMA---"
    end_schema_section = "---END A2UI JSON SCHEMA---"
    
    if schema_section in prompt and end_schema_section in prompt:
        end_idx = prompt.find(end_schema_section) + len(end_schema_section)
        
        chinese_component_guide = """

## 📋 A2UI 组件中文说明

### 布局组件
- **Column**: 垂直布局容器
- **Row**: 水平布局容器
- **List**: 列表容器
- **Card**: 卡片容器

### 内容组件
- **Text**: 文本组件
  - `text.literalString`: 固定文本
  - `text.path`: 数据绑定路径
  - `usageHint`: 文本样式（h1-h5, body, caption）
- **Image**: 图片组件
- **Table**: 表格组件
  - `headers`: 表头数组
  - `rows`: 二维数组数据

### 表单组件
- **TextField**: 文本输入框
- **MultipleChoice**: 多选/单选组件
  - `selections`: 选中项绑定
  - `options`: 选项数组
  - `variant`: 样式 ("checkbox" | "chips" | "dropdown")
    - `"dropdown"` - 下拉选择框（推荐用于单选）
    - `"chips"` - 标签选择
    - `"checkbox"` - 复选框列表
  - `maxAllowedSelections`: 最大可选数量
    - 设置为 1 = 单选
- **Slider**: 滑块输入
- **DateTimeInput**: 日期时间选择器
  - `value`: 日期时间值，使用 `path` 绑定到 data model
  - `enableDate`: 是否显示日期选择（true/false）
  - `enableTime`: 是否显示时间选择（true/false）
  - ⚠️ **重要**：必须在 `dataModelUpdate` 中提供初始值，格式为 ISO 8601 字符串
    - 日期时间：`"2026-03-12T10:30:00"`
    - 仅日期：`"2026-03-12"`
    - 仅时间：`"10:30:00"`
- **CheckBox**: 复选框/单选框
  - `type`: 类型 ("checkbox" 或 "radio")
- **Button**: 按钮组件
  - `primary`: 是否为主要按钮（蓝色）
  - `action`: 按钮点击动作
    - `name`: 动作名称
    - `context`: 上下文数据（可选）
- **Column**: 列布局组件
  - `alignment`: 子组件对齐方式 ("start" | "center" | "end")
    - `"center"` - 子组件居中（按钮居中必须使用此属性）
  - `spacing`: 子组件间距（数字）
- **Row**: 行布局组件
  - `alignment`: 子组件垂直对齐 ("start" | "center" | "end")
  - `distribution`: 子组件水平分布 ("start" | "center" | "end" | "spaceBetween" | "spaceAround")

## 📝 表单示例（按钮居中）

```json
[
  {"beginRendering": {"surfaceId": "default", "root": "root-column"}},
  {"surfaceUpdate": {"surfaceId": "default", "components": [
    {"id": "root-column", "component": {"Column": {
      "children": {"explicitList": ["name-field", "date-field", "time-field", "submit-button"]},
      "alignment": "center", 
      "spacing": 20
    }}},
    {"id": "name-field", "component": {"TextField": {"label": {"literalString": "姓名"}, "text": {"path": "/name"}, "textFieldType": "shortText"}}},
    {"id": "date-field", "component": {"DateTimeInput": {"value": {"path": "/date"}, "enableDate": true, "enableTime": false}}},
    {"id": "time-field", "component": {"DateTimeInput": {"value": {"path": "/time"}, "enableDate": false, "enableTime": true}}},
    {"id": "submit-button", "component": {"Button": {"child": "button-text", "primary": true, "action": {"name": "submit", "context": []}}}},
    {"id": "button-text", "component": {"Text": {"text": {"literalString": "提交"}}}}
  ]}},
  {"dataModelUpdate": {"surfaceId": "default", "path": "/", "contents": [
    {"key": "name", "valueString": ""},
    {"key": "date", "valueString": "2026-03-12"},
    {"key": "time", "valueString": "10:00:00"}
  ]}}
]
```

⚠️ **表单重要提示**：
- 所有使用 `path` 绑定的字段（TextField、DateTimeInput、MultipleChoice 等）都必须在 `dataModelUpdate` 中提供初始值
- DateTimeInput 的初始值必须是 ISO 8601 格式
- MultipleChoice 的初始值必须是数组格式，即使是单选也要用数组

"""
        
        prompt = prompt[:end_idx] + chinese_component_guide + prompt[end_idx:]
    
    return prompt


if __name__ == "__main__":
    full_prompt = generate_full_prompt()
    with open("prompt.txt", "w",encoding='utf-8') as f:  # noqa: SIM115
        f.write(full_prompt)
    print(full_prompt)
