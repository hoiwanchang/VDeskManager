"""
快捷键管理模块
支持自定义快捷键切换虚拟桌面

核心修复：Windows RegisterHotKey 要求注册和消息循环在同一线程。
原实现在主线程注册但在子线程监听，导致 WM_HOTKEY 消息发到主线程队列
而子线程永远收不到。本模块在专用线程中完成注册 + 消息循环。

配置文件: ~/.vdesk-manager/hotkeys.json
"""

import ctypes
import json
import logging
import os
import threading
import time
from ctypes import wintypes
from typing import Callable

logger = logging.getLogger("vdesk")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ── Windows 常量 ──
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

MODIFIER_MAP = {
    'ctrl': MOD_CONTROL, 'control': MOD_CONTROL,
    'alt': MOD_ALT,
    'shift': MOD_SHIFT,
    'win': MOD_WIN, 'super': MOD_WIN, 'windows': MOD_WIN,
}

KEY_MAP = {
    # 方向键
    'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
    # 导航键
    'home': 0x24, 'end': 0x23, 'pageup': 0x21, 'pagedown': 0x22,
    'insert': 0x2D, 'delete': 0x2E,
    # 编辑键
    'backspace': 0x08, 'tab': 0x09,
    'enter': 0x0D, 'return': 0x0D,
    'escape': 0x1B, 'esc': 0x1B, 'space': 0x20,
    # 功能键
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
}

# 数字键 0-9
for _i in range(10):
    KEY_MAP[str(_i)] = 0x30 + _i

# 字母键 A-Z
for _c in 'abcdefghijklmnopqrstuvwxyz':
    KEY_MAP[_c] = ord(_c.upper())

# ── 配置 ──
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".vdesk-manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "hotkeys.json")

DEFAULT_CONFIG = {
    "hotkeys": {
        "prev": "Ctrl+Alt+Left",
        "next": "Ctrl+Alt+Right",
        "desktop_1": "Ctrl+Alt+1",
        "desktop_2": "Ctrl+Alt+2",
        "desktop_3": "Ctrl+Alt+3",
        "desktop_4": "Ctrl+Alt+4",
        "desktop_5": "",
        "desktop_6": "",
        "desktop_7": "",
        "desktop_8": "",
        "desktop_9": "",
    },
    "_说明": {
        "格式": "修饰键+键名，例如 Ctrl+Alt+Left",
        "修饰键": "Ctrl / Alt / Shift / Win（可任意组合，用+连接）",
        "按键名": "A-Z / 0-9 / F1-F12 / Left / Right / Up / Down / Space / Enter 等",
        "禁用": "将快捷键值留空字符串即可禁用",
        "desktop_N": "切换到第 N 个桌面（N = 1-9）",
        "prev_next": "切换到上一个 / 下一个桌面",
        "生效": "修改后右键托盘图标 → 快捷键 → 重新加载",
    }
}


def parse_hotkey(hotkey_str: str) -> tuple:
    """
    解析快捷键字符串为 (modifiers, vk_code)
    例如 "Ctrl+Alt+Left" → (MOD_CONTROL|MOD_ALT, VK_LEFT)
    空字符串返回 (0, None)
    """
    if not hotkey_str or not hotkey_str.strip():
        return 0, None

    parts = [p.strip().lower() for p in hotkey_str.split('+')]
    if not parts:
        return 0, None

    modifiers = 0
    vk = None

    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            # 修饰键
            mod = MODIFIER_MAP.get(part)
            if mod is None:
                logger.warning(f"未知修饰键: {part}")
                return 0, None
            modifiers |= mod
        else:
            # 按键
            vk = KEY_MAP.get(part)
            if vk is None:
                logger.warning(f"未知按键: {part}（可用: A-Z, 0-9, F1-F12, Left/Right/Up/Down, Space 等）")
                return 0, None

    return modifiers, vk


