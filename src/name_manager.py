"""
桌面名称持久化管理模块
将桌面名称映射保存到本地文件，确保桌面 ID 变化后名称不丢失。

存储格式 (JSON):
{
    "_version": 1,
    "_last_refresh": "2026-04-22T12:00:00",
    "desktops": {
        "desktop-id-uuid-xxx": {"name": "开发"},
        "desktop-id-uuid-yyy": {"name": "工作"}
    }
}
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger("vdesk")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".vdesk-manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "desktop_names.json")

DEFAULT_CONFIG = {
    "_version": 1,
    "_last_refresh": "",
    "desktops": {},
}


def get_config_path() -> str:
    """获取配置文件路径"""
    return CONFIG_FILE


def load_names() -> dict:
    """
    加载保存的桌面名称映射
    返回: {desktop_id: name} 字典
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)

    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict) or "desktops" not in data:
            logger.warning("桌面名称配置文件格式错误，使用默认配置")
            return {}

        result = {}
        for desk_id, info in data.get("desktops", {}).items():
            if isinstance(info, str):
                result[desk_id] = info
            elif isinstance(info, dict) and "name" in info:
                result[desk_id] = info["name"]

        logger.info(f"已加载 {len(result)} 个桌面名称映射")
        return result

    except Exception as e:
        logger.error(f"加载桌面名称失败: {e}")
        return {}


def save_names(desktop_names: dict):
    """
    保存桌面名称映射
    
    :param desktop_names: {desktop_id: name} 字典
    """
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)

        data = dict(DEFAULT_CONFIG)
        data["_last_refresh"] = datetime.now().isoformat()
        data["desktops"] = desktop_names

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"已保存 {len(desktop_names)} 个桌面名称映射")

    except Exception as e:
        logger.error(f"保存桌面名称失败: {e}")


def get_persisted_name(desktop_id, default_name: str = "") -> str:
    """
    获取已保存的桌面名称，如果没有则返回默认名称
    """
    names = load_names()
    return names.get(desktop_id, default_name)


def save_single_name(desktop_id: str, name: str):
    """保存单个桌面的名称"""
    names = load_names()
    names[desktop_id] = name
    save_names(names)


def remove_name(desktop_id: str):
    """移除桌面名称映射"""
    names = load_names()
    names.pop(desktop_id, None)
    save_names(names)
