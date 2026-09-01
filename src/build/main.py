import subprocess
import shutil
import sys
from datetime import datetime
from pathlib import Path
from inspect import cleandoc
from pathlib import Path
import plistlib
import shutil

from utils.constants import VERSION_FILE_PATH, APP_NAME_EN, LICENSES_DIR_PATH

# 設定
DIST_DIR_PATH = Path(f"dist")
DIST_APP_DIR_PATH = DIST_DIR_PATH / APP_NAME_EN
DIST_APP_LICENSE_DIR_PATH = DIST_APP_DIR_PATH / "licenses"
BUILD_DIR_PATH = Path("build")
WORK_DIR_PATH = BUILD_DIR_PATH / "temp"
SPEC_DIR_PATH = BUILD_DIR_PATH / "spec"
ZIP_OUTPUT_DIR = Path("release")
APP_ICO_FILE_ABS_PATH = Path("app.ico").resolve()
APP_ICNS_FILE_ABS_PATH = Path("app.icns").resolve()
LICENSE_FILE_ABS_PATH = Path("LICENSE").resolve()

# macOS の .app 関係
# NOTE
#   バンドル識別子は画面収録の許可（TCC）の紐づけ先になる。
#   変えると許可を与え直すことになるので、固定する。
BUNDLE_IDENTIFIER = "com.chikuwav.aynime-issen-style"
DIST_APP_BUNDLE_PATH = DIST_APP_DIR_PATH / f"{APP_NAME_EN}.app"
MINIMUM_SYSTEM_VERSION = "12.3"  # NOTE ScreenCaptureKit の要求

# 同梱物のライセンス表示をまとめたファイル
THIRD_PARTY_LICENSE_FILE_NAME = "THIRD-PARTY-LICENSES.txt"
THIRD_PARTY_LICENSE_FILE_PATH = WORK_DIR_PATH / THIRD_PARTY_LICENSE_FILE_NAME

# .app に同梱されるが、python のパッケージではないもの
# NOTE
#   これらのライセンス本文は licenses/ に置いてある。
NATIVE_LICENSE_ENTRIES = [
    ("Python", "python-LICENSE.txt"),
    ("Tcl", "tcl-license.terms"),
    ("Tk", "tk-license.terms"),
]


def clean_build_artifacts():
    """
    古い中間・成果物を削除
    """
    for path in [BUILD_DIR_PATH, DIST_DIR_PATH]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def make_version_file():
    """
    バージョン情報ファイルを生成する
    """
    # git コミットハッシュ
    commit_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
        text=True,
    ).stdout.strip()

    # ビルド日時
    build_date = datetime.now().strftime("%Y/%m/%d %H:%M")

    # 中身作ってファイルに書き込み
    version_constants_text = f"""
    COMMIT_HASH = '{commit_hash}'
    BUILD_DATE = '{build_date}'
    """
    open(VERSION_FILE_PATH, "w").write(cleandoc(version_constants_text))


