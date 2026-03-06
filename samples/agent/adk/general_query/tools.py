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
import logging
import os

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def get_data(query: str, tool_context: ToolContext) -> str:
    """
    通用数据查询工具。
    根据用户查询内容，从 data.json 中查询匹配的数据并返回 JSON 格式。
    """
    logger.info(f"--- TOOL CALLED: get_data ---")
    logger.info(f"  - Query: {query}")
    
    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, "data.json")
        
        with open(file_path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
        
        results = query_data(all_data, query)
        logger.info(f"  -查询数据结果: {results}")
        
        return json.dumps(results, ensure_ascii=False)
        
    except FileNotFoundError:
        logger.error(f"  - Error: data.json not found at {file_path}")
        return json.dumps([])
    except Exception as e:
        logger.error(f"  - Error: {e}")
        return json.dumps([])


def query_data(data: list, query: str) -> list:
    """
    从数据中查询匹配的记录。
    """
    query_lower = query.lower().strip()
    logger.info(f"  - Query lower: {query_lower}")
    
    # 判断查询类型
    is_person_query = any(kw in query_lower for kw in ["人", "员工", "姓名", "联系", "电话", "职位", "性别", "年龄", "张三", "李四", "王五"])
    is_food_query = any(kw in query_lower for kw in ["菜", "菜品", "食物", "吃", "火锅", "牛排", "价格", "菜单", "什么菜", "有什么菜"])
    is_it_query = any(kw in query_lower for kw in ["电脑", "IT", "商品", "产品", "物品", "东西", "卖", "购物", "买"])
    
    logger.info(f"  - 查询类型判断: person={is_person_query}, food={is_food_query}, IT={is_it_query}")
    
    results = []
    
    for item in data:
        item_type = item.get("type", "")
        
        # IT 产品查询
        if is_it_query and item_type == "IT":
            product_name = item.get("商品名称", "")
            if product_name and (product_name in query or query_lower in product_name.lower()):
                results.append(item)
            else:
                # 如果查询包含 IT 关键词但没匹配具体名称，返回所有 IT 产品
                results.append(item)
        
        # 菜品查询
        elif is_food_query and item_type == "food":
            dish_name = item.get("菜品名称", "")
            if dish_name and (dish_name in query or query_lower in dish_name.lower()):
                results.append(item)
            else:
                results.append(item)
        
        # 人员查询
        elif is_person_query and item_type == "person":
            name = item.get("姓名", "")
            if name and (name in query or query_lower in name.lower()):
                results.append(item)
            else:
                results.append(item)
        
    # 如果明确查询类型但没找到匹配，返回对应类型的所有数据
    if is_it_query and not results:
        results = [item for item in data if item.get("type") == "IT"]
    elif is_food_query and not results:
        results = [item for item in data if item.get("type") == "food"]
    elif is_person_query and not results:
        results = [item for item in data if item.get("type") == "person"]
    
    if not results:
        results = []
    return results

def text_response(text: str) -> str:
    """
    如果是闲聊/问候问题，返回空字符串。
    """
    logger.info(f"--- TOOL CALLED: text_response ---")
    logger.info(f"  - 文本输入: {text}")
    return ""