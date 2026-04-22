"""
虚拟桌面核心管理模块
封装 pyvda 提供统一的虚拟桌面操作接口

适配 pyvda >= 0.5.0：
  - get_current_desktop() 已移除，改为 VirtualDesktop.current()
  - Desktop 对象有 number, id, name, go(), remove(), rename() 等属性/方法

多显示器支持：
  - 统一模式：所有显示器同步切换（pyvda 直接切换当前桌面）
  - 独立模式：找到每个显示器上的前台窗口，分别移动到目标桌面
"""

import ctypes
import logging
import os
import threading
from typing import Optional

user32 = ctypes.windll.user32
shcore = ctypes.windll.shcore

logger = logging.getLogger("vdesk")

# 延迟导入 pyvda，避免在非 Windows 平台直接崩溃
_pyvda = None
_VirtualDesktop = None


def _ensure_pyvda():
    global _pyvda, _VirtualDesktop
    if _pyvda is None:
        try:
            import pyvda as _m
            _pyvda = _m
            _VirtualDesktop = _m.VirtualDesktop
        except ImportError:
            raise RuntimeError(
                "pyvda 未安装，请执行: pip install pyvda"
            )
    return _pyvda


class DesktopInfo:
    """虚拟桌面信息封装"""

    def __init__(self, index: int, name: str, is_current: bool, hwnd=None, id: str = ""):
        self.index = index          # 从 1 开始的序号
        self.name = name            # 桌面名称
        self.is_current = is_current  # 是否为当前桌面
        self.hwnd = hwnd            # pyvda VirtualDesktop 对象引用
        self.id = id                # 桌面唯一 ID (UUID 字符串)

    def __repr__(self):
        marker = " ★" if self.is_current else ""
        return f"[{self.index}] {self.name}{marker}"