def make_third_party_license_file():
    """
    .app に同梱するものの著作権表示を 1 つのファイルにまとめる（macOS 版）

    NOTE
        pyinstaller で固めた .app には python 本体・Tcl/Tk・各パッケージが
        そのまま入る。これらは MIT や BSD なので再配布できるが、
        著作権表示を配布物に含めることが条件になっている。
    NOTE
        ffmpeg と gifsicle はここに含めない。
        同梱しておらず、利用者が自分でインストールしたものを呼び出すだけなので、
        こちらに表示義務は生じない。
    """
    from importlib import metadata

    THIRD_PARTY_LICENSE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    blocks = [
        cleandoc(
            f"""
            {APP_NAME_EN} 同梱物の著作権表示

            このアプリには、以下のソフトウェアがそのまま含まれています。
            それぞれの著作権表示と許諾条件を、以下にそのまま掲載します。

            なお ffmpeg と gifsicle はこのアプリに含まれていません。
            利用者がインストールしたものを外部プログラムとして呼び出しています。
            それらの条項は licenses/ 以下を参照してください。
            """
        )
    ]

    # python 本体と Tcl/Tk
    for title, file_name in NATIVE_LICENSE_ENTRIES:
        license_file_path = LICENSES_DIR_PATH / file_name
        blocks.append(f"{'=' * 78}\n{title}\n{'=' * 78}\n")
        blocks.append(license_file_path.read_text(encoding="utf-8", errors="replace"))

    # python パッケージ
    # NOTE
    #   実際に同梱されるものを機械的に絞り込むのは難しい。
    #   足りないより多い方が安全なので、インストール済みのものを全部載せる。
    for dist in sorted(
        metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()
    ):
        name = dist.metadata["Name"]
        if not name or name == "aynime_capture_mac":
            continue
        license_texts = []
        for file in dist.files or []:
            if "licenses/" in str(file) or Path(file).name.upper().startswith(
                ("LICENSE", "COPYING", "NOTICE")
            ):
                try:
                    license_texts.append(file.read_text(encoding="utf-8"))
                except Exception:
                    continue
        if not license_texts:
            continue
        blocks.append(f"{'=' * 78}\n{name} {dist.version}\n{'=' * 78}\n")
        blocks.extend(license_texts)

    THIRD_PARTY_LICENSE_FILE_PATH.write_text("\n".join(blocks), encoding="utf-8")


def run_pyinstaller():
    """
    pyinstaller を呼び出してビルド
    """
    if sys.platform == "darwin":
        _run_pyinstaller_darwin()
        return
    subprocess.run(
        [
            "pyinstaller",
            "src\\gui\\main.py",
            f"--name={APP_NAME_EN}",
            "--onefile",
            "--strip",
            "--noconsole",
            "--log-level=WARN",
            "--collect-binaries=aynime_capture",
            "--collect-submodules=numpy",
            "--collect-submodules=aynime_capture",
            "--collect-data=numpy",
            f"--icon={APP_ICO_FILE_ABS_PATH}",
            f"--add-data={APP_ICO_FILE_ABS_PATH}:.",
            f"--distpath={DIST_APP_DIR_PATH}",
            f"--workpath={WORK_DIR_PATH}",
            f"--specpath={SPEC_DIR_PATH}",
        ],
        check=True,
    )


def _run_pyinstaller_darwin():
    """
    pyinstaller を呼び出して .app をビルドする（macOS 版）
    """
    # NOTE
    #   --onefile は使わない。
    #   起動のたびに一時ディレクトリへ展開されるので、
    #   画面収録の許可（TCC）の紐づけ先が安定しない。
    # NOTE
    #   ライセンス関係のファイルはバンドルの中に入れる。
    #   .app から起動するとカレントディレクトリが / になるため、
    #   実行ファイルと同じ階層に置く Windows 版のやり方が通用しない。
    # NOTE
    #   aynime_capture は editable install されていることがある。
    #   その場合 pyinstaller が場所を解決できないので、実際の場所を渡してやる。
    import aynime_capture

    aynime_capture_search_path = Path(aynime_capture.__file__).resolve().parent.parent

    make_third_party_license_file()

    subprocess.run(
        [
            "pyinstaller",
            "src/gui/main.py",
            f"--name={APP_NAME_EN}",
            "--onedir",
            "--strip",
            "--noconsole",
            "--log-level=WARN",
            f"--paths={aynime_capture_search_path}",
            "--collect-binaries=aynime_capture",
            "--collect-submodules=numpy",
            "--collect-submodules=aynime_capture",
            "--collect-data=numpy",
            f"--icon={APP_ICNS_FILE_ABS_PATH}",
            f"--osx-bundle-identifier={BUNDLE_IDENTIFIER}",
            # NOTE
            #   .ico はアプリのアイコン（.icns）とは別に、
            #   スプラッシュ画像として PIL から読まれる。同梱が要る。
            f"--add-data={APP_ICO_FILE_ABS_PATH}:.",
            f"--add-data={LICENSE_FILE_ABS_PATH}:.",
            f"--add-data={THIRD_PARTY_LICENSE_FILE_PATH.resolve()}:.",
            f"--add-data={LICENSES_DIR_PATH.resolve()}:licenses",
            f"--distpath={DIST_APP_DIR_PATH}",
            f"--workpath={WORK_DIR_PATH}",
            f"--specpath={SPEC_DIR_PATH}",
        ],
        check=True,
    )
    _fixup_info_plist()

    # 素の onedir 出力を削除する
    # NOTE
    #   --windowed --onedir は .app と、それとは別に素のディレクトリの
    #   両方を出力する。利用者に要るのは .app だけで、
    #   そのまま zip に含めると配布物のサイズが倍になる。
    shutil.rmtree(DIST_APP_DIR_PATH / APP_NAME_EN, ignore_errors=True)


