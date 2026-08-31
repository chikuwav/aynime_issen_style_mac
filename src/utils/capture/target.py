# std
from typing import Generator
from dataclasses import dataclass
import re
import sys

# utils
from utils.std import replace_multi


@dataclass
class MonitorIdentifier:
    """
    モニター識別子を保持するクラス
    """

    adapter_index: int  # グラボのインデックス
    output_index: int  # モニターのインデックス


@dataclass
class WindowHandle:
    """
    ウィンドウ識別子を保持するクラス

    NOTE
        Windows では HWND、macOS では CGWindowID を保持する。
        どちらも整数なので、この型はそのまま両対応できる。
    """

    value: int


def _parse_nime_title(text: str) -> tuple[str, bool]:
    """
    ブラウザのページタイトルからアニメ名を抽出する。

    配信サービスごとの命名規則を扱う。
    ここは OS に依存しないので、Windows / macOS で共有する。
    (加工された名前, えぃにめか？) を返す。
    """
    # 配信サービス別の処理
    # NOTE
    #   アニメタイトルと話数は区別せずに１つの「アニメ名」とみなす。
    #   最終的にそれを見た人間が認識できれば何でも良いので、一閃流として区別する必要がない。
    bc_pos = text.find("バンダイチャンネル")
    if text.endswith("dアニメストア"):
        if text.find("アニメ動画見放題") >= 0:
            # NOTE
            #   作品ページの場合「アニメ動画見放題」がついている
            #   作品ページはタイトルに話数情報が含まれないのでアニメ名抽出の対象としない
            return text, False
        else:
            # NOTE
            #   dアニメストアは「<アニメ名> - <話数> - <話タイトル>」形式。
            #   <話タイトル> は冗長なので除外する。
            #   区切り文字「 - 」は贅沢なので空白１文字に短縮。
            text = text.replace(" dアニメストア", "")
            text = " ".join(text.split(" - ")[:2])
    elif text.endswith("AnimeFesta"):
        # NOTE
        #   AnimeFesta はアニメ名しか出てこないので、特別にすることも無い
        text = text.replace("を見る AnimeFesta", "")
    elif bc_pos != -1:
        # NOTE
        #   バンダイチャンネルの場合、余計な文字がいっぱい付くので、それらをまとめてカット。
        #   また、微妙な区切り文字が残るのでそれもカット。
        text = text[:bc_pos]
        if text.endswith("- "):
            text = text[:-2]
    elif text.endswith("Prime Video"):
        # NOTE
        #   Amazon Prime Video の場合、前後に余計な文字が付くので、それらをカット。
        text = replace_multi(text, ["Amazon.co.jp ", "を観る Prime Video"], "")
    elif text.endswith("ABEMA"):
        # NOTE
        #   ABEMA の場合、シンプルにカットしていくだけで良い
        text = replace_multi(
            text, ["(アニメ)", "無料動画・見逃し配信を見るなら", "ABEMA"], ""
        )
    else:
        return text, False

    # 余計な空白を除去
    text = text.strip().rstrip()
    text = re.sub(r" {2,}", " ", text)

    # 正常終了
    return text, True


# OS 別実装のディスパッチ
if sys.platform == "win32":
    from utils.capture.target_win32 import (
        enumerate_windows,
        get_browser_page_title,
    )
elif sys.platform == "darwin":
    from utils.capture.target_darwin import (
        enumerate_windows,
        get_browser_page_title,
    )
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def get_nime_window_text(window_handle: WindowHandle) -> tuple[str, bool]:
    """
    一閃流的に都合の良いように加工されたウィンドウ名を取得する。
    平たく言えば、ウィンドウ名からアニメ名を抽出する。
    (加工された名前, えぃにめか？) を返す。
    """
    if window_handle is None:
        return "", False
    text, is_browser = get_browser_page_title(window_handle)
    if not text:
        return "", False
    if not is_browser:
        return text, False
    return _parse_nime_title(text)
