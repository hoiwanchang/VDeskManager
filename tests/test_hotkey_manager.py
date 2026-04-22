"""
热键管理器单元测试
"""

import pytest
import sys


# 只在 Windows 环境下测试需要 ctypes.windll 的模块
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_parse_hotkey_basic():
    """测试基础热键解析"""
    from src.hotkey_manager import parse_hotkey

    # 测试 Ctrl+Alt+Left
    modifiers, vk = parse_hotkey("Ctrl+Alt+Left")
    assert modifiers == (0x11 | 0x08)  # Ctrl | Alt
    assert vk == 0xA7  # VK_LEFT


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_parse_hotkey_simple():
    """测试简单热键解析"""
    from src.hotkey_manager import parse_hotkey

    # 测试 Ctrl+A
    modifiers, vk = parse_hotkey("Ctrl+A")
    assert modifiers == 0x11  # Ctrl
    assert vk == 0x41  # 'A'


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_parse_hotkey_invalid():
    """测试无效热键"""
    from src.hotkey_manager import parse_hotkey

    # 测试无效热键
    modifiers, vk = parse_hotkey("InvalidKey")
    assert modifiers is None
    assert vk is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_parse_hotkey_with_shift():
    """测试带 Shift 的热键"""
    from src.hotkey_manager import parse_hotkey

    modifiers, vk = parse_hotkey("Shift+F1")
    assert modifiers == 0x04  # Shift
    assert vk == 0x70  # VK_F1


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_detect_conflicts():
    """测试冲突检测"""
    from src.hotkey_manager import HotkeyManager, KNOWN_CONFLICTS

    # 创建包含冲突热键的配置
    config_with_conflicts = {
        "hotkeys": {
            "prev": "Ctrl+Alt+Left",
            "next": "Ctrl+Alt+Right",
            "desktop_1": "Ctrl+Alt+1",
            "desktop_2": "Ctrl+Alt+2",
            "conflicting": "Ctrl+Shift+Esc",  # 与任务管理器冲突
        }
    }

    manager = HotkeyManager.__new__(HotkeyManager)
    manager._config = config_with_conflicts

    conflicts = manager.detect_conflicts()
    assert len(conflicts) > 0
    assert any("任务管理器" in c for c in conflicts)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_no_conflicts():
    """测试无冲突情况"""
    from src.hotkey_manager import HotkeyManager

    config_no_conflicts = {
        "hotkeys": {
            "prev": "Ctrl+Alt+Up",
            "next": "Ctrl+Alt+Down",
            "desktop_1": "Ctrl+Alt+1",
        }
    }

    manager = HotkeyManager.__new__(HotkeyManager)
    manager._config = config_no_conflicts

    conflicts = manager.detect_conflicts()
    assert len(conflicts) == 0


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_get_registered_summary():
    """测试获取注册摘要"""
    from src.hotkey_manager import HotkeyManager

    config = {
        "hotkeys": {
            "prev": "Ctrl+Alt+Left",
            "next": "Ctrl+Alt+Right",
            "desktop_1": "Ctrl+Alt+1",
        }
    }

    manager = HotkeyManager.__new__(HotkeyManager)
    manager._config = config

    summary = manager.get_registered_summary()
    assert len(summary) == 3
    assert any("上一个桌面" in s for s in summary)
    assert any("下一个桌面" in s for s in summary)
    assert any("桌面 1" in s for s in summary)
