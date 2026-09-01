# Technocore Easy Setup

[English](README.md) | **日本語**

非技術者でも、ターミナルでコマンドを一つずつ実行せずにTechnocoreへ参加できる日英対応デスクトップGUIです。

MVPでは次の6機能を利用できます。

- DIDを作成
- DIDを表示
- `lobby` に参加
- 署名メッセージを投稿
- 公開した貢献URLを登録
- 完全なGitコミットに対する貢献Proofを作成

これは独立したコミュニティ製ツールです。Flop Labs公式ツールではなく、報酬、`$FLOP`、参加資格、配布量を保証しません。

## 安全設計

アプリはEd25519秘密鍵を1つ作成し、暗号化PKCS#8 PEMとして端末内のユーザーフォルダに保存します。既存の秘密鍵は上書きしません。12文字以上のパスフレーズが必要で、パスフレーズ自体は保存しません。

投稿を明示的に確認したときだけ、次の公開情報を `https://technocore.chat` へ送ります。

- 公開DID
- Ed25519署名
- nonce
- 正規化済みメッセージ本文

秘密鍵とパスフレーズはネットワーク送信に含めません。MVPの接続先はTechnocoreのHTTPSホストに固定し、任意サーバー欄は設けていません。

秘密鍵ファイルの場所:

- macOS: `~/Library/Application Support/Technocore Easy Setup/identity.pem`
- Windows: `%LOCALAPPDATA%\Technocore Easy Setup\identity.pem`

暗号化済み `identity.pem` とパスフレーズは別々の安全な場所へバックアップしてください。PEMファイルをGitHub、チャット、クラウド共有、報酬請求ページへ公開・送信してはいけません。公開DID `did:key:z6Mk...` は共有できます。

詳しくは [SECURITY.md](SECURITY.md) を確認してください。

## デスクトップ版をダウンロード

[Releasesページ](https://github.com/244whopper-cyber/technocore-easy-setup/releases) から、macOS Apple silicon版、macOS Intel版、Windows x64版の試用パッケージを入手できます。PythonとTkを同梱するため、利用者が別途Pythonをインストールする必要はありません。

現在の試用版は、Apple Developer ID署名・公証およびWindows Authenticode署名が未実施です。ZIP内の `README-FIRST.txt` を読み、同時に配布されるSHA-256チェックサムを確認してください。OSのセキュリティ機能を全体的に無効化してはいけません。正式な署名済みパッケージが用意されるまでは、下記のソースからの起動を推奨します。

## ソースから起動する

このMVPは、既存の `technocore-did-starter` v1.0.0と同じPython 3.12および `cryptography` の組み合わせを基準にしています。

Gitで取得するか、[`244whopper-cyber/technocore-easy-setup`](https://github.com/244whopper-cyber/technocore-easy-setup) の **Code → Download ZIP** からダウンロードできます。

```sh
git clone https://github.com/244whopper-cyber/technocore-easy-setup.git
```

### macOS

1. [python.org](https://www.python.org/downloads/macos/) からPython 3.12をインストールします。GUIに必要なTkも同梱されています。
2. このリポジトリをダウンロードまたはcloneします。
3. `start_macos.command` をダブルクリックします。

スクリプトがテキストエディタで開く場合は、このフォルダでTerminalを開き、次を実行します。

```sh
./start_macos.command
```

専用の `.venv` と必要ライブラリを準備してGUIを開きます。**DIDを作成**ボタンを押すまで秘密鍵は作りません。

### Windows

1. [python.org](https://www.python.org/downloads/windows/) からPython 3.12をインストールし、**Add python.exe to PATH** を有効にします。
2. このリポジトリをダウンロードまたはcloneします。
3. `start_windows.bat` をダブルクリックします。

専用の `.venv` と必要ライブラリを準備してGUIを開きます。**DIDを作成**ボタンを押すまで秘密鍵は作りません。

## 6機能の使い方

1. **DIDを作成** — 新しい12文字以上のパスフレーズを2回入力します。作成は1回だけで、既存DIDは上書きされません。
2. **DIDを表示** — ローカルの暗号化鍵を開き、共有可能な公開DIDだけを表示します。
3. **lobbyに参加** — 公開される本文と送信先を確認してから、1回だけ署名投稿します。
4. **署名メッセージを投稿** — Roomと本文を指定し、公開前に内容を確認します。
5. **貢献URLを登録** — 公開HTTPS URLと短い説明を入力します。Starterガイドどおり、URL入りメッセージを同じDIDで `technocore` Roomへ署名投稿します。専用の「登録API」があるわけではありません。
6. **貢献Proofを作成** — Gitに保存した成果物だけが対象です。公開リポジトリURLと完全な40桁または64桁コミットIDを入力します。新しい公開JSONを保存して署名を検証し、既存ファイルは上書きしません。

すでに `technocore-did-starter` を使っている場合は、新しいDIDを作らず、DID状態欄の **既存のidentity.pemを使用** を選んでください。パスフレーズとEd25519鍵を検証して暗号化ファイルをアプリのローカルフォルダへコピーし、元ファイルは変更しません。既存の公開DIDと参加履歴をそのまま使えます。

X投稿、動画、記事、画像などGitに置かない成果物は5までで構いません。Git Proofは任意であり、実在しないコミットを作ってはいけません。

## 配布用アプリをビルドする

macOSの保守担当者:

```sh
./scripts/build_macos.sh
```

Windows PowerShell:

```powershell
.\scripts\build_windows.ps1
```

macOS版は `dist/TechnocoreEasySetup.app`、Windows版は `dist/Technocore Easy Setup/` に作られます。一般公開版はコード署名、macOS notarization、Windows Authenticode署名、マルウェアスキャン、SHA-256チェックサムを用意してください。OSのセキュリティ機能を全体的に無効化する案内はしないでください。

## テスト

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
```

テストでは、秘密鍵の暗号化、上書き拒否、本文正規化、Proof生成・検証、送信項目の最小化、サーバー応答の厳密照合を確認します。テストからTechnocoreへ投稿はしません。

## 既存ガイドとの整合

署名・DID・Proof仕様は [`zunmax/technocore-did-starter`](https://github.com/zunmax/technocore-did-starter) v1.0.0、commit `3cc03a6e908e8776de9fdd465c53d23d31db2e9f` と照合しています。

参加手順と注意書きは [`244whopper-cyber/technocore-japanese-guide`](https://github.com/244whopper-cyber/technocore-japanese-guide) のcommit `a5ec4e021f6a70ae4ad7cd5b6303f7e78730b838` に合わせています。

## ライセンス

MITです。[LICENSE](LICENSE) と [NOTICE.md](NOTICE.md) を参照してください。
