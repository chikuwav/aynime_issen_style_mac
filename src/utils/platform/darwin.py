"""
macOS 版の OS 依存機能。

`utils.platform.win32` と同じ名前・同じ意味の API を提供する。
"""

# std
from typing import Callable
from pathlib import Path
import fcntl
import os

# TK/CTk
import customtkinter as ctk

# macOS
from AppKit import NSPasteboard, NSURL

# utils
from utils.ais_logging import write_log


def file_to_clipboard(file_path: Path) -> None:
    """
    file_path の指すファイルをクリップボードに乗せて、
    Finder や Discord 上でペースト可能な状態にする。

    Windows 版の CF_HDROP に相当する。
    macOS ではファイル URL を一般ペーストボードに書けば同じ意味になる。

    Args:
        file_path (Path): クリップボードに乗せたいファイルのパス

    Raises:
        FileNotFoundError: file_path が存在しない場合
    """
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))

    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    url = NSURL.fileURLWithPath_(str(file_path))
    if not pasteboard.writeObjects_([url]):
        raise RuntimeError(f"Failed to put {file_path} on the pasteboard")


class GlobalHotkey:
    """
    グローバルホットキーをトリガーにハンドラーを呼び出すクラス。

    NOTE
        現時点では未実装のスタブ。
        登録は受け付けるが、キーを押しても何も起きない。
        Carbon の RegisterEventHotKey (quickmachotkey) で実装する予定。
    """

    type Handler = Callable[[], None]

    def __init__(self, ctk_app: ctk.CTk):
        """
        コンストラクタ

        ctk_app:
            CTk アプリインスタンス。
            将来、ホットキー押下をメインスレッドへ橋渡しするのに使う。
        """
        self._ctk_app = ctk_app
        self._key_handler_map: dict[str, list["GlobalHotkey.Handler"]] = dict()

    def register(self, key_ch: str, handler: Handler) -> None:
        """
        ハンドラーを登録

        key_ch:
            Ctrl + Alt + key_ch がホットキーとして登録される。

        handler:
            ホットキーで呼び出されるハンドラ
        """
        if len(key_ch) != 1:
            raise ValueError("key_ch must be a single character")
        self._key_handler_map.setdefault(key_ch.upper(), []).append(handler)
        write_log(
            "warning",
            f"Global hotkey Ctrl+Alt+{key_ch.upper()} is not implemented on macOS yet.",
        )


class SystemWideMutex:
    """
    システムワイドのミューテックスを表すクラス

    Windows 版の名前付きミューテックスに相当するものとして、
    ロックファイルへの排他ロックを使う。
    プロセスが死ねば OS がロックを外すので、後始末の考慮が要らない。
    """

    def __init__(self, name: str):
        """
        コンストラクタ

        Args:
            name (str): ミューテックス名
        """
        lock_dir = Path.home() / "Library" / "Application Support" / name
        lock_dir.mkdir(parents=True, exist_ok=True)
        self._lock_file_path = lock_dir / f"{name}.lock"
        self._already_exists = False
        try:
            self._fd = os.open(self._lock_file_path, os.O_RDWR | os.O_CREAT, 0o644)
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._already_exists = True

    @property
    def already_exists(self) -> bool:
        """
        すでに同名のミューテックスが存在しているか調べる

        Returns:
            bool: すでに同名のミューテックスが存在しているなら True
        """
        return self._already_exists
