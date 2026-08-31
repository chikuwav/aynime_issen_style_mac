"""
macOS 版のキャプチャ対象ウィンドウの列挙・識別。

`utils.capture.target_win32` と同じ名前・同じ意味の API を提供する。
ウィンドウの識別子は CGWindowID で、Windows 版の HWND と同じく整数。
"""

# std
from typing import Any, Generator
import threading

# macOS
import ScreenCaptureKit as SCK

# utils
from utils.std import sanitize_text
from utils.capture.target import WindowHandle

# ブラウザとみなすアプリの bundle identifier
# NOTE
#   Windows 版はウィンドウ名の末尾（" - Google Chrome" など）でアプリを判別している。
#   macOS のブラウザはウィンドウ名にアプリ名を付けないので、その手が使えない。
#   代わりに bundle identifier で判別する。こちらのほうが確実でもある。
BROWSER_BUNDLE_IDS = {
    "com.google.Chrome",
    "org.mozilla.firefox",
}

# ウィンドウ名の末尾に付くタブ音声インジケータ
# NOTE
#   macOS の Chrome は、音を鳴らしているタブのウィンドウ名の末尾に
#   スピーカーの絵文字を付ける（例: "<ページ名> 🔊"）。
#   アニメ再生中は必ず付くので、これを消さないと配信サービスの判定が全部外れる。
TAB_AUDIO_MARKS = "\U0001F507\U0001F508\U0001F509\U0001F50A"


def _strip_tab_audio_mark(text: str) -> str:
    """
    ウィンドウ名末尾のタブ音声インジケータを取り除く。
    """
    return text.rstrip(TAB_AUDIO_MARKS + " ").rstrip()


# 非同期呼び出しの待ち時間
CALLBACK_TIMEOUT_IN_SEC = 8.0

# 直近の列挙結果。CGWindowID から SCWindow を引くために保持する。
_WINDOW_CACHE: dict[int, Any] = dict()


def _wait_async(start, timeout: float = CALLBACK_TIMEOUT_IN_SEC):
    """
    非同期な ScreenCaptureKit の呼び出しを同期的に扱う。

    NOTE
        ハンドラは dispatch queue 上で呼ばれるので、
        メインのランループを回す必要がない。
        Tk が mainloop を握っていても、この待ち方なら干渉しない。
    """
    done = threading.Event()
    box = []

    def handler(*args):
        box.append(args)
        done.set()

    start(handler)
    if not done.wait(timeout):
        return None
    return box[0] if box else None


def _fetch_shareable_content():
    """
    キャプチャ可能なウィンドウ・ディスプレイの一覧を取得する。

    NOTE
        onScreenWindowsOnly を False にしている。
        「オンスクリーン」はアクティブな Space 上を意味するので、
        True にするとフルスクリーン表示中のブラウザが一覧から消える。
        一閃流が狙うのはまさにそのウィンドウなので、False でなければならない。
    """
    result = _wait_async(
        lambda handler: SCK.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(
            True, False, handler
        )
    )
    if result is None:
        return None
    content, error = result
    if error is not None:
        return None
    return content


def get_sc_window(window_handle: WindowHandle):
    """
    CGWindowID に対応する SCWindow を取得する。

    見つからない場合は一覧を取り直してから、もう一度だけ探す。
    """
    sc_window = _WINDOW_CACHE.get(window_handle.value)
    if sc_window is not None:
        return sc_window
    content = _fetch_shareable_content()
    if content is None:
        return None
    _refresh_cache(content)
    return _WINDOW_CACHE.get(window_handle.value)


def _refresh_cache(content) -> None:
    _WINDOW_CACHE.clear()
    for sc_window in content.windows():
        _WINDOW_CACHE[int(sc_window.windowID())] = sc_window


def enumerate_windows() -> Generator[WindowHandle, None, None]:
    """
    キャプチャ対象になりうるウィンドウを列挙する。
    """
    content = _fetch_shareable_content()
    if content is None:
        return
    _refresh_cache(content)

    for sc_window in content.windows():
        # 通常のウィンドウ層にないものはスキップ
        # NOTE
        #   Dock、メニューバー、通知センター、Spotlight などは
        #   0 以外のウィンドウ層に置かれる。
        #   Windows 版が GW_OWNER 持ちのウィンドウを除外しているのと同じ意図。
        if sc_window.windowLayer() != 0:
            continue

        # オーナーアプリを持たないものはスキップ
        # NOTE
        #   実測で 641 件中の大半が window server の内部ウィンドウ
        #   （"Packages Display 4 Shield" など）だった。
        #   これらは bundle identifier を持たないので、それで弾ける。
        application = sc_window.owningApplication()
        if application is None or not application.bundleIdentifier():
            continue

        # サイズを持たないウィンドウはスキップ
        frame = sc_window.frame()
        if frame.size.width <= 0 or frame.size.height <= 0:
            continue

        # タイトルでフィルタ
        # NOTE
        #   空タイトルはダメ、という Windows 版と同じ判定。
        #   循環 import を避けるためにここで import する。
        from utils.capture.target import get_nime_window_text

        title, _ = get_nime_window_text(WindowHandle(int(sc_window.windowID())))
        if not title:
            continue

        yield WindowHandle(int(sc_window.windowID()))


def get_browser_page_title(window_handle: WindowHandle) -> tuple[str, bool]:
    """
    ウィンドウ名を取得し、それがブラウザのページタイトルかどうかを返す。

    (ウィンドウ名, ブラウザのページタイトルか？) を返す。
    """
    sc_window = get_sc_window(window_handle)
    if sc_window is None:
        return "", False

    text = _strip_tab_audio_mark(sanitize_text(sc_window.title() or ""))
    if not text:
        return "", False

    application = sc_window.owningApplication()
    bundle_id = application.bundleIdentifier() if application else ""
    return text, bundle_id in BROWSER_BUNDLE_IDS