def _fixup_info_plist():
    """
    .app の Info.plist に足りないキーを書き込む（macOS 版）
    """
    plist_file_path = DIST_APP_BUNDLE_PATH / "Contents" / "Info.plist"
    with plist_file_path.open("rb") as f:
        plist = plistlib.load(f)
    # NOTE
    #   ScreenCaptureKit が macOS 12.3 以降を要求する。
    plist["LSMinimumSystemVersion"] = MINIMUM_SYSTEM_VERSION
    # NOTE
    #   これが無いと Retina でぼやける。
    plist["NSHighResolutionCapable"] = True
    with plist_file_path.open("wb") as f:
        plistlib.dump(plist, f)
    # NOTE
    #   pyinstaller は .app を ad-hoc 署名する。
    #   その後に Info.plist を書き換えると署名が壊れるので、署名し直す。
    #   （codesign --verify が "invalid Info.plist" で落ちる状態になる）
    subprocess.run(
        ["codesign", "--force", "--sign", "-", str(DIST_APP_BUNDLE_PATH)],
        check=True,
        capture_output=True,
    )


def put_files():
    """
    その他同梱したいファイルを配置する
    """
    # ライセンスファイルを同梱
    shutil.copyfile(
        LICENSE_FILE_ABS_PATH, DIST_APP_DIR_PATH / LICENSE_FILE_ABS_PATH.name
    )
    if sys.platform == "darwin":
        shutil.copyfile(
            THIRD_PARTY_LICENSE_FILE_PATH,
            DIST_APP_DIR_PATH / THIRD_PARTY_LICENSE_FILE_NAME,
        )
    DIST_APP_LICENSE_DIR_PATH.mkdir(parents=True, exist_ok=True)
    for p in LICENSES_DIR_PATH.glob("**/*.*"):
        shutil.copyfile(p, DIST_APP_LICENSE_DIR_PATH / p.name)


def zip_executable():
    """
    成果物を zip 圧縮する
    """
    # zip ファイルパスを生成
    date_str = datetime.now().strftime("%Y%m%d")
    zip_file_stem = f"{APP_NAME_EN}_{date_str}"
    zip_file_base_path = ZIP_OUTPUT_DIR / zip_file_stem

    # 出力フォルダを確保
    ZIP_OUTPUT_DIR.mkdir(exist_ok=True)

    # zip ファイルに圧縮
    # NOTE
    #   .app はシンボリックリンクを含むので、macOS では ditto を使う。
    #   zipfile 経由だとリンクが実体化されて、バンドルが壊れる。
    if sys.platform == "darwin":
        subprocess.run(
            [
                "ditto",
                "-c",
                "-k",
                "--keepParent",
                str(DIST_APP_DIR_PATH),
                str(zip_file_base_path.with_suffix(".zip")),
            ],
            check=True,
        )
    else:
        shutil.make_archive(
            base_name=str(zip_file_base_path), format="zip", root_dir=DIST_DIR_PATH
        )


def main():
    """
    メイン関数
    """
    clean_build_artifacts()
    make_version_file()
    run_pyinstaller()
    put_files()
    zip_executable()


if __name__ == "__main__":
    main()
