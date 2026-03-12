# Install and build the Markdown renderer
cd renderers/markdown/markdown-it
npm install
npm run build

# Install and build the Web Core library
cd ../../web_core
npm install
npm run build

# Install and build the Lit renderer
cd ../lit
npm install
npm run build

# Install and run the shell client
cd ../../samples/client/lit/shell
npm install
npm run dev


新增组件需要添加的位置：
1. specification/v0_8/json/standard_catalog_definition.json - 原始规范定义
2. A2UI\renderers\web_core\src\v0_8\schemas\standard_catalog_definition.json - 前端 Schema
3. a2a_agents/python/a2ui_agent/src/a2ui/assets/0.8/standard_catalog_definition.json - Python 加载的规范定义
4. A2UI\renderers\web_core\src\v0_8\types\components.ts
5. A2UI\renderers\web_core\src\v0_8\types\types.ts
6. A2UI\renderers\lit\src\0.8\ui\table.ts 
7. A2UI\renderers\lit\src\0.8\ui\root.ts 
8. A2UI\renderers\lit\src\0.8\ui\ui.ts
9. A2UI\samples\client\lit\shell\configs\contacts.ts   - components中添加组件
10.A2UI\samples\client\lit\shell\theme\default-theme.ts  - components中添加组件