class HotkeyManager:
    """快捷键管理器 — 在专用线程中注册和监听全局快捷键"""

    def __init__(
        self,
        on_prev: Callable,
        on_next: Callable,
        on_desktop: Callable[[int], None],
        config_path: str = CONFIG_FILE,
    ):
        """
        :param on_prev: 切换到上一个桌面的回调
        :param on_next: 切换到下一个桌面的回调
        :param on_desktop: 切换到指定桌面的回调，参数为桌面序号(从1开始)
        :param config_path: 配置文件路径
        """
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_desktop = on_desktop
        self._config_path = config_path
        self._config: dict = {}

        self._thread: threading.Thread | None = None
        self._thread_id: int = 0
        self._ready_event = threading.Event()
        self._running = False

    # ── 配置管理 ──

    def load_config(self) -> dict:
        """加载配置文件，如不存在则创建默认配置"""
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)

        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._config = config
                logger.info(f"已加载快捷键配置: {self._config_path}")
                return config
            except Exception as e:
                logger.error(f"加载快捷键配置失败: {e}，使用默认配置")

        # 创建默认配置
        self._config = dict(DEFAULT_CONFIG)
        self._save_config()
        return self._config

    def _save_config(self):
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            logger.info(f"已保存快捷键配置: {self._config_path}")
        except Exception as e:
            logger.error(f"保存快捷键配置失败: {e}")

    def get_registered_summary(self) -> list[str]:
        """获取已注册快捷键的摘要列表"""
        hotkeys = self._config.get('hotkeys', {})
        lines = []
        for action, key in hotkeys.items():
            if not key:
                continue
            if action == 'prev':
                desc = '上一个桌面'
            elif action == 'next':
                desc = '下一个桌面'
            elif action.startswith('desktop_'):
                desc = f'桌面 {action.replace("desktop_", "")}'
            else:
                continue
            lines.append(f"{key} → {desc}")
        return lines

    # ── 生命周期 ──

    def start(self):
        """启动快捷键监听线程"""
        if self._running:
            return

        self.load_config()
        self._running = True
        self._ready_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="VDesk-Hotkey"
        )
        self._thread.start()

        # 等待线程就绪
        self._ready_event.wait(timeout=5)

    def stop(self):
        """停止快捷键监听"""
        if not self._running:
            return

        self._running = False

        # 向线程发送 WM_QUIT 以退出消息循环
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

        if self._thread:
            self._thread.join(timeout=3)

        logger.info("快捷键管理器已停止")

    def reload(self):
        """重新加载配置并重启快捷键"""
        logger.info("正在重新加载快捷键配置...")
        self.stop()
        time.sleep(0.2)
        self.start()
        summary = self.get_registered_summary()
        if summary:
            logger.info("快捷键已重新加载:\n  " + "\n  ".join(summary))

    def open_config_file(self):
        """用记事本打开配置文件"""
        import subprocess
        # 确保文件存在
        if not os.path.exists(self._config_path):
            self.load_config()

        subprocess.Popen(
            ['notepad.exe', self._config_path],
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        logger.info(f"已打开快捷键配置文件: {self._config_path}")

    # ── 线程主函数 ──

    def _run(self):
        """快捷键线程：注册所有快捷键并进入消息循环（必须与注册在同一线程）"""
        self._thread_id = kernel32.GetCurrentThreadId()
        self._ready_event.set()

        hotkeys = self._config.get('hotkeys', {})
        registrations: list[tuple[int, str]] = []  # [(hotkey_id, action_name)]
        hotkey_id = 1

        for action, hotkey_str in hotkeys.items():
            if not hotkey_str:
                continue

            modifiers, vk = parse_hotkey(hotkey_str)
            if vk is None:
                continue

            if user32.RegisterHotKey(None, hotkey_id, modifiers, vk):
                registrations.append((hotkey_id, action))
                desc = {
                    'prev': '上一个桌面',
                    'next': '下一个桌面',
                }.get(action, f'桌面 {action.replace("desktop_", "")}')
                logger.info(f"  已注册: {hotkey_str} → {desc}")
                hotkey_id += 1
            else:
                logger.warning(f"  注册失败: {hotkey_str} → {action}（可能已被其他程序占用）")

        if not registrations:
            logger.warning("没有成功注册任何快捷键")
            return

        logger.info(f"快捷键就绪 (共 {len(registrations)} 个)")

        # 消息循环 — WM_HOTKEY 会发送到此线程的队列
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                hid = msg.wParam
                for reg_id, action in registrations:
                    if reg_id == hid:
                        self._dispatch(action)
                        break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # 退出时注销所有快捷键
        for reg_id, _ in registrations:
            user32.UnregisterHotKey(None, reg_id)

        logger.debug("快捷键线程已退出")

    def _dispatch(self, action: str):
        """分发快捷键动作到回调"""
        try:
            if action == 'prev':
                self._on_prev()
            elif action == 'next':
                self._on_next()
            elif action.startswith('desktop_'):
                idx_str = action.replace('desktop_', '')
                try:
                    idx = int(idx_str)
                    self._on_desktop(idx)
                except ValueError:
                    logger.warning(f"无效的桌面序号: {idx_str}")
            else:
                logger.warning(f"未知快捷键动作: {action}")
        except Exception as e:
            logger.error(f"快捷键动作执行失败: {e}")
