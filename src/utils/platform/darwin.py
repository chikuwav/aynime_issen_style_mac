"""
macOS 版の OS 依存機能。

`utils.platform.win32` と同じ名前・同じ意味の API を提供する。
"""

# std
from typing import Callable
from inspect import cleandoc
from pathlib import Path
import fcntl
import os
import queue
import subprocess
import warnings

# TK/CTk
import customtkinter as ctk

# macOS
from AppKit import NSPasteboard, NSURL
from quickmachotkey import quickHotKey, mask
from quickmachotkey import constants as qmhk_constants

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


def _resolve_virtual_key(key_ch: str) -> int:
    """
    文字から macOS の仮想キーコードを解決する。

    NOTE
        Windows 版は ord(key_ch.upper()) をそのまま仮想キーコードとして使えるが、
        macOS の仮想キーコードは ASCII と何の関係もない（kVK_ANSI_A = 0）。
        そのため変換表が要る。
    """
    virtual_key = getattr(qmhk_constants, f"kVK_ANSI_{key_ch}", None)
    if virtual_key is None:
        raise ValueError(f"Unsupported hotkey character ({key_ch})")
    return virtual_key


class GlobalHotkey:
    """
    グローバルホットキーをトリガーにハンドラーを呼び出すクラス。

    NOTE
        Carbon の RegisterEventHotKey を quickmachotkey 経由で使う。
        NSEvent のグローバルモニタと違って「入力監視」の許可が要らない。
    """

    type Handler = Callable[[], None]

    # 定数
    MOD = mask(qmhk_constants.controlKey, qmhk_constants.optionKey)

    def __init__(self, ctk_app: ctk.CTk):
        """
        コンストラクタ

        ctk_app:
            CTk アプリインスタンス。
            メッセージのポーリングに使われる。
        """
        # キー：ハンドラーマップ
        self._key_handler_map: dict[str, list["GlobalHotkey.Handler"]] = dict()

        # 登録済みホットキーの保持先
        # NOTE
        #   quickHotKey が返すオブジェクトを捨てると、
        #   ガベージコレクトされた時に登録が解除されうる。
        self._registered: dict[str, object] = dict()

        # グローバルホットキー押下イベント通知キュー
        # NOTE
        #   ctk の機能を Carbon のハンドラから呼び出すとクラッシュする（ctk はマルチスレッド非対応）
        #   そのため、このキューを介してメインスレッドへホットキー押下を通知する。
        self._ghk_event_queue = queue.SimpleQueue[str]()

        # グローバルホットキーイベントポーリング関数
        def poll_ghk_event():
            while not self._ghk_event_queue.empty():
                key_ch = self._ghk_event_queue.get()
                handlers = self._key_handler_map.get(key_ch)
                if handlers is not None:  # NOTE 未登録キーは飛ばす
                    for handler in handlers:
                        try:
                            handler()
                        except Exception as e:
                            warn_text = """
                            Unexpected exception raised in poll_ghk_event.
                            """
                            warnings.warn(cleandoc(warn_text))
            ctk_app.after(10, poll_ghk_event)

        # ポーリング処理をキック
        ctk_app.after(0, poll_ghk_event)

    def register(self, key_ch: str, handler: Handler) -> None:
        """
        ハンドラーを登録

        key_ch:
            Ctrl + Alt + key_ch がホットキーとして登録される。

        handler:
            ホットキーで呼び出されるハンドラ
        """
        # 仮想キー番号を解決
        if len(key_ch) != 1:
            raise ValueError("key_ch must be a single character")
        else:
            key_ch = key_ch.upper()
            virtual_key = _resolve_virtual_key(key_ch)

        # すでに登録されているキーならハンドラ追加だけ
        if key_ch in self._key_handler_map:
            self._key_handler_map[key_ch].append(handler)
            return

        # キー・ハンドラーマップに登録
        self._key_handler_map[key_ch] = [handler]

        # ホットキーを登録
        # NOTE
        #   Carbon のハンドラがどのスレッドで呼ばれるか保証がないので、
        #   ここではキューに積むだけにする。
        def on_hotkey() -> None:
            self._ghk_event_queue.put(key_ch)

        self._registered[key_ch] = quickHotKey(
            virtualKey=virtual_key, modifierMask=GlobalHotkey.MOD
        )(on_hotkey)


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


def open_directory(dir_path: Path) -> None:
    """
    dir_path の指すディレクトリを Finder で開く。

    Windows 版の os.startfile に相当する。

    NOTE
        まだ一度もキャプチャしていない場合はディレクトリが存在せず、
        open コマンドが失敗する。そのため、先に作る。

    Args:
        dir_path (Path): 開きたいディレクトリのパス
    """
    dir_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["open", str(dir_path)], check=True)
