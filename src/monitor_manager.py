"""
多显示器虚拟桌面管理模块

Windows 11 支持"每个屏幕独立虚拟桌面"，Windows 10 默认统一切换。
本模块提供两种模式：
  - 统一模式：所有显示器同步切换到同一桌面的下一个/上一个
  - 独立模式：每个显示器各自切换到其同级桌面（鼠标在哪个显示器就切换哪个）

切换方式：
  - 统一：直接调用 pyvda 切换当前桌面（对所有显示器生效）
  - 独立：找到每个显示器上的前台窗口，分别移动到目标桌面
"""

import ctypes
import logging
import threading
import time
from ctypes import wintypes
from typing import Callable, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

logger = logging.getLogger("vdesk")

# 显示器信息
class MonitorInfo:
    """显示器信息"""
    def __init__(self, handle, name, left, top, right, bottom, is_primary):
        self.handle = handle           # HMONITOR
        self.name = name
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.width = right - left
        self.height = bottom - top
        self.is_primary = is_primary
        self.center_x = left + self.width // 2
        self.center_y = top + self.height // 2

    @property
    def center(self):
        return (self.center_x, self.center_y)

    def __repr__(self):
        primary = " ★" if self.is_primary else ""
        return f"Monitor({self.name}{primary} {self.width}x{self.height} @{self.left},{self.top})"


# ── 回调配置 ──
# 每个显示器一个回调，用于切换桌面
_MONITORS: list[MonitorInfo] = []
_SWITCH_CALLBACKS: dict[str, Optional[Callable]] = {}  # monitor_name -> callback(index)
_SYNC_CALLBACKS: list[Callable] = []  # 统一切换回调


def get_monitors() -> list[MonitorInfo]:
    """枚举所有显示器"""
    global _MONITORS
    if _MONITORS:
        return _MONITORS

    monitors = []

    def enum_callback(hMonitor, hdcMonitor, lprcBounds, lParam):
        info = wintypes.MONITORINFO()
        info.cbSize = ctypes.sizeof(wintypes.MONITORINFO)
        user32.GetMonitorInfoW(hMonitor, ctypes.byref(info))

        # 获取显示器名称
        name = f"Monitor_{info.rcMonitor[0]}_{info.rcMonitor[1]}"
        is_primary = bool(info.dwFlags & 0x01)  # MONITORINFOF_PRIMARY

        monitors.append(MonitorInfo(
            handle=hMonitor,
            name=name,
            left=info.rcMonitor[0],
            top=info.rcMonitor[1],
            right=info.rcMonitor[2],
            bottom=info.rcMonitor[3],
            is_primary=is_primary,
        ))
        return True

    user32.EnumDisplayMonitors(None, None, ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(wintypes.RECT), ctypes.c_ulong
    )(enum_callback), 0)

    _MONITORS = monitors
    logger.info(f"检测到 {len(monitors)} 个显示器: {', '.join(str(m) for m in monitors)}")
    return monitors


def set_switch_callback(monitor_name: str, callback: Optional[Callable]):
    """为指定显示器设置桌面切换回调"""
    _SWITCH_CALLBACKS[monitor_name] = callback


def set_sync_callback(callback: Callable):
    """设置统一切换回调"""
    if callback not in _SYNC_CALLBACKS:
        _SYNC_CALLBACKS.append(callback)


def remove_sync_callback(callback: Callable):
    """移除统一切换回调"""
    _SYNC_CALLBACKS[:] = [cb for cb in _SYNC_CALLBACKS if cb != callback]


def switch_all_desktops(offset: int) -> list[tuple[str, bool]]:
    """
    统一切换所有显示器上的桌面
    
    :param offset: -1=上一个, 1=下一个
    :return: [(monitor_name, success), ...]
    """
    results = []
    for cb in _SYNC_CALLBACKS:
        try:
            cb(offset)
            results.append(("all", True))
        except Exception as e:
            logger.error(f"统一切换失败: {e}")
            results.append(("all", False))
    return results


def switch_independent_desktops(offset: int) -> list[tuple[str, bool]]:
    """
    独立切换每个显示器上的桌面
    
    找到每个显示器上最靠近中心的前台窗口，分别切换到对应桌面
    
    :param offset: -1=上一个, 1=下一个
    :return: [(monitor_name, success), ...]
    """
    monitors = get_monitors()
    if not monitors:
        return []

    results = []
    for monitor in monitors:
        callback = _SWITCH_CALLBACKS.get(monitor.name)
        if not callback:
            continue

        try:
            callback(offset)
            results.append((monitor.name, True))
        except Exception as e:
            logger.error(f"独立切换显示器 {monitor.name} 失败: {e}")
            results.append((monitor.name, False))
    return results


def get_mouse_monitor() -> Optional[MonitorInfo]:
    """获取鼠标所在的显示器"""
    pt = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        return None

    hMonitor = user32.MonitorFromPoint(pt, 0x00000002)  # MONITOR_DEFAULTTONEAREST
    for m in get_monitors():
        if m.handle == hMonitor:
            return m
    return None


def get_foreground_monitor() -> Optional[MonitorInfo]:
    """获取包含前台窗口的显示器"""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        pt = wintypes.POINT()
        user32.GetWindowRect(hwnd, ctypes.byref(wintypes.RECT()))
        # 获取窗口中心点
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        cx = (rect.left + rect.right) // 2
        cy = (rect.top + rect.bottom) // 2

        hMonitor = user32.MonitorFromPoint(wintypes.POINT(cx, cy), 0x00000002)
        for m in get_monitors():
            if m.handle == hMonitor:
                return m
    except Exception as e:
        logger.debug(f"获取前台显示器失败: {e}")
    return None
