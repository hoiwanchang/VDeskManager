"""
开机自启动管理模块
通过 Windows 任务计划程序实现用户登录后自动启动

为什么用任务计划程序而不是注册表 Run 键：
  - 支持以最高权限运行
  - 支持延迟启动（避免与其他启动程序争抢资源）
  - 可以可靠地检测/删除已注册的任务
  - 不需要管理员权限即可操作当前用户的任务
"""

import ctypes
import logging
import os
import subprocess
import sys

logger = logging.getLogger("vdesk")

TASK_NAME = "VDeskManager_AutoStart"
TASK_XML_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>VDesk Manager - 虚拟桌面管理工具开机自启动</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT5S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <WorkingDirectory>{workdir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def get_exe_path() -> str:
    """获取当前可执行文件路径（打包 EXE 或 Python 脚本）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包的 EXE
        return sys.executable
    else:
        # 开发模式：用 pythonw 运行 main.py
        return sys.executable


def get_workdir() -> str:
    """获取工作目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(sys.argv[0]))


def is_auto_start_enabled() -> bool:
    """检查是否已注册开机自启动"""
    try:
        result = subprocess.run(
            ['schtasks', '/Query', '/TN', TASK_NAME, '/XML'],
            capture_output=True, text=True,
            creationflags=0x08000000,
            timeout=10,
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug(f"查询自启动任务失败: {e}")
        return False


def enable_auto_start() -> bool:
    """启用开机自启动"""
    try:
        exe_path = get_exe_path()
        workdir = get_workdir()

        # 生成 XML
        if getattr(sys, 'frozen', False):
            command = exe_path
        else:
            script = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "main.py")
            command = f'"{exe_path}" "{script}"'

        xml = TASK_XML_TEMPLATE.format(
            command=command,
            workdir=workdir,
        )

        # 写入临时 XML 文件
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.xml', encoding='utf-16',
            delete=False, prefix='vdesk_task_'
        ) as f:
            f.write(xml)
            xml_path = f.name

        try:
            # 使用 schtasks 注册任务
            # /F 强制覆盖已有任务
            result = subprocess.run(
                ['schtasks', '/Create', '/TN', TASK_NAME, '/XML', xml_path, '/F'],
                capture_output=True, text=True,
                creationflags=0x08000000,
                timeout=15,
            )

            if result.returncode == 0:
                logger.info("开机自启动已启用")
                return True
            else:
                logger.error(f"注册自启动任务失败: {result.stderr.strip()}")
                return False
        finally:
            os.unlink(xml_path)

    except Exception as e:
        logger.error(f"启用自启动失败: {e}")
        return False


def disable_auto_start() -> bool:
    """禁用开机自启动"""
    try:
        result = subprocess.run(
            ['schtasks', '/Delete', '/TN', TASK_NAME, '/F'],
            capture_output=True, text=True,
            creationflags=0x08000000,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info("开机自启动已禁用")
            return True
        else:
            logger.error(f"删除自启动任务失败: {result.stderr.strip()}")
            return False

    except Exception as e:
        logger.error(f"禁用自启动失败: {e}")
        return False


def toggle_auto_start() -> tuple[bool, bool]:
    """
    切换自启动状态
    返回: (操作是否成功, 当前是否启用)
    """
    if is_auto_start_enabled():
        success = disable_auto_start()
        return success, False
    else:
        success = enable_auto_start()
        return success, True
