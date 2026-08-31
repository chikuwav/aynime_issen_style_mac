# std
from typing import Generator

# win32
import win32gui, win32con

# utils
from utils.std import sanitize_text
from utils.platform.win32 import is_cloaked
from utils.capture.target import WindowHandle


def enumerate_windows() -> Generator[WindowHandle, None, None]:
    # 全てのウィンドウハンドルを列挙
    hwnds: list[int] = []

    def enum_handler(hwnd: int, _):
        hwnds.append(hwnd)

    win32gui.EnumWindows(enum_handler, None)

    # 合法なウィンドウを順番に返す
    for hwnd in hwnds:
        # 不可視ウィンドウはスキップ
        if not win32gui.IsWindowVisible(hwnd):
            continue

        # 最小化されているウィンドウはスキップ
        if win32gui.IsIconic(hwnd):
            continue

        # クローク状態のウィンドウはスキップ
        if is_cloaked(hwnd):
            continue

        # サイズを持たないウィンドウはスキップ
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        if right - left <= 0 or bottom - top <= 0:
            continue

        # オーナーが居るウィンドウはスキップ
        if win32gui.GetWindow(hwnd, win32con.GW_OWNER):
            continue

        # タイトルでフィルタ
        # NOTE
        #   空タイトルはダメ
        #   Program Manager は何故か残っちゃうので名指しで除外
        # NOTE
        #   循環 import を避けるためにここで import する。
        from utils.capture.target import get_nime_window_text

        title, _ = get_nime_window_text(WindowHandle(hwnd))
        if not title:
            continue
        elif title == "Program Manager":
            continue

        # ウィンドウ情報を生成して返す
        yield WindowHandle(hwnd)


def get_browser_page_title(window_handle: WindowHandle) -> tuple[str, bool]:
    """
    ウィンドウ名を取得し、それがブラウザのページタイトルかどうかを返す。

    (ウィンドウ名, ブラウザのページタイトルか？) を返す。
    Windows ではウィンドウ名の末尾にアプリ名が付くので、それで判別できる。
    """
    # None は空文字列化
    if window_handle is None:
        return "", False

    # ウィンドウ名を取得
    text = win32gui.GetWindowText(window_handle.value)
    text = sanitize_text(text)
    if len(text) == 0:
        return "", False

    # アプリの種類で分岐
    # NOTE
    #   ブラウザの場合はアニメ名が取れるので、末尾のアプリ名だけ取って続行。
    #   それ以外は断念
    if text.endswith("Mozilla Firefox"):
        text = text.replace(" - Mozilla Firefox", "")
    elif text.endswith("Google Chrome"):
        text = text.replace(" - Google Chrome", "")
    elif text.endswith(" - Discord"):
        # NOTE
        #   Discord の配信画面は、チャンネル名が返ってくる
        #   そこにえぃにめは無い
        text = text.replace(" - Discord", "")
        return text, False
    else:
        # それ以外の非対応アプリ
        return text, False

    # ここまで来たならブラウザのページタイトル
    return text, True
