"""
虚拟桌面核心管理模块
封装 pyvda 提供统一的虚拟桌面操作接口

适配 pyvda >= 0.5.0：
  - get_current_desktop() 已移除，改为 VirtualDesktop.current()
  - Desktop 对象有 number, id, name, go(), remove(), rename() 等属性/方法
"""

import ctypes
import logging
from typing import Optional

user32 = ctypes.windll.user32

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
