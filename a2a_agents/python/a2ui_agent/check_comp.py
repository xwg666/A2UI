from a2ui.inference.schema.loader import PackageLoader
import json

loader = PackageLoader('a2ui.assets.0.8')
data = loader.load('standard_catalog_definition.json')
components = data.get('components', {})
print('FileUpload:', 'FileUpload' in components)
print('Table:', 'Table' in components)
print('组件列表:', list(components.keys())[-5:])
