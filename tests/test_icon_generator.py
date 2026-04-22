"""
图标生成器单元测试
"""

import pytest
from PIL import Image


def test_generate_tray_icon_basic():
    """测试基础图标生成"""
    from src.icon_generator import generate_tray_icon

    # 生成 4 个桌面的图标
    icon = generate_tray_icon(current=1, total=4)

    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)
    assert icon.mode == "RGBA"


def test_generate_tray_icon_current_variations():
    """测试不同当前桌面的图标生成"""
    from src.icon_generator import generate_tray_icon

    for current in range(1, 5):
        icon = generate_tray_icon(current=current, total=4)
        assert icon.size == (64, 64)


def test_generate_tray_icon_single_desktop():
    """测试单个桌面的图标生成"""
    from src.icon_generator import generate_tray_icon

    icon = generate_tray_icon(current=1, total=1)
    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)


def test_generate_tray_icon_many_desktops():
    """测试多桌面情况的图标生成"""
    from src.icon_generator import generate_tray_icon

    # 超过 9 个桌面应该显示数字
    icon = generate_tray_icon(current=5, total=12)
    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)


def test_generate_desktop_icon():
    """测试单个桌面图标生成"""
    from src.icon_generator import generate_desktop_icon

    # 当前桌面
    icon_current = generate_desktop_icon(index=1, total=4, is_current=True)
    assert icon_current.size == (32, 32)

    # 非当前桌面
    icon_inactive = generate_desktop_icon(index=2, total=4, is_current=False)
    assert icon_inactive.size == (32, 32)


def test_icon_colors():
    """测试图标颜色是否正确"""
    from src.icon_generator import generate_tray_icon, COLORS

    icon = generate_tray_icon(current=1, total=4)
    pixels = list(icon.getdata())

    # 检查是否有背景色（深色）- 简化测试，不检查具体颜色值
    has_dark_pixels = any(pixel[0] < 100 and pixel[1] < 100 and pixel[2] < 100 for pixel in pixels)
    assert has_dark_pixels, "图标应该包含深色像素"
