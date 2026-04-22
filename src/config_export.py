"""
配置备份与恢复模块
将所有 VDesk Manager 配置导出为一个 JSON 文件，方便多机器同步。

导出内容包括:
- 快捷键配置
- 桌面名称映射
- 桌面预设
- 窗口自动归类规则
"""

import json
import logging
import os
import shutil
from datetime import datetime
from typing import Optional

logger = logging.getLogger("vdesk")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".vdesk-manager")


def get_backup_dir() -> str:
    """获取备份目录"""
    backup_dir = os.path.join(CONFIG_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def export_all_config(output_path: Optional[str] = None) -> str:
    """
    导出所有配置到一个 JSON 文件
    
    :param output_path: 输出路径，如果为 None 则自动生成带时间戳的文件名
    :return: 导出文件路径
    """
    backup_dir = get_backup_dir()
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(backup_dir, f"vdesk-config-{timestamp}.json")

    config = {
        "_export_version": 1,
        "_export_time": datetime.now().isoformat(),
        "sources": {},
    }

    # 读取各配置文件
    files_to_export = {
        "hotkeys": os.path.join(CONFIG_DIR, "hotkeys.json"),
        "desktop_names": os.path.join(CONFIG_DIR, "desktop_names.json"),
        "desktop_sets": os.path.join(CONFIG_DIR, "desktop_sets.json"),
        "win_autoroute": os.path.join(CONFIG_DIR, "win_autoroute.json"),
    }

    for key, filepath in files_to_export.items():
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config["sources"][key] = json.load(f)
                logger.info(f"已导出配置: {key}")
            except Exception as e:
                logger.warning(f"导出配置 {key} 失败: {e}")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"配置已导出到: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"导出配置失败: {e}")
        raise


def import_config(input_path: str) -> bool:
    """
    从 JSON 文件导入配置
    
    :param input_path: 导入文件路径
    :return: 是否成功
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"读取导入文件失败: {e}")
        return False

    if not isinstance(config, dict) or "sources" not in config:
        logger.error("导入文件格式错误")
        return False

    os.makedirs(CONFIG_DIR, exist_ok=True)
    success_count = 0

    # 将各配置文件复制到目标路径
    target_files = {
        "hotkeys": os.path.join(CONFIG_DIR, "hotkeys.json"),
        "desktop_names": os.path.join(CONFIG_DIR, "desktop_names.json"),
        "desktop_sets": os.path.join(CONFIG_DIR, "desktop_sets.json"),
        "win_autoroute": os.path.join(CONFIG_DIR, "win_autoroute.json"),
    }

    for key, filepath in target_files.items():
        if key in config.get("sources", {}):
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config["sources"][key], f, indent=2, ensure_ascii=False)
                logger.info(f"已导入配置: {key}")
                success_count += 1
            except Exception as e:
                logger.error(f"导入配置 {key} 失败: {e}")

    logger.info(f"配置导入完成，成功 {success_count}/{len(target_files)} 项")
    return success_count > 0


def list_backups() -> list[str]:
    """列出所有备份文件"""
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        return []
    files = []
    for f in sorted(os.listdir(backup_dir)):
        if f.startswith("vdesk-config-") and f.endswith(".json"):
            filepath = os.path.join(backup_dir, f)
            size = os.path.getsize(filepath)
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")
            files.append(f"{f} ({size} bytes, {mtime})")
    return files


def cleanup_backups(keep: int = 10):
    """清理旧备份，只保留最近的 N 个"""
    backup_dir = get_backup_dir()
    files = sorted(
        [(f, os.path.getmtime(os.path.join(backup_dir, f)))
         for f in os.listdir(backup_dir)
         if f.startswith("vdesk-config-") and f.endswith(".json")],
        key=lambda x: x[1],
        reverse=True,
    )
    if len(files) <= keep:
        return
    for f, _ in files[keep:]:
        try:
            os.unlink(os.path.join(backup_dir, f))
            logger.info(f"清理旧备份: {f}")
        except Exception as e:
            logger.error(f"清理备份失败: {e}")
