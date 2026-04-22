"""
窗口自动归类模块
注册窗口事件，当新窗口打开时自动将其移动到指定桌面。

类似 Windows 11 的原生"自动窗口摆放"功能，但通过 pyvda 实现。
"""

import ctypes
import json
import logging
import os
import threading
import time
from typing import Callable, Optional

user32 = ctypes.windll.user32

logger = logging.getLogger("vdesk")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".vdesk-manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "win_autoroute.json")

DEFAULT_CONFIG = {
    "_version": 1,
    "enabled": False,
    "rules": {},
}


class WindowAutoRouter:
    """窗口自动归类管理器"""

    def __init__(
        self,
        on_window_moved: Optional[Callable] = None,
        config_path: str = CONFIG_FILE,
    ):
        self._on_window_moved = on_window_moved
        self._config_path = config_path
        self._config: dict = dict(DEFAULT_CONFIG)
        self._known_hwnds: set = set()
        self._running = False
        self._thread: threading.Thread | None = None
        self._monitor_thread: threading.Thread | None = None
        self._monitor_running = False

    # ── 配置管理 ──

    def load_config(self) -> dict:
        """加载配置"""
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info("已加载窗口自动归类配置")
            except Exception as e:
                logger.error(f"加载窗口自动归类配置失败: {e}")
        return self._config

    def save_config(self):
        """保存配置"""
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存窗口自动归类配置失败: {e}")

    def add_rule(self, window_class: str, desktop_index: int):
        """添加窗口归类规则"""
        self.load_config()
        self._config["rules"][window_class] = desktop_index
        self.save_config()
        logger.info(f"已添加归类规则: {window_class} → 桌面 {desktop_index}")

    def remove_rule(self, window_class: str):
        """移除窗口归类规则"""
        self.load_config()
        self._config["rules"].pop(window_class, None)
        self.save_config()
        logger.info(f"已移除归类规则: {window_class}")

    def toggle_enabled(self) -> bool:
        """切换启用/禁用状态"""
        self.load_config()
        self._config["enabled"] = not self._config.get("enabled", False)
        self.save_config()
        return self._config["enabled"]

    # ── 生命周期 ──

    def start(self):
        """启动自动归类监控"""
        if self._running:
            return
        self.load_config()
        self._running = True
        self._monitor_running = True

        # 获取现有窗口列表
        self._collect_existing_windows()

        self._thread = threading.Thread(
            target=self._monitor_windows,
            daemon=True,
            name="VDesk-WinAutoRoute",
        )
        self._thread.start()
        logger.info("窗口自动归类已启动")

    def stop(self):
        """停止自动归类监控"""
        self._running = False
        self._monitor_running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        logger.info("窗口自动归类已停止")

    # ── 窗口监控 ──

    def _collect_existing_windows(self):
        """收集当前所有可见窗口"""
        def enum_callback(hwnd, extra):
            try:
                if user32.IsWindowVisible(hwnd):
                    self._known_hwnds.add(hwnd)
            except Exception:
                pass
            return True
        try:
            user32.EnumWindows(ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.c_uint64, ctypes.c_int
            )(enum_callback), 0)
        except Exception as e:
            logger.debug(f"收集窗口失败: {e}")

    def _monitor_windows(self):
        """监控新窗口打开"""
        last_count = len(self._known_hwnds)
        while self._monitor_running and self._running:
            current_hwnds = self._get_all_windows()
            new_hwnds = current_hwnds - self._known_hwnds

            for hwnd in new_hwnds:
                self._process_new_window(hwnd)

            self._known_hwnds = current_hwnds
            time.sleep(0.5)

    def _get_all_windows(self) -> set:
        """获取所有可见窗口句柄"""
        hwnds = set()
        def enum_callback(hwnd, extra):
            try:
                if user32.IsWindowVisible(hwnd):
                    hwnds.add(hwnd)
            except Exception:
                pass
            return True
        try:
            user32.EnumWindows(ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.c_uint64, ctypes.c_int
            )(enum_callback), 0)
        except Exception as e:
            logger.debug(f"枚举窗口失败: {e}")
        return hwnds

    def _process_new_window(self, hwnd: int):
        """处理新窗口，根据规则归类"""
        try:
            class_name_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name_buf, 256)
            class_name = class_name_buf.value

            # 跳过某些不需要归类的窗口
            if not class_name or class_name in ("Windows.UI.Core.CoreWindow",):
                return

            self.load_config()
            if not self._config.get("enabled", False):
                return

            rules = self._config.get("rules", {})
            if class_name in rules:
                desktop_index = rules[class_name]
                try:
                    from .desktop_manager import _pyvda
                    if _pyvda:
                        desktops = _pyvda.get_virtual_desktops()
                        if 1 <= desktop_index <= len(desktops):
                            _pyvda.ViewVirtualDesktop(hwnd, desktops[desktop_index - 1])
                            logger.info(f"窗口 {class_name} (0x{hwnd:x}) 已移动到桌面 {desktop_index}")
                            if self._on_window_moved:
                                self._on_window_moved(hwnd, class_name, desktop_index)
                except Exception as e:
                    logger.debug(f"移动窗口失败: {e}")
        except Exception as e:
            logger.debug(f"处理窗口失败: {e}")
