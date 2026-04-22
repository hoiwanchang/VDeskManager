"""
桌面切换动画控制模块

Windows 通过注册表控制桌面切换动画：
  HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced
  EnableWindowLivePreview (1=开, 0=关)

注意：
  - 此设置控制 Aero Peek 和任务视图动画
  - Windows 11 还有一个 SeparatePerMonitor=1 影响多显示器行为
  - 修改后需要注销/重启资源管理器才能生效
"""

import ctypes
import logging
import winreg as reg

logger = logging.getLogger("vdesk")

_REGISTRY_PATH = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
)


def get_switch_animation_enabled() -> bool:
    """获取桌面切换动画是否启用"""
    try:
        key = reg.OpenKey(
            reg.HKEY_CURRENT_USER,
            _REGISTRY_PATH,
            0,
            reg.KEY_READ,
        )
        value, _ = reg.QueryValueEx(key, "EnableWindowLivePreview")
        reg.CloseKey(key)
        return bool(value)
    except Exception as e:
        logger.debug(f"读取动画设置失败: {e}")
        return True  # 默认启用


def set_switch_animation_enabled(enabled: bool):
    """设置桌面切换动画开关"""
    try:
        key = reg.OpenKey(
            reg.HKEY_CURRENT_USER,
            _REGISTRY_PATH,
            0,
            reg.KEY_WRITE,
        )
        reg.SetValueEx(key, "EnableWindowLivePreview", 0, reg.REG_DWORD,
                       1 if enabled else 0)
        reg.CloseKey(key)
        logger.info(f"桌面切换动画已 {'启用' if enabled else '禁用'}")
    except Exception as e:
        logger.error(f"设置动画失败: {e}")


def toggle_switch_animation() -> bool:
    """切换动画开关"""
    current = get_switch_animation_enabled()
    set_switch_animation_enabled(not current)
    return not current
