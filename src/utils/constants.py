# std
from pathlib import Path
import sys


# アプリ名
APP_NAME_EN = "aynime_issen_style"
APP_NAME_JP = "えぃにめ一閃流奥義「一閃」"

# ウィジェットのパディングサイズ
WIDGET_PADDING = 6

# ウィジェットの最小サイズ
WIDGET_MIN_WIDTH = 60
WIDGET_MIN_HEIGHT = 32

# ウィンドウの最小サイズ
# NOTE
#   16:9 をスチルキャプチャしたときにちょうど良いサイズ。
WINDOW_MIN_WIDTH = 640
WINDOW_MIN_HEIGHT = 480

# ウィンドウの初期サイズ
# NOTE
#   16:9 をビデオキャプチャしたときにちょうど良いサイズ。
WINDOW_INIT_WIDTH = 640
WINDOW_INIT_HEIGHT = 960

# 共通して使用するフォント
# NOTE
#   Windows と macOS で同等の役割のフォントを割り当てている。
#   FAMILY は Tk 側、PATH は PIL 側で使う。
if sys.platform == "darwin":
    DEFAULT_FONT_FAMILY = "Hiragino Sans"
    DEFAULT_FONT_PATH = Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc")
    OVERLAY_FONT_FAMILY = "Hiragino Sans"
    OVERLAY_FONT_PATH = Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc")
    NUMERIC_FONT_FAMILY = "Menlo"
    NUMERIC_FONT_PATH = Path("/System/Library/Fonts/Menlo.ttc")
else:
    DEFAULT_FONT_FAMILY = "Yu Gothic UI"
    DEFAULT_FONT_PATH = Path("C:\\Windows\\Fonts\\YuGothM.ttc")
    OVERLAY_FONT_FAMILY = "Meiryo UI Bold"
    OVERLAY_FONT_PATH = Path("C:\\Windows\\Fonts\\Meiryob.ttc")
    NUMERIC_FONT_FAMILY = "Consolas"
    NUMERIC_FONT_PATH = Path("C:\\Windows\\Fonts\\Consolas.ttc")

# バージョン情報ファイルのパス
VERSION_FILE_PATH = Path("src") / "utils" / "version_constants.py"

# 各種データの保存先
# NOTE
#   Windows 版は「実行ファイルと同じ階層」に全部を置く。
#   macOS では .app の中に書き込めないうえ、
#   .app から起動するとカレントディレクトリが / になるため、
#   OS の作法どおりホーム以下の定位置に置く。
if sys.platform == "darwin":
    _PICTURES_DIR_PATH = Path.home() / "Pictures" / APP_NAME_EN
    _SUPPORT_DIR_PATH = Path.home() / "Library" / "Application Support" / APP_NAME_EN
    _LOG_DIR_PATH = Path.home() / "Library" / "Logs" / APP_NAME_EN
else:
    _PICTURES_DIR_PATH = Path.cwd()
    _SUPPORT_DIR_PATH = Path.cwd()
    _LOG_DIR_PATH = Path.cwd() / "log"

# ユーザープロパティファイルのパス
USER_PROPERTIES_FILE_PATH = _SUPPORT_DIR_PATH / "user_properties.json"

# ライセンス関係のパス
AIS_LICENSE_FILE_PATH = Path.cwd() / "LICENSE"
LICENSES_DIR_PATH = Path.cwd() / "licenses"

# キャプチャ保存先
# NOTE
#   nime はリサイズなどの処理適用済みの最終結果画像の保存先
#   raw は処理適用前のオリジナルのキャプチャ画像の保存先
NIME_DIR_PATH = _PICTURES_DIR_PATH / "nime"
TENSEI_DIR_PATH = _PICTURES_DIR_PATH / "tensei"
RAW_DIR_PATH = _PICTURES_DIR_PATH / "raw"
LOG_DIR_PATH = _LOG_DIR_PATH
TOOL_DIR_PATH = _SUPPORT_DIR_PATH / "tools"

# サムネイルの高さ方向のサイズ
THUMBNAIL_HEIGHT = 120

# キャプチャフレームバッファの保持秒数
CAPTURE_FRAME_BUFFER_DURATION_IN_SEC = 5

# 拡張子(NIME)
# NOTE
#   OUT:
#       現行バージョンの一閃流が出力する形式
#   INOUT:
#       NIME フォルダ上に存在して良い拡張子
#       歴史的経緯でいろいろな拡張子があり得る
NIME_STILL_OUT_SUFFIX = ".webp"
NIME_VIDEO_OUT_SUFFIX = ".avif"
# NIME_VIDEO_OUT_PIL_FORMAT = ...
NIME_STILL_INOUT_SUFFIXES = {NIME_STILL_OUT_SUFFIX, ".jpg", ".jpeg"}
NIME_VIDEO_INOUT_SUFFIXES = {NIME_VIDEO_OUT_SUFFIX, ".gif"}
NIME_CONTENT_INOUT_SUFFIXES = NIME_STILL_INOUT_SUFFIXES | NIME_VIDEO_INOUT_SUFFIXES

# 拡張子(RAW)
RAW_STILL_OUT_SUFFIX = ".png"
RAW_VIDEO_OUT_SUFFIX = ".webp"
# RAW_VIDEO_OUT_PIL_FORMAT = ...
RAW_STILL_INOUT_SUFFIXES = {RAW_STILL_OUT_SUFFIX}
RAW_VIDEO_INOUT_SUFFIXES = {RAW_VIDEO_OUT_SUFFIX, ".zip"}
RAW_CONTENT_INOUT_SUFFIXES = RAW_STILL_INOUT_SUFFIXES | RAW_VIDEO_INOUT_SUFFIXES

# 拡張子(NIME/RAW)
ALL_STILL_INOUT_SUFFIXES = NIME_STILL_INOUT_SUFFIXES | RAW_STILL_INOUT_SUFFIXES
ALL_VIDEO_INOUT_SUFFIXES = NIME_VIDEO_INOUT_SUFFIXES | RAW_VIDEO_INOUT_SUFFIXES
ALL_CONTENT_INOUT_SUFFIXES = ALL_STILL_INOUT_SUFFIXES | ALL_VIDEO_INOUT_SUFFIXES

# メディアファイルに持たせるメタデータのキー
# NOTE
#   ファイルへのメタデータの読み書きに使用するので、キーの変更＝破壊的変更。
#   基本的には変更不可能。
METADATA_KEY = "aynime_issen_style"
