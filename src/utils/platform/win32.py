# std
from typing import Callable, Any
import threading
import queue
import warnings
from inspect import cleandoc
from pathlib import Path
import struct
import re
from dataclasses import dataclass

# TK/CTk
import customtkinter as ctk

# win32
import ctypes
from ctypes import wintypes
import win32con, win32gui, win32api, win32event, winerror, win32clipboard


def file_to_clipboard(file_path: Path) -> None:
    """
    file_path の指すファイルをクリップボードに乗せて、
    エクスプローラー上でペースト可能な状態にする。

    Args:
        file_path (Path): クリップボードに乗せたいファイルのパス

    Raises:
        FileNotFoundError: file_path が存在しない場合
    """
    # ファイルの存在をチェック
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))

    # データを組み立てる
    # NOTE
    #   DROPFILES ヘッダ (sizeof=20, wide char)
    #   パス列 (UTF-16LE, ダブル終端)
    dropfiles = struct.pack("IiiII", 20, 0, 0, 0, 1)
    files = (str(file_path) + "\0\0").encode("utf-16le")
    data = dropfiles + files

    # クリップボードを開いて CF_HDROP をセット
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
    finally:
        win32clipboard.CloseClipboard()


class GlobalHotkey:
    """
    グローバルホットキーをトリガーにハンドラーを呼び出すクラス。
    """

    type Handler = Callable[[], None]

    # 定数
    MOD = win32con.MOD_CONTROL | win32con.MOD_ALT
    HOTKEY_ID = 1

    @dataclass
    class Entry:
        key_ch: str
        handler: "GlobalHotkey.Handler"

    def __init__(self, ctk_app: ctk.CTk):
        """
        コンストラクタ

        ctk_app:
            CTk アプリインスタンス。
            メッセージのポーリングに使われる。
        """
        # キー：ハンドラーマップ
        self._key_handler_map: dict[str, list[GlobalHotkey.Handler]] = dict()

        # グローバルホットキー押下イベント通知キュー
        # NOTE
        #   ctk の機能を win32 スレッドから呼び出すとクラッシュする（ctk はマルチスレッド非対応）
        #   そのため、このキューを介してメインスレッドへホットキー押下を通知する。
        ghk_event_queue = queue.SimpleQueue[str]()

        # win32 から呼び出されるプロシジャー
        def _window_procedure(hWnd, msg, wParam, lParam):
            if msg == win32con.WM_HOTKEY and wParam == GlobalHotkey.HOTKEY_ID:
                vk_code = (lParam >> 16) & 0xFFFF
                key_ch = chr(vk_code).upper()
                ghk_event_queue.put(key_ch)
                return 0
            else:
                return win32gui.DefWindowProc(hWnd, msg, wParam, lParam)

        # メッセージウィンドウを作成
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)  # type: ignore
        wc.lpszClassName = "AynimeIssenStyleHotKeyMessageOnlyWindow"  # type: ignore
        wc.lpfnWndProc = _window_procedure  # type: ignore
        class_atom = win32gui.RegisterClass(wc)
        self._msg_hwnd = win32gui.CreateWindowEx(
            0, class_atom, None, 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None  # type: ignore
        )

        # 保留メッセージのポンプ処理をデーモンスレッドで実行
        threading.Thread(target=win32gui.PumpWaitingMessages, daemon=True).start()

        # グローバルホットキーイベントポーリング関数
        def poll_ghk_event():
            while not ghk_event_queue.empty():
                key_ch = ghk_event_queue.get()
                handlers = self._key_handler_map.get(key_ch)
                if handlers is not None:  # NOTE 未登録キーは飛ばす
                    for handler in handlers:
                        try:
                            handler()
                        except Exception as e:
                            warn_text = f"""
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
            Ctrl + Atl + key_ch がホットキーとして登録される。

        handler:
            ホットキーで呼び出されるハンドラ
        """
        # 仮想キー番号を解決
        if len(key_ch) != 1:
            raise ValueError("key_ch must be a single character")
        else:
            vk_code = ord(key_ch.upper())

        # すでに登録されているキーならハンドラ追加だけ
        if key_ch in self._key_handler_map:
            self._key_handler_map[key_ch].append(handler)
            return

        # キー・ハンドラーマップに登録
        self._key_handler_map[key_ch] = [handler]

        # ホットキーを登録
        win32gui.RegisterHotKey(
            self._msg_hwnd,
            GlobalHotkey.HOTKEY_ID,
            GlobalHotkey.MOD,
            vk_code,
        )


class SystemWideMutex:
    """
    システムワイドのミューテックスを表すクラス
    """

    def __init__(self, name: str):
        """
        コンストラクタ

        Args:
            name (str): ミューテックス名
        """
        self._handle = win32event.CreateMutex(None, False, "Global\\" + name)  # type: ignore
        self._last_error = win32api.GetLastError()

    @property
    def already_exists(self) -> bool:
        """
        すでに同名のミューテックスが存在しているか調べる

        Returns:
            bool: すでに同名のミューテックスが存在しているなら True
        """
        return self._last_error == winerror.ERROR_ALREADY_EXISTS


def is_cloaked(hwnd: int) -> bool:
    """
    hwnd が指すウィンドウがクローク状態なら True を返す
    """
    DWMWA_CLOAKED = 14
    cloaked = wintypes.DWORD()
    res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
    )
    return res == 0 and cloaked.value != 0