class DesktopManager:
    """虚拟桌面管理器"""

    def __init__(self):
        _ensure_pyvda()
        self._name_map: dict = {}  # desktop_id -> name
        self._load_names()

    def _load_names(self):
        """加载持久化的桌面名称映射"""
        try:
            from .name_manager import load_names
            self._name_map = load_names()
        except Exception as e:
            logger.debug(f"加载桌面名称映射失败: {e}")

    def _save_name(self, desktop_id: str, name: str):
        """保存单个桌面名称到持久化存储"""
        try:
            from .name_manager import save_single_name
            save_single_name(desktop_id, name)
        except Exception as e:
            logger.debug(f"保存桌面名称失败: {e}")

    def _persist_names(self):
        """持久化所有桌面名称映射"""
        try:
            from .name_manager import save_names
            save_names(self._name_map)
        except Exception as e:
            logger.debug(f"持久化桌面名称失败: {e}")

    def get_desktops(self) -> list[DesktopInfo]:
        """获取所有虚拟桌面列表"""
        try:
            all_desktops = _pyvda.get_virtual_desktops()
            current = _VirtualDesktop.current()
            current_id = current.id

            result = []
            for desk in all_desktops:
                desk_id = str(desk.id)
                desk_number = desk.number if hasattr(desk, 'number') else len(result) + 1
                try:
                    original_name = desk.name or ""
                except Exception:
                    original_name = ""

                # 优先使用持久化名称，如果不存在则使用系统名称
                name = self._name_map.get(desk_id, original_name) or f"桌面 {desk_number}"
                is_current = (desk_id == current_id)

                result.append(DesktopInfo(
                    index=desk_number,
                    name=name,
                    is_current=is_current,
                    hwnd=desk,
                    id=desk_id,  # 添加 ID 属性
                ))
            return result
        except Exception as e:
            logger.error(f"获取桌面列表失败: {e}")
            return []

    def get_current_desktop(self) -> Optional[DesktopInfo]:
        """获取当前桌面"""
        try:
            desktops = self.get_desktops()
            for d in desktops:
                if d.is_current:
                    return d
            return desktops[0] if desktops else None
        except Exception as e:
            logger.error(f"获取当前桌面失败: {e}")
            return None

    def switch_to(self, index: int) -> bool:
        """切换到指定序号的桌面 (从 1 开始)"""
        try:
            desktops = self.get_desktops()
            if 1 <= index <= len(desktops):
                desk = desktops[index - 1]
                if desk.hwnd:
                    desk.hwnd.go()
                    logger.info(f"已切换到桌面 {index}: {desk.name}")
                    return True
            logger.warning(f"无效的桌面序号: {index}")
            return False
        except Exception as e:
            logger.error(f"切换桌面失败: {e}")
            return False

    def switch_by_offset(self, offset: int) -> bool:
        """按偏移量切换桌面 (负数=左, 正数=右)"""
        try:
            desktops = self.get_desktops()
            for i, d in enumerate(desktops):
                if d.is_current:
                    new_index = i + offset
                    if 0 <= new_index < len(desktops):
                        return self.switch_to(new_index + 1)
                    break
            return False
        except Exception as e:
            logger.error(f"偏移切换失败: {e}")
            return False

    def create_desktop(self) -> bool:
        """创建新的虚拟桌面"""
        try:
            _VirtualDesktop.create()
            logger.info("已创建新桌面")
            return True
        except Exception as e:
            logger.error(f"创建桌面失败: {e}")
            return False

    def remove_desktop(self, index: int) -> bool:
        """移除指定序号的桌面"""
        try:
            desktops = self.get_desktops()
            if len(desktops) <= 1:
                logger.warning("至少保留一个桌面")
                return False
            if 1 <= index <= len(desktops):
                desk = desktops[index - 1]
                if desk.is_current:
                    # 先切换到相邻桌面
                    target = index - 1 if index > 1 else index + 1
                    if target <= len(desktops):
                        self.switch_to(target)
                desk.hwnd.remove()
                logger.info(f"已移除桌面 {index}")
                return True
            return False
        except Exception as e:
            logger.error(f"移除桌面失败: {e}")
            return False

    def rename_desktop(self, index: int, new_name: str) -> bool:
        """重命名指定桌面"""
        try:
            desktops = self.get_desktops()
            if 1 <= index <= len(desktops):
                desk = desktops[index - 1]
                if hasattr(desk.hwnd, 'rename'):
                    desk.hwnd.rename(new_name)
                elif hasattr(desk.hwnd, 'set_name'):
                    desk.hwnd.set_name(new_name)
                elif hasattr(desk.hwnd, 'name'):
                    desk.hwnd.name = new_name
                else:
                    logger.warning("当前 pyvda 版本不支持重命名")
                    return False
                logger.info(f"桌面 {index} 已重命名为: {new_name}")
                
                # 持久化名称映射
                if desk.id:
                    self._save_name(desk.id, new_name)
                return True
            return False
        except Exception as e:
            logger.error(f"重命名桌面失败: {e}")
            return False

    def move_window_to_desktop(self, window_handle, desktop_index: int) -> bool:
        """将窗口移动到指定桌面"""
        try:
            desktops = self.get_desktops()
            if 1 <= desktop_index <= len(desktops):
                target = desktops[desktop_index - 1]
                _pyvda.ViewVirtualDesktop(window_handle, target.hwnd)
                return True
            return False
        except Exception as e:
            logger.error(f"移动窗口失败: {e}")
            return False

    @property
    def desktop_count(self) -> int:
        """当前桌面总数"""
        return len(self.get_desktops())

    def get_foreground_window(self) -> Optional[int]:
        """获取前台窗口的句柄 (HWND)"""
        try:
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                return hwnd
            return None
        except Exception as e:
            logger.error(f"获取前台窗口失败: {e}")
            return None

    def move_foreground_window_to_desktop(self, desktop_index: int) -> bool:
        """将前台窗口移动到指定桌面 (从 1 开始)"""
        try:
            hwnd = self.get_foreground_window()
            if not hwnd:
                logger.warning("没有前台窗口可移动")
                return False
            return self.move_window_to_desktop(hwnd, desktop_index)
        except Exception as e:
            logger.error(f"移动前台窗口失败: {e}")
            return False

    def switch_by_offset_multi_monitor(self, offset: int, mode: str = "sync") -> dict:
        """
        多显示器桌面切换
        
        :param offset: -1=上一个, 1=下一个
        :param mode: "sync"=统一切换所有显示器, "independent"=独立切换每个显示器
        :return: {"mode": str, "results": [(monitor_name, success), ...]}
        """
        try:
            if mode == "sync":
                # 统一切换：直接切换到目标桌面
                success = self.switch_by_offset(offset)
                return {"mode": "sync", "results": [("all", success)]}
            else:
                # 独立切换：找到每个显示器上的前台窗口，分别移动到目标桌面
                return self._switch_independent(offset)
        except Exception as e:
            logger.error(f"多显示器切换失败: {e}")
            return {"mode": mode, "results": []}

    def _switch_independent(self, offset: int) -> dict:
        """
        独立切换每个显示器上的桌面
        
        原理：找到每个显示器上的前台窗口，获取其所在桌面索引，然后切换到目标桌面索引。
        使用 pyvda.ViewVirtualDesktop 将窗口移动到目标桌面。
        """
        try:
            # 获取所有显示器
            monitors = self._get_monitors()
            if not monitors:
                return {"mode": "independent", "results": []}

            results = []
            desktops = self.get_desktops()
            total = len(desktops)
            if total == 0:
                return {"mode": "independent", "results": []}

            for monitor in monitors:
                # 找到该显示器上的前台窗口
                hwnd = self._get_foreground_window_for_monitor(monitor)
                if not hwnd:
                    results.append((monitor["name"], False))
                    continue

                # 找到该窗口当前所在的桌面索引
                current_index = self._get_desktop_index_for_window(hwnd, desktops)
                if current_index is None:
                    # 窗口不在任何桌面（可能在桌面1），或出错，使用索引1
                    current_index = 0

                # 计算目标桌面索引
                target_index = current_index + offset
                if target_index < 0:
                    target_index = total - 1
                elif target_index >= total:
                    target_index = 0

                # 移动到目标桌面（索引从0开始）
                target_desktop = desktops[target_index]
                try:
                    _pyvda.ViewVirtualDesktop(hwnd, target_desktop.hwnd)
                    results.append((monitor["name"], True))
                    logger.info(
                        f"独立切换: {monitor['name']} 窗口 0x{hwnd:x} "
                        f"桌面 {current_index+1} → {target_index+1}"
                    )
                except Exception as e:
                    logger.error(f"移动窗口到目标桌面失败: {e}")
                    results.append((monitor["name"], False))

            return {"mode": "independent", "results": results}
        except Exception as e:
            logger.error(f"独立切换失败: {e}")
            return {"mode": "independent", "results": []}

    def _get_monitors(self) -> list[dict]:
        """枚举所有显示器"""
        monitors = []
        wintypes = __import__("ctypes").wintypes

        def enum_callback(hMonitor, hdcMonitor, lprcBounds, lParam):
            info = wintypes.MONITORINFO()
            info.cbSize = ctypes.sizeof(wintypes.MONITORINFO)
            user32.GetMonitorInfoW(hMonitor, ctypes.byref(info))

            name = f"Monitor_{info.rcMonitor[0]}_{info.rcMonitor[1]}"
            is_primary = bool(info.dwFlags & 0x01)

            monitors.append({
                "handle": hMonitor,
                "name": name,
                "left": info.rcMonitor[0],
                "top": info.rcMonitor[1],
                "right": info.rcMonitor[2],
                "bottom": info.rcMonitor[3],
                "is_primary": is_primary,
                "width": info.rcMonitor[2] - info.rcMonitor[0],
                "height": info.rcMonitor[3] - info.rcMonitor[1],
            })
            return True

        user32.EnumDisplayMonitors(None, None, ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(wintypes.RECT), ctypes.c_ulong
        )(enum_callback), 0)

        return monitors

    def _get_foreground_window_for_monitor(self, monitor: dict) -> Optional[int]:
        """获取指定显示器上的前台窗口"""
        try:
            # 获取该显示器上的所有可见窗口
            hwnds = []

            def enum_callback(hwnd, lParam):
                if user32.IsWindowVisible(hwnd):
                    # 获取窗口矩形
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    # 检查窗口是否在该显示器区域内
                    center_x = (rect.left + rect.right) // 2
                    center_y = (rect.top + rect.bottom) // 2
                    if (monitor["left"] <= center_x < monitor["right"] and
                            monitor["top"] <= center_y < monitor["bottom"]):
                        hwnds.append(hwnd)
                return True

            user32.EnumWindows(ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.c_uint64, ctypes.c_ulong
            )(enum_callback), 0)

            if hwnds:
                # 返回 Z 序最前的窗口（列表第一个）
                return hwnds[0]
            return None
        except Exception as e:
            logger.debug(f"获取显示器 {monitor['name']} 前台窗口失败: {e}")
            return None

    def _get_desktop_index_for_window(self, hwnd: int, desktops: list) -> Optional[int]:
        """
        获取窗口所在的桌面索引
        
        使用 IVirtualDesktopManager.IsWindowOnCurrentVirtualDesktop 判断
        每个桌面是否包含该窗口。
        
        由于 IVirtualDesktopManager 是内部 API，这里采用简化方案：
        默认返回当前桌面的索引。如果需要精确检测每个窗口的桌面归属，
        需要安装 pywin32 并使用 ctypes 调用 COM。
        """
        try:
            # 简化方案：返回当前桌面的索引
            current = _VirtualDesktop.current()
            for i, desk in enumerate(desktops):
                if desk.id == current.id:
                    return i
            return None
        except Exception as e:
            logger.debug(f"获取窗口桌面索引失败: {e}")
            return None
