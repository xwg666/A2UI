import json
import logging
import os

logger = logging.getLogger(__name__)

PEOPLE_DATA = [
    {"id": "1", "name": "张三", "department": "技术部", "position": "高级工程师", "email": "zhangsan@example.com", "phone": "138-0000-0001"},
    {"id": "2", "name": "李四", "department": "产品部", "position": "产品经理", "email": "lisi@example.com", "phone": "138-0000-0002"},
    {"id": "3", "name": "王五", "department": "技术部", "position": "前端工程师", "email": "wangwu@example.com", "phone": "138-0000-0003"},
    {"id": "4", "name": "赵六", "department": "设计部", "position": "UI设计师", "email": "zhaoliu@example.com", "phone": "138-0000-0004"},
    {"id": "5", "name": "孙七", "department": "技术部", "position": "后端工程师", "email": "sunqi@example.com", "phone": "138-0000-0005"},
    {"id": "6", "name": "周八", "department": "市场部", "position": "市场经理", "email": "zhouba@example.com", "phone": "138-0000-0006"},
    {"id": "7", "name": "吴九", "department": "人事部", "position": "HR专员", "email": "wujiu@example.com", "phone": "138-0000-0007"},
    {"id": "8", "name": "郑十", "department": "财务部", "position": "财务主管", "email": "zhengshi@example.com", "phone": "138-0000-0008"},
]


def get_people(name: str = "", department: str = "") -> str:
    """
    查询人员信息。
    name: 人员姓名（可选，支持模糊匹配）
    department: 部门名称（可选）
    返回: 匹配的人员列表 JSON 字符串
    """
    logger.info(f"--- TOOL: get_people called with name='{name}', department='{department}' ---")
    
    results = PEOPLE_DATA
    
    if name:
        results = [p for p in results if name.lower() in p["name"].lower()]
    
    if department:
        results = [p for p in results if department.lower() in p["department"].lower()]
    
    logger.info(f"--- TOOL: Found {len(results)} people ---")
    return json.dumps(results, ensure_ascii=False)
