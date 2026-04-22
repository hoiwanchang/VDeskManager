"""
系统托盘指示器模块
使用 pystray 构建右键菜单，实现虚拟桌面的快速切换和管理

pystray 回调约定：
  action 回调签名 = (icon, item)，即两个位置参数
  checked 回调签名 = (menu_item)，即一个位置参数
  需要携带额外参数的 action 使用 _make_xxx_action() 工厂方法闭包捕获
"""

import logging
import threading
import time
from typing import Callable, Optional

import pystray
from PIL import Image

from .desktop_manager import DesktopManager, DesktopInfo
from .icon_generator import generate_tray_icon

logger = logging.getLogger("vdesk")


class TrayIconApp:
    """系统托盘虚拟桌面管理应用"""

    def __init__(self, poll_interval: float = 1.0):
        """
        :param poll_interval: 轮询桌面变化的间隔（秒）
        """
        self.manager = DesktopManager()
        self.poll_interval = poll_interval
        self._icon: Optional[pystray.Icon] = None
        self._running = False
        self._last_desktop_count = 0
        self._last_current_index = 0
        self._poll_thread: Optional[threading.Thread] = None
        self._rename_dialog_active = False
        self._refresh_lock = threading.Lock()

        # 快捷键管理器（由 main.py 设置）
        self.hotkey_manager = None

    def _create_icon(self) -> pystray.Icon:
        """创建托盘图标"""
        desktops = self.manager.get_desktops()
        current = self._find_current(desktops)
        current_idx = current.index if current else 1
        total = len(desktops) or 1

        icon_image = generate_tray_icon(current_idx, total)

        icon = pystray.Icon(
            name="VDesk Manager",
            icon=icon_image,
            title=self._build_tooltip(desktops),
            menu=self._build_menu(desktops),
        )
        return icon

    def _build_tooltip(self, desktops: list[DesktopInfo]) -> str:
        """构建鼠标悬停提示"""
        if not desktops:
            return "VDesk Manager - 虚拟桌面管理器"
        current = self._find_current(desktops)
        if current:
            return f"VDesk Manager | 当前: {current.name} ({current.index}/{len(desktops)})"
        return f"VDesk Manager | {len(desktops)} 个桌面"

    def _build_menu(self, desktops: list[DesktopInfo]) -> pystray.Menu:
        """构建右键菜单"""
        items = []
        current = self._find_current(desktops)
        current_idx = current.index if current else 0
        total = len(desktops)

        # ── 状态信息 ──
        status_text = f"当前桌面: {current_idx} / {total}"
        items.append(pystray.MenuItem(
            status_text,
            lambda icon, item: None,
            enabled=False,
        ))

        items.append(pystray.Menu.SEPARATOR)

        # ── 桌面列表（快速切换）──
        for desk in desktops:
            label = f"{'● ' if desk.is_current else '  '}{desk.name}"
            items.append(pystray.MenuItem(
                label,
                self._make_switch_action(desk.index),
                checked=lambda item, idx=desk.index: self._is_current(idx),
                radio=True,
            ))

        items.append(pystray.Menu.SEPARATOR)

        # ── 导航操作 ──
        items.append(pystray.MenuItem("◀  上一个桌面", self._action_prev))
        items.append(pystray.MenuItem("▶  下一个桌面", self._action_next))

        items.append(pystray.Menu.SEPARATOR)

        # ── 管理操作 ──
        items.append(pystray.MenuItem("＋ 新建桌面", self._action_create))

        # 删除桌面子菜单
        if len(desktops) > 1:
            remove_items = []
            for desk in desktops:
                remove_items.append(pystray.MenuItem(
                    f"删除: {desk.name}",
                    self._make_remove_action(desk.index),
                ))
            items.append(pystray.MenuItem("✕ 删除桌面", pystray.Menu(*remove_items)))

        # 重命名桌面子菜单
        rename_items = []
        for desk in desktops:
            rename_items.append(pystray.MenuItem(
                f"重命名: {desk.name}",
                self._make_rename_action(desk.index),
            ))
        items.append(pystray.MenuItem("✎ 重命名桌面", pystray.Menu(*rename_items)))

        items.append(pystray.Menu.SEPARATOR)

        # ── 快捷键设置 ──
        if self.hotkey_manager:
            hk_items = []
            hk_items.append(pystray.MenuItem("✎ 编辑配置文件", self._action_edit_hotkeys))
            hk_items.append(pystray.MenuItem("↻  重新加载快捷键", self._action_reload_hotkeys))
            items.append(pystray.MenuItem("⌨ 快捷键", pystray.Menu(*hk_items)))

        # ── 其他 ──
        items.append(pystray.MenuItem("⊞ 打开任务视图", self._action_task_view))

        # ── 开机自启动 ──
        items.append(pystray.MenuItem(
            "🚀 开机自启动",
            self._action_toggle_autostart,
            checked=lambda item: self._is_autostart_enabled(),
        ))

        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("退出 VDesk Manager", self._action_exit))

        return pystray.Menu(*items)

    def _find_current(self, desktops: list[DesktopInfo]) -> Optional[DesktopInfo]:
        for d in desktops:
            if d.is_current:
                return d
        return desktops[0] if desktops else None

    def _is_current(self, index: int) -> bool:
        desktops = self.manager.get_desktops()
        for d in desktops:
            if d.index == index and d.is_current:
                return True
        return False

    def _refresh(self):
        """刷新托盘图标和菜单（线程安全）"""
        with self._refresh_lock:
            try:
                desktops = self.manager.get_desktops()
                current = self._find_current(desktops)
                current_idx = current.index if current else 1
                total = len(desktops) or 1

                if self._icon:
                    self._icon.icon = generate_tray_icon(current_idx, total)
                    self._icon.title = self._build_tooltip(desktops)
                    self._icon.menu = self._build_menu(desktops)

                self._last_desktop_count = total
                self._last_current_index = current_idx
            except Exception as e:
                logger.error(f"刷新托盘失败: {e}")

    def _schedule_refresh(self, delay: float = 0.3):
        """在后台线程中延迟刷新"""
        def _do_refresh():
            time.sleep(delay)
            self._refresh()
        t = threading.Thread(target=_do_refresh, daemon=True, name="VDesk-Refresh")
        t.start()

    def _run_in_thread(self, func, *args, **kwargs):
        """在后台线程中执行操作，避免阻塞 pystray 消息循环"""
        def _worker():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"操作执行失败: {e}")
        t = threading.Thread(target=_worker, daemon=True, name="VDesk-Action")
        t.start()

    def _poll_desktop_changes(self):
        """后台轮询桌面变化"""
        while self._running:
            try:
                desktops = self.manager.get_desktops()
                total = len(desktops)
                current = self._find_current(desktops)
                current_idx = current.index if current else 0

                if total != self._last_desktop_count or current_idx != self._last_current_index:
                    logger.debug(f"桌面变化: count={total}, current={current_idx}")
                    self._refresh()
            except Exception as e:
                logger.error(f"轮询出错: {e}")

            time.sleep(self.poll_interval)

    # ── 菜单动作（pystray action 回调签名: (icon, item)）──

    def _make_switch_action(self, index: int):
        """创建切换桌面的 action 回调（闭包捕获 index）"""
        def action(icon, item):
            def _do():
                self.manager.switch_to(index)
                self._schedule_refresh(delay=0.2)
            self._run_in_thread(_do)
        return action

    def _action_prev(self, icon, item):
        def _do():
            self.manager.switch_by_offset(-1)
            self._schedule_refresh(delay=0.2)
        self._run_in_thread(_do)

    def _action_next(self, icon, item):
        def _do():
            self.manager.switch_by_offset(1)
            self._schedule_refresh(delay=0.2)
        self._run_in_thread(_do)

    def _action_create(self, icon, item):
        def _do():
            self.manager.create_desktop()
            self._schedule_refresh(delay=0.4)
        self._run_in_thread(_do)

    def _make_remove_action(self, index: int):
        """创建删除桌面的 action 回调"""
        def action(icon, item):
            def _do():
                self.manager.remove_desktop(index)
                self._schedule_refresh(delay=0.4)
            self._run_in_thread(_do)
        return action

    def _make_rename_action(self, index: int):
        """创建重命名桌面的 action 回调"""
        def action(icon, item):
            if self._rename_dialog_active:
                return
            self._rename_dialog_active = True
            def _do():
                try:
                    self._show_rename_dialog(index)
                finally:
                    self._rename_dialog_active = False
            self._run_in_thread(_do)
        return action

    def _show_rename_dialog(self, index: int):
        """弹出重命名对话框（使用 tkinter）"""
        try:
            import tkinter as tk
            from tkinter import simpledialog

            desktops = self.manager.get_desktops()
            old_name = desktops[index - 1].name if index <= len(desktops) else ""

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            new_name = simpledialog.askstring(
                "重命名桌面",
                f"输入新名称 (桌面 {index}):",
                initialvalue=old_name,
                parent=root,
            )
            root.destroy()

            if new_name and new_name.strip():
                self.manager.rename_desktop(index, new_name.strip())
                self._schedule_refresh(delay=0.2)
        except ImportError:
            logger.warning("tkinter 不可用，无法弹出重命名对话框")
        except Exception as e:
            logger.error(f"重命名对话框失败: {e}")

    def _action_task_view(self, icon, item):
        """模拟 Win+Tab 打开任务视图"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            KEYEVENTF_KEYUP = 0x0002

            user32.keybd_event(0x5B, 0, 0, 0)                   # Win down
            user32.keybd_event(0x09, 0, 0, 0)                   # Tab down
            user32.keybd_event(0x09, 0, KEYEVENTF_KEYUP, 0)     # Tab up
            user32.keybd_event(0x5B, 0, KEYEVENTF_KEYUP, 0)     # Win up

            logger.info("已打开任务视图")
        except Exception as e:
            logger.error(f"打开任务视图失败: {e}")

    def _action_edit_hotkeys(self, icon, item):
        """打开快捷键配置文件"""
        if self.hotkey_manager:
            self.hotkey_manager.open_config_file()

    def _action_reload_hotkeys(self, icon, item):
        """重新加载快捷键配置"""
        if self.hotkey_manager:
            self.hotkey_manager.reload()

    def _is_autostart_enabled(self) -> bool:
        """检查开机自启动是否已启用"""
        try:
            from .autostart import is_auto_start_enabled
            return is_auto_start_enabled()
        except Exception:
            return False

    def _action_toggle_autostart(self, icon, item):
        """切换开机自启动"""
        def _do():
            try:
                from .autostart import toggle_auto_start
                success, now_enabled = toggle_auto_start()
                if success:
                    state = "已启用" if now_enabled else "已禁用"
                    logger.info(f"开机自启动{state}")
                    self._icon.notify(f"开机自启动{state}", "VDesk Manager")
                else:
                    logger.error("切换开机自启动失败")
                    self._icon.notify("操作失败，请查看日志", "VDesk Manager")
            except Exception as e:
                logger.error(f"切换自启动失败: {e}")
            self._schedule_refresh(delay=0.3)
        self._run_in_thread(_do)

    def _action_exit(self, icon, item):
        """退出应用"""
        self._running = False
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        if self._icon:
            self._icon.stop()

    # ── 生命周期 ──

    def run(self):
        """启动托盘应用（阻塞主线程）"""
        logger.info("VDesk Manager 启动中...")
        self._running = True
        self._icon = self._create_icon()

        # 启动轮询线程
        self._poll_thread = threading.Thread(
            target=self._poll_desktop_changes,
            daemon=True,
            name="VDesk-Poll"
        )
        self._poll_thread.start()

        logger.info("VDesk Manager 已启动，托盘图标就绪")
        self._icon.run()

    def run_detached(self):
        """非阻塞方式启动（用于集成到其他应用）"""
        self._running = True
        self._icon = self._create_icon()

        self._poll_thread = threading.Thread(
            target=self._poll_desktop_changes,
            daemon=True,
            name="VDesk-Poll"
        )
        self._poll_thread.start()

        self._icon.run_detached()

    def stop(self):
        """停止托盘应用"""
        self._running = False
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        if self._icon:
            self._icon.stop()
        logger.info("VDesk Manager 已停止")
