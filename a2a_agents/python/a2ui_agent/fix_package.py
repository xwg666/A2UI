import os
import shutil

# Fix package structure
src_dir = r'c:\项目文件\A2UI-0302\A2UI\a2a_agents\python\a2ui_agent\src\a2ui'
dest_dir = r'C:\Users\Administrator\AppData\Local\Programs\Python\Python314\Lib\site-packages\a2ui'

# Create dest directory if needed
os.makedirs(dest_dir, exist_ok=True)

# Copy all files from src to dest
for item in os.listdir(src_dir):
    src_item = os.path.join(src_dir, item)
    dest_item = os.path.join(dest_dir, item)
    if os.path.isdir(src_item):
        if os.path.exists(dest_item):
            shutil.rmtree(dest_item)
        shutil.copytree(src_item, dest_item)
    else:
        shutil.copy2(src_item, dest_item)

print('Package restored!')

# Now test loading
from a2ui.inference.schema.loader import PackageLoader
try:
    loader = PackageLoader('a2ui.assets.0.8')
    data = loader.load('server_to_client.json')
    print('Test passed! Loaded server_to_client.json')
except Exception as e:
    print(f'Test failed: {e}')
