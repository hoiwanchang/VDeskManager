"""
桌面切换动画控制单元测试
"""

import pytest
import sys
from unittest.mock import patch, MagicMock


# 只在 Windows 环境下测试需要 winreg 的模块
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_get_switch_animation_enabled_default():
    """测试默认动画设置读取"""
    from src.switch_animation import get_switch_animation_enabled

    with patch("src.switch_animation.reg.OpenKey") as mock_open_key:
        mock_key = MagicMock()
        mock_open_key.return_value = mock_key
        mock_key.QueryValueEx.return_value = (1, None)

        result = get_switch_animation_enabled()
        assert result is True


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_get_switch_animation_enabled_disabled():
    """测试动画禁用状态读取"""
    from src.switch_animation import get_switch_animation_enabled

    with patch("src.switch_animation.reg.OpenKey") as mock_open_key:
        mock_key = MagicMock()
        mock_open_key.return_value = mock_key
        mock_key.QueryValueEx.return_value = (0, None)

        result = get_switch_animation_enabled()
        assert result is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_toggle_switch_animation():
    """测试动画切换功能"""
    from src.switch_animation import toggle_switch_animation

    with patch("src.switch_animation.get_switch_animation_enabled") as mock_get, \
         patch("src.switch_animation.set_switch_animation_enabled") as mock_set:
        mock_get.return_value = True
        result = toggle_switch_animation()

        assert result is False  # 从 True 切换到 False
        mock_set.assert_called_once_with(False)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only module")
def test_toggle_switch_animation_reverse():
    """测试动画切换反向"""
    from src.switch_animation import toggle_switch_animation

    with patch("src.switch_animation.get_switch_animation_enabled") as mock_get, \
         patch("src.switch_animation.set_switch_animation_enabled") as mock_set:
        mock_get.return_value = False
        result = toggle_switch_animation()

        assert result is True  # 从 False 切换到 True
        mock_set.assert_called_once_with(True)
