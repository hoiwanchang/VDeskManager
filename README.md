# VDesk Manager - Windows 虚拟桌面管理工具

通过系统托盘图标快速管理和切换 Windows 虚拟桌面。

## 功能特性

- 🖥️ **系统托盘图标** — 实时显示当前桌面编号和桌面网格概览
- ⚡ **快速切换** — 右键菜单一键切换任意桌面
- ➕ **创建桌面** — 快速新建虚拟桌面
- ✕ **删除桌面** — 选择并移除指定桌面
- ✎ **重命名桌面** — 为桌面设置有意义的名称
- ⌨️ **全局热键** — `Ctrl+Alt+←/→` 左右切换桌面
- 🔄 **自动刷新** — 检测桌面变化实时更新图标和菜单

## 系统要求

- Windows 10 (1903+) 或 Windows 11
- Python 3.10+

## 快速开始

### 方式一：直接运行

```batch
:: 安装依赖
pip install -r requirements.txt

:: 启动
python main.py
```

或直接双击 `start.bat`

### 方式二：打包为 EXE

```batch
pip install pyinstaller
build.bat
```

打包后生成 `dist/VDeskManager.exe`，双击即可运行，无需 Python 环境。

## 命令行参数

```
python main.py [OPTIONS]

选项:
  --log-level {DEBUG,INFO,WARNING,ERROR}  日志级别 (默认: INFO)
  --poll-interval FLOAT                    轮询间隔秒数 (默认: 0.8)
  --no-hotkeys                             禁用全局热键
```

## 使用方法

1. 启动后，任务栏右下角出现托盘图标
2. 图标会显示当前桌面位置的网格缩略图
3. **左键单击** — 弹出桌面切换菜单
4. **右键单击** — 完整功能菜单（切换/创建/删除/重命名）

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Alt+←` | 切换到上一个桌面 |
| `Ctrl+Alt+→` | 切换到下一个桌面 |

### 图标说明

托盘图标会根据桌面数量自动切换显示模式：

- **1-4 个桌面** → 2×2 网格，当前桌面高亮
- **5-9 个桌面** → 3×3 网格，当前桌面高亮
- **10+ 个桌面** → 显示当前桌面编号

## 项目结构

```
vdesk-manager/
├── main.py               # 主入口
├── start.bat             # Windows 启动脚本
├── build.bat             # PyInstaller 打包脚本
├── requirements.txt      # Python 依赖
├── README.md             # 本文档
└── src/
    ├── __init__.py
    ├── desktop_manager.py  # 虚拟桌面核心管理
    ├── tray_icon.py        # 系统托盘指示器
    └── icon_generator.py   # 动态图标生成
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 虚拟桌面 API | [pyvda](https://github.com/mirober/pyvda) — Windows Virtual Desktop COM API 封装 |
| 系统托盘 | [pystray](https://github.com/moses-palmer/pystray) — 跨平台系统托盘库 |
| 图标生成 | [Pillow](https://python-pillow.org/) — 图像处理 |
| 打包 | PyInstaller — 单文件 EXE |

## 注意事项

- 虚拟桌面 API 依赖 Windows 未公开的 COM 接口，极少数 Windows 更新可能导致临时失效
- 日志文件位于 `~/.vdesk-manager/logs/vdesk.log`
- 如热键冲突，使用 `--no-hotkeys` 禁用

## License

MIT License
