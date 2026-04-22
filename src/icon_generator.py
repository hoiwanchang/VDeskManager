"""
图标生成模块
使用 Pillow 动态生成系统托盘图标
根据当前桌面编号实时更新图标显示
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os


# 颜色方案
COLORS = {
    "bg_active": (41, 128, 185),       # 活跃桌面 - 蓝色
    "bg_inactive": (52, 73, 94),       # 非活跃 - 深灰蓝
    "bg_dark": (30, 39, 46),           # 深色背景
    "text_primary": (255, 255, 255),   # 主文字白色
    "text_secondary": (189, 195, 199), # 次文字灰色
    "accent_green": (46, 204, 113),    # 绿色指示
    "accent_red": (231, 76, 60),       # 红色指示
    "border": (149, 165, 166),         # 边框
    "grid_line": (100, 120, 140),      # 网格线
}


def _get_font(size: int):
    """获取字体，优先使用系统字体"""
    font_paths = [
        "C:/Windows/Fonts/segoeui.ttf",       # Windows UI 字体
        "C:/Windows/Fonts/arial.ttf",          # Arial
        "C:/Windows/Fonts/msyh.ttc",           # 微软雅黑
        "C:/Windows/Fonts/calibri.ttf",        # Calibri
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_tray_icon(current: int, total: int) -> Image.Image:
    """
    生成系统托盘图标
    显示当前桌面编号和总桌面数的缩略视图

    :param current: 当前桌面编号 (从1开始)
    :param total: 桌面总数
    :return: PIL Image 对象 (64x64)
    """
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角背景
    draw_rounded_rect(draw, (2, 2, size - 3, size - 3), radius=12,
                      fill=COLORS["bg_dark"], outline=COLORS["border"], width=1)

    if total <= 4:
        _draw_grid_2x2(draw, current, total, size)
    elif total <= 9:
        _draw_grid_3x3(draw, current, total, size)
    else:
        _draw_number(draw, current, size)

    return img


def _draw_grid_2x2(draw: ImageDraw.Draw, current: int, total: int, size: int):
    """绘制 2x2 网格（最多4个桌面）"""
    padding = 10
    gap = 4
    cell_w = (size - 2 * padding - gap) // 2
    cell_h = (size - 2 * padding - gap) // 2

    for i in range(total):
        row, col = divmod(i, 2)
        x = padding + col * (cell_w + gap)
        y = padding + row * (cell_h + gap)
        is_current = (i + 1 == current)
        color = COLORS["bg_active"] if is_current else COLORS["bg_inactive"]

        draw_rounded_rect(draw, (x, y, x + cell_w, y + cell_h),
                          radius=4, fill=color)

        if is_current:
            # 添加小圆点指示器
            cx = x + cell_w // 2
            cy = y + cell_h // 2
            r = 4
            draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                         fill=COLORS["text_primary"])


def _draw_grid_3x3(draw: ImageDraw.Draw, current: int, total: int, size: int):
    """绘制 3x3 网格（最多9个桌面）"""
    padding = 8
    gap = 3
    cell_w = (size - 2 * padding - 2 * gap) // 3
    cell_h = (size - 2 * padding - 2 * gap) // 3

    for i in range(total):
        row, col = divmod(i, 3)
        x = padding + col * (cell_w + gap)
        y = padding + row * (cell_h + gap)
        is_current = (i + 1 == current)
        color = COLORS["bg_active"] if is_current else COLORS["bg_inactive"]

        draw_rounded_rect(draw, (x, y, x + cell_w, y + cell_h),
                          radius=3, fill=color)


def _draw_number(draw: ImageDraw.Draw, current: int, size: int):
    """超过9个桌面时，直接显示当前桌面编号"""
    font = _get_font(32)
    text = str(current)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2 - 2
    draw.text((x, y), text, fill=COLORS["text_primary"], font=font)


def generate_desktop_icon(index: int, total: int, is_current: bool = False) -> Image.Image:
    """为单个桌面生成小图标（用于菜单等）"""
    size = 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = COLORS["bg_active"] if is_current else COLORS["bg_inactive"]
    draw_rounded_rect(draw, (2, 2, size - 3, size - 3), radius=6, fill=color)

    font = _get_font(16)
    text = str(index)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2
    draw.text((x, y), text, fill=COLORS["text_primary"], font=font)

    return img


def draw_rounded_rect(draw: ImageDraw.Draw, bbox: tuple,
                      radius: int = 8,
                      fill: tuple = None,
                      outline: tuple = None,
                      width: int = 0):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = bbox
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)

    # 四个角的圆
    draw.ellipse((x1, y1, x1 + 2 * r, y1 + 2 * r), fill=fill, outline=outline, width=width)
    draw.ellipse((x2 - 2 * r, y1, x2, y1 + 2 * r), fill=fill, outline=outline, width=width)
    draw.ellipse((x1, y2 - 2 * r, x1 + 2 * r, y2), fill=fill, outline=outline, width=width)
    draw.ellipse((x2 - 2 * r, y2 - 2 * r, x2, y2), fill=fill, outline=outline, width=width)

    # 中间矩形
    draw.rectangle((x1 + r, y1, x2 - r, y2), fill=fill, outline=outline, width=width)
    draw.rectangle((x1, y1 + r, x2, y2 - r), fill=fill, outline=outline, width=width)

    # 如果有描边，用线段覆盖连接处避免重叠
    if outline and width > 0:
        draw.line([(x1 + r, y1), (x2 - r, y1)], fill=fill, width=width)
        draw.line([(x1 + r, y2), (x2 - r, y2)], fill=fill, width=width)
        draw.line([(x1, y1 + r), (x1, y2 - r)], fill=fill, width=width)
        draw.line([(x2, y1 + r), (x2, y2 - r)], fill=fill, width=width)


if __name__ == "__main__":
    # 测试图标生成
    for i in range(1, 5):
        icon = generate_tray_icon(current=i, total=4)
        icon.save(f"test_icon_{i}.png")
        print(f"生成图标: current={i}, total=4")
