"""
pytest 配置和 fixtures
"""

import sys
import os
from pathlib import Path
import pytest

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def test_icon_dir(tmp_path):
    """创建临时图标目录"""
    icon_dir = tmp_path / "icons"
    icon_dir.mkdir()
    return icon_dir


@pytest.fixture
def mock_desktop_manager(mocker):
    """模拟 DesktopManager"""
    mock = mocker.MagicMock()
    mock.get_desktops.return_value = []
    return mock
