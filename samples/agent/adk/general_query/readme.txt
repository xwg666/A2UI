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


新增组件需要添加到 3 个位置 才能正常工作：
1. ✅ specification/v0_8/json/standard_catalog_definition.json - 规范定义
2. ✅ renderers/web_core/src/v0_8/schemas/server_to_client_with_standard_catalog.json - Web Core Schema
3. ✅ a2a_agents/python/a2ui_agent/src/a2ui/assets/0.8/standard_catalog_definition.json - Python 包 assets（最关键）