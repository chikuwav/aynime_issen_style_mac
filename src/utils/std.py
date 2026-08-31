# std
import re
from typing import Any, Iterable
import copy


def flatten(source: Any) -> Any:
    """
    入れ子になったリストをフラット化する

    Args:
        source (List[Any]): フラット化したいリスト

    Returns:
        List[Any]: フラット化されたリスト
    """
    if isinstance(source, list):
        for item in source:
            yield from flatten(item)
    elif isinstance(source, tuple):
        for item in source:
            yield from flatten(item)
    else:
        yield source


def replace_multi(
    text: str,
    repl_sources: Iterable[str],
    repl_target: str,
) -> str:
    """
    text 中に登場する repl_source を repl_target で置き換える。
    標準の replace の複数指定可能バージョン
    """
    for repl_source in repl_sources:
        text = text.replace(repl_source, repl_target)
    return text


class MultiscaleSequence:
    """
    マルチスケール数列クラス。
    0 ~ 10 ** num_zero までの整数列を表す。
    1000, 999, 998, ..., 991, 990, 980, ..., 910, 900, 800, ..., 200, 100, 0
    みたいな感じでステップ幅が桁に合わせて変動する。
    スライダーウィジェットと組み合わせた時に人間にとってわかりやすい挙動をするのが利点。
    """

    def __init__(self, num_zero: int):
        """
        コンストラクタ
        """
        # パラメータ保存
        self._num_zero = num_zero

        # 数列を生成
        self._values: list[int] = []
        current: int = 10**num_zero
        self._values.append(current)
        current -= 1
        self._values.append(current)
        for e in range(num_zero):
            variance: int = 10**e
            for _ in range(1, 10):
                current -= variance
                self._values.append(current)

        # 数列をソート
        self._values.sort()

    @property
    def num_values(self) -> int:
        """
        数列の長さを取得
        """
        return len(self._values)

    @property
    def values(self) -> list[int]:
        """
        数列のコピーを取得
        """
        return copy.deepcopy(self._values)

    def __getitem__(self, index: int) -> int:
        """
        添字アクセス
        """
        return self._values[index]

    def to_uniform_float(self, value: int) -> float:
        """
        value が数列上の値だと仮定して [0.0, 1.0] にスケーリングする。
        """
        scalar: float = 10**-self._num_zero
        return value * scalar

    def to_pct_str(self, value: int) -> str:
        """
        value が数列上の値だと仮定して [0, 100] にスケーリングする。
        """
        # 小数点以下・以上に分割
        div_point: int = 10 ** (self._num_zero - 2)
        upper = value // div_point
        lower = value % div_point

        # 小数点以上を文字列化
        # NOTE
        #   最大値 100 なので桁数は 3 で決め打ちでいい
        upper_num_digits = 3
        upper_str = str(upper)
        while len(upper_str) < upper_num_digits:
            upper_str = " " + upper_str

        # 小数点以下を文字列化
        lower_num_digits = self._num_zero - 2
        lower_str = str(lower)
        while len(lower_str) < lower_num_digits:
            lower_str = lower_str + "0"

        return f"{upper_str}.{lower_str}"


def sanitize_text(text: str) -> str:
    """
    text を「無毒化」する
    無毒化されたテキストは、ファイル名に含めることができる。
    """
    # Windows パス的な禁止文字を削除
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "　", text)

    # 見た目空白な文字を ASCII 半角スペースに統一
    # NOTE
    #   NBSP, 全角, 2000-系, 202F, 205F, 1680
    text = re.sub(r"[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]", " ", text)

    # ゼロ幅系を削除
    # NOTE
    #   ZWSP/ZWNJ/ZWJ/WORD JOINER/BOM
    #   歴史的に空白扱いの MVS
    text = re.sub(r"[\u200B-\u200D\u2060\uFEFF\u180E]", "", text)

    # ソフトハイフンを削除
    # NOTE
    #   通常は印字されず「改行位置の候補」だけを意味する。
    #   可視の意図はないので 削除。
    text = re.sub(r"\u00AD", "", text)

    # 区切り文字を ASCII のハイフンで統一
    # NOTE
    #   \u2013 = en dash
    #   \u2014 = em dash
    #   \u2015 = horizontal bar
    #   \u007C = vertical bar (ASCII |)
    #   \uFF5C = fullwidth vertical bar
    #   \u2011 = non-breaking hyphen
    text = re.sub(r"[\u2013\u2014\u2015\u007C\uFF5C\u2011]", "-", text)

    # アンダースコア --> 半角空白
    text = text.replace("_", " ")

    # ２つ以上連続する空白を 1 文字に短縮
    text = re.sub(r" {2,}", " ", text)

    # 前後の空白系文字を削除
    text = text.strip().rstrip()

    # 正常終了
    return text
