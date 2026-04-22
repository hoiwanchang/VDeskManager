"""
VDesk Manager - Windows 虚拟桌面管理工具
通过系统托盘图标管理和切换虚拟桌面

功能：
  - 系统托盘图标实时显示当前桌面状态
  - 右键菜单快速切换桌面
  - 创建/删除/重命名虚拟桌面
  - 可自定义全局快捷键（默认 Ctrl+Alt+←/→ 切换，Ctrl+Alt+1-4 直达桌面）
  - 桌面变化自动刷新

使用：
  直接运行即可，托盘图标出现在任务栏右下角
  快捷键配置文件: ~/.vdesk-manager/hotkeys.json
"""

import sys
import os
import logging
import argparse

# 确保可以作为模块运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_logging(level: str = "INFO"):
    """配置日志"""
    log_dir = os.path.join(os.path.expanduser("~"), ".vdesk-manager", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "vdesk.log")

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ]
    )


def check_platform():
    """检查平台兼容性"""
    if sys.platform != "win32":
        print("错误: VDesk Manager 仅支持 Windows 10/11 平台")
        print("此工具依赖 Windows Virtual Desktop API")
        sys.exit(1)

    version = sys.getwindowsversion()
    if version.major < 10:
        print(f"错误: 不支持 Windows {version.major}.{version.minor}")
        print("需要 Windows 10 (1903+) 或 Windows 11")
        sys.exit(1)

    # Windows 10 1903 (build 18362) 引入虚拟桌面 API
    if version.build < 18362:
        print(f"警告: Windows Build {version.build} 可能不完全支持虚拟桌面 API")
        print("建议升级到 Windows 10 1903 或更高版本")


def check_dependencies():
    """检查依赖是否安装"""
    missing = []

    try:
        import pyvda
    except ImportError:
        missing.append("pyvda")

    try:
        import pystray
    except ImportError:
        missing.append("pystray")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    if missing:
        print("缺少依赖包，正在安装...")
        import subprocess
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + missing,
                creationflags=0x08000000 if sys.platform == "win32" else 0,
            )
            print("依赖安装完成！")
        except subprocess.CalledProcessError:
            print(f"自动安装失败，请手动执行: pip install {' '.join(missing)}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="VDesk Manager - Windows 虚拟桌面管理工具"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)"
    )
    parser.add_argument(
        "--poll-interval", type=float, default=0.8,
        help="桌面状态轮询间隔秒数 (默认: 0.8)"
    )
    parser.add_argument(
        "--no-hotkeys", action="store_true",
        help="禁用全局快捷键"
    )
    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger("vdesk")

    logger.info("=" * 50)
    logger.info("VDesk Manager 启动")
    logger.info("=" * 50)

    check_platform()
    check_dependencies()

    from src.tray_icon import TrayIconApp

    app = TrayIconApp(poll_interval=args.poll_interval)

    if not args.no_hotkeys:
        from src.hotkey_manager import HotkeyManager

        def on_hotkey_prev():
            app.manager.switch_by_offset(-1)
            app._schedule_refresh(delay=0.1)

        def on_hotkey_next():
            app.manager.switch_by_offset(1)
            app._schedule_refresh(delay=0.1)

        def on_hotkey_desktop(index: int):
            app.manager.switch_to(index)
            app._schedule_refresh(delay=0.1)

        hotkey_mgr = HotkeyManager(
            on_prev=on_hotkey_prev,
            on_next=on_hotkey_next,
            on_desktop=on_hotkey_desktop,
        )
        app.hotkey_manager = hotkey_mgr

        logger.info("正在启动快捷键管理器...")
        hotkey_mgr.start()

    try:
        logger.info("正在启动托盘图标...")
        app.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        app.stop()
    except Exception as e:
        logger.critical(f"运行时错误: {e}", exc_info=True)
        raise
    finally:
        logger.info("VDesk Manager 已退出")


if __name__ == "__main__":
    main()
