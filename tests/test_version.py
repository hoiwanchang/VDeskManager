"""
版本信息单元测试
"""

import pytest


def test_version_constants():
    """测试版本常量是否正确定义"""
    from src.version import (
        __version__,
        __app_name__,
        __author__,
        __description__,
        __repo__,
    )

    assert __version__ == "1.2.0"
    assert __app_name__ == "VDesk Manager"
    assert __author__ == "Kane Chang"
    assert __description__ == "Virtual Desktop Manager - Windows 虚拟桌面管理工具"
    assert __repo__ == "https://github.com/hoiwanchang/VDeskManager"


def test_version_format():
    """测试版本号格式"""
    from src.version import __version__

    # 版本号应该符合语义化版本格式
    parts = __version__.split(".")
    assert len(parts) == 3
    assert parts[0].isdigit()  # 主版本号
    assert parts[1].isdigit()  # 次版本号
    assert parts[2].isdigit()  # 修订号


def test_version_import():
    """测试版本号可以正常导入"""
    try:
        from src.version import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0
    except ImportError:
        pytest.fail("无法导入 src.version")
