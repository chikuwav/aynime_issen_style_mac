"""
OS 依存の機能をプラットフォーム別実装に振り分ける。

呼び出し側は `from utils.platform import file_to_clipboard` のように書き、
どの OS で動いているかを意識しない。
"""

import sys

if sys.platform == "win32":
    from utils.platform.win32 import (
        file_to_clipboard,
        GlobalHotkey,
        SystemWideMutex,
    )
elif sys.platform == "darwin":
    from utils.platform.darwin import (
        file_to_clipboard,
        GlobalHotkey,
        SystemWideMutex,
    )
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")

__all__ = [
    "file_to_clipboard",
    "GlobalHotkey",
    "SystemWideMutex",
]
