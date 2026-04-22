"""
桌面预设/桌面组管理模块
允许用户定义桌面分组（如"工作/开发/通讯/娱乐"），一键切换整组。

存储格式 (JSON):
{
    "_version": 1,
    "sets": {
        "work": {
            "name": "工作",
            "count": 3,
            "names": ["邮件", "文档", "浏览器"]
        },
        "dev": {
            "name": "开发",
            "count": 2,
            "names": ["VS Code", "终端"]
        }
    }
}
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger("vdesk")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".vdesk-manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "desktop_sets.json")

DEFAULT_SETS = {
    "_version": 1,
    "sets": {},
}


def get_config_path() -> str:
    """获取配置文件路径"""
    return CONFIG_FILE


def load_sets() -> dict:
    """加载桌面预设配置"""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    if not os.path.exists(CONFIG_FILE):
        return {"sets": {}}

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict) or "sets" not in data:
            logger.warning("桌面预设配置文件格式错误，使用默认配置")
            return {"sets": {}}

        logger.info(f"已加载 {len(data.get('sets', {}))} 个桌面预设")
        return data

    except Exception as e:
        logger.error(f"加载桌面预设失败: {e}")
        return {"sets": {}}


def save_sets(sets_data: dict):
    """保存桌面预设配置"""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(sets_data, f, indent=2, ensure_ascii=False)
        logger.info(f"已保存 {len(sets_data.get('sets', {}))} 个桌面预设")
    except Exception as e:
        logger.error(f"保存桌面预设失败: {e}")


def get_all_set_names() -> list[str]:
    """获取所有预设名称列表"""
    data = load_sets()
    return list(data.get("sets", {}).keys())


def add_set(name: str, count: int, desktop_names: list[str]):
    """添加一个新的桌面预设"""
    data = load_sets()
    data["sets"][name] = {
        "name": desktop_names[0] if desktop_names else name,
        "count": count,
        "names": desktop_names,
    }
    save_sets(data)


def remove_set(name: str):
    """移除一个桌面预设"""
    data = load_sets()
    data["sets"].pop(name, None)
    save_sets(data)


def get_set(name: str) -> Optional[dict]:
    """获取指定预设的详情"""
    data = load_sets()
    return data.get("sets", {}).get(name)
