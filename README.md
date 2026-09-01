# えぃにめ一閃流奥義「一閃」 macOS 版

## TL;DR
- アニメのスクショを撮って Discord に投げる営みを保証する GUI ツールの **macOS 版**
- 原作（Windows 専用）は [Nu-Pan/aynime_issen_style](https://github.com/Nu-Pan/aynime_issen_style)
- 使い方は原作の [wiki](https://github.com/Nu-Pan/aynime_issen_style/wiki/User's-Manual) と同じ

## 原作との関係
- 本リポジトリは原作の fork。**macOS で動かすために必要な差分だけ**を持つ
- 原作にない機能・改善・拡張は入れない。挙動に迷ったら原作（Windows 版）を正とする
- Windows 側の挙動は変えない。共通コードは両 OS で同じ結果になるようにしてある
- **原作リポジトリへは変更を送らない**
- キャプチャ部分は Windows 版の `aynime_capture`（C++ / Windows.Graphics.Capture）ではなく、
  ScreenCaptureKit で実装した [chikuwav/aynime_capture_mac](https://github.com/chikuwav/aynime_capture_mac) を使う

## 動作環境
- macOS 12.3 以上（ScreenCaptureKit を使うため）
- Python 3.13（Tcl/Tk 8.6 系。CustomTkinter 5.2.2 が Tk 9 を想定していない）
- ffmpeg / gifsicle … `brew install ffmpeg gifsicle`
- 画面収録の許可（システム設定 > プライバシーとセキュリティ > 画面収録）

## セットアップ
```
python3.13 -m venv .venv
.venv/bin/pip install -e .
```

## 実行方法
リポジトリのルートで、以下を実行する。

```
PYTHONPATH=src .venv/bin/python src/gui/main.py
```

カレントディレクトリはリポジトリのルートである必要がある。

## macOS 固有の注意
- **画面収録の許可は「起動元アプリ」に紐づく。** ターミナルから起動したならターミナル、VSCode から起動したなら VSCode に許可を与える
- **許可は起動時にしか読み直されない。** 許可を与えたら、起動元のアプリを再起動する
- ウィンドウが 1 件も列挙されない場合は、まず許可が古いことを疑う
- 対象ウィンドウが最小化中・別 Space にあると、フレームが止まる。原作 wiki の推奨構成（アニメを別ディスプレイでフルスクリーン）なら問題にならない
- macOS 15 以降、画面収録の許可は月に一度、再確認を求められる

## ファイルの保存先
Windows 版は実行ファイルと同じ階層に置くが、macOS では OS の作法に従う。

| 用途 | パス |
|---|---|
| キャプチャ結果 | `~/Pictures/aynime_issen_style/{nime,raw,tensei}` |
| 設定・外部ツール | `~/Library/Application Support/aynime_issen_style/` |
| ログ | `~/Library/Logs/aynime_issen_style/` |

## ライセンス
MIT。原作者の著作権表示は [LICENSE](LICENSE) に保持している。
同梱している `ctk_tabview.py` は CustomTkinter のファイルなので、
その著作権表示を [licenses/customtkinter-MIT.txt](licenses/customtkinter-MIT.txt) に置いてある。
