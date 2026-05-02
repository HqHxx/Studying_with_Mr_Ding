"""统一路径解析模块 — 兼容开发环境与 PyInstaller 打包环境。"""

import sys
from pathlib import Path


def get_base_dir() -> Path:
    """返回项目根目录。

    - 开发时: 返回脚本所在目录
    - PyInstaller 打包后: 返回 EXE 所在目录
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，sys.executable 指向 EXE 自身
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_internal_dir() -> Path:
    """返回内部资源目录（只读资源，如字体、语料库）。

    - 开发时: 与 get_base_dir() 相同
    - PyInstaller --onedir 打包后: 与 get_base_dir() 相同
    - PyInstaller --onefile 打包后: 返回临时解压目录 sys._MEIPASS
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


# 预计算常用路径
BASE_DIR = get_base_dir()
INTERNAL_DIR = get_internal_dir()
