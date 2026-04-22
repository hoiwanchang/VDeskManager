# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-04-22

### Added
- 窗口移动到指定桌面功能（托盘菜单 ⇄ 移动当前窗口到）
- 桌面名称持久化映射（`~/.vdesk-manager/desktop_names.json`），桌面 ID 变化后名称不丢失
- 日志轮转（`RotatingFileHandler`，5MB 上限，保留 5 份）
- 快捷键配置文件自动检测变化，自动重载
- 桌面预设/桌面组功能（`src/desktop_sets.py`）
- 窗口自动归类（`src/win_autoroute.py`），新窗口打开时自动移动到指定桌面
- 配置备份与恢复（`src/config_export.py`），托盘菜单导出/导入所有配置
- 多显示器独立/统一切换（`src/monitor_manager.py`）

### Fixed
- 修复重命名对话框 `_rename_dialog_active` 标志位泄露导致后续重命名失效
- 修复 PyInstaller 打包后自启动路径错误（使用 `sys.argv[0]` 并复制到 AppData）
- 修复启动时自动 pip install 过于激进导致失败的问题

## [1.0.3] - 2026-04-21

### Fixed
- 修复 PyInstaller 打包后 `Compress-Archive` 路径错误（single-file exe）
- CI/CD workflow 正确检测并压缩 `.exe` 文件

## [1.0.2] - 2026-04-21

### Fixed
- 调试修复（未发布 release）

## [1.0.1] - 2026-04-21

### Fixed
- 修复 CI/CD 认证问题（SSH key 配置）

## [1.0.0] - 2026-04-20

### Added
- 初始版本
- 托盘图标（动态网格图标，实时显示当前桌面序号）
- 桌面切换（左右偏移切换 / 序号直达 / 菜单点击）
- 创建/删除/重命名桌面
- 全局快捷键（可配置 JSON）
- 开机自启（任务计划程序）
- 自动轮询刷新 UI
- 任务视图唤起
