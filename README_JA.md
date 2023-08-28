# 🇯🇵 Network File System (NFS) — Free Edition

> [🇪🇸 Español](README_ES.md) · [🇧🇷 Português](README_PT.md) · [🇬🇧 English](README_EN.md) · [🇩🇪 Deutsch](README_DE.md) · [🇷🇺 Русский](README_RU.md)

グラフィカルインターフェースを通じた完全なNFS管理を提供するaaPanel向けの無料オープンソースプラグインです。エクスポート（共有）の作成、リモートディレクトリのマウント、NFSサーバーの監視、マウント失敗の自動診断が可能です。

```
作者:      Jose Alexis Correa Valencia (jalexiscv)
バージョン: 1.0
ライセンス: MIT — フリーソフトウェア
```

---

## 目次

1. [NFSプロトコルについて](#1-nfsプロトコルについて)
2. [プラグインの機能](#2-プラグインの機能)
3. [システム要件](#3-システム要件)
4. [インストール](#4-インストール)
5. [ファイル構成](#5-ファイル構成)
6. [ポートとファイアウォール](#6-ポートとファイアウォール)
7. [設定ファイル](#7-設定ファイル)
8. [起動時の自動マウント](#8-起動時の自動マウント)
9. [障害診断](#9-障害診断)
10. [メンテナンススクリプト](#10-メンテナンススクリプト)
11. [バックエンドAPI](#11-バックエンドapi)
12. [コントリビューション](#12-コントリビューション)
13. [サポートとコミュニティ](#13-サポートとコミュニティ)
14. [ライセンス](#14-ライセンス)
15. [作者](#15-作者)
16. [寄付](#16-寄付)

---

## 1. NFSプロトコルについて

**Network File System（NFS）** は、1984年にSun Microsystemsが開発した分散ファイルシステムプロトコルです。オペレーティングシステムがネットワーク上の別のコンピュータに保存されたファイルに、ローカルファイルと同じ方法でアクセスできるようにし、ストレージの物理的な場所をアプリケーションから透過的に扱えるようにします。

NFSはクライアント/サーバーモデルで動作します：サーバーはディレクトリを**エクスポート**してネットワークに公開し、クライアントはそれを自分のボリュームであるかのようにローカルに**マウント**します。通信はTCPまたはUDP上のリモートプロシージャコール（RPC）によって行われます。

### プロトコルバージョン

| バージョン | 年    | 主な特徴 |
|-----------|-------|---------|
| NFSv2     | 1989  | 最初の広く普及したバージョン；UDPのみ；最大2GBのファイル |
| NFSv3     | 1995  | TCPサポート；大容量ファイル（64ビット）；非同期書き込み |
| NFSv4     | 2003  | ステートフルプロトコル；強力な認証（Kerberos）；単一ポート（2049）；ACLサポート |
| NFSv4.1   | 2010  | pNFS（並列アクセス）；耐障害性セッション；クラスターサポート向上 |

### 一般的なユースケース

- アプリケーションサーバー間の共有ストレージ
- Linux/Unix環境における集中管理ホームディレクトリ
- 分散バックアップインフラストラクチャ
- HPCクラスターおよびKubernetesの共有ストレージ
- Webサーバー間の静的アセット（画像、動画）の共有

> **セキュリティ:** NFSはKerberos + RPCSEC_GSSを使用しない限り、転送中のデータを暗号化しません。常に信頼できるサブネットへのアクセスを制限し、NFSポートをインターネットに公開しないことを強く推奨します。

---

## 2. プラグインの機能

- **共有（NFSエクスポート）:** 認証済みIP制御（CIDR）、読み取り/書き込みモード、同期、パーミッションスカッシュポリシーを含む、リモートクライアントからアクセス可能なローカルディレクトリを定義します。
- **マウント（リモートマウント）:** バージョン（NFSv3/NFSv4）、ブロックサイズ（rsize/wsize）、タイムアウト、TCP/UDP、ハード/ソフトマウントの完全なプロトコルオプションで他のNFSサーバーの共有リソースに接続します。
- **サーバー監視:** `nfs-server`と`rpcbind`のステータス、登録済みRPCサービス、`/proc/net/rpc`からのプロトコル統計、`nfsiostat`によるマウントごとのI/Oメトリクス。
- **起動時自動マウント:** システムinitサービスを通じて`auto_mount=1`で設定されたリソースを自動的にマウントします。
- **接続追跡:** アクティブなマウントと接続クライアントをリアルタイムで監視し、プラグイン外での状態変化を検出します。
- **インテリジェント障害診断:** 7ステップの検証シーケンス（ping、IP検出、ポートチェック、showmount、CIDRマッチング）で正確な原因とアクション可能な提案を返します。
- **アクティビティログ:** イベントタイプ、結果、IPアドレスによるフィルターを備えたすべての操作のスレッドセーフなログ。

---

## 3. システム要件

| コンポーネント | 要件 |
|---|---|
| パネル | aaPanel（BTパネル）インストール済み |
| オペレーティングシステム | Ubuntu/Debian 16.04+ · CentOS/RHEL/Rocky/Alma 7+ |
| Python | 3.6+（パネル環境に含まれる） |
| システムパッケージ | `nfs-kernel-server` + `nfs-common`（Debian/Ubuntu） · `nfs-utils`（RHEL/CentOS） |

---

## 4. インストール

```bash
# 1. プラグインをパネルディレクトリにコピー
cp -r nfs_free/ /www/server/panel/plugin/nfs_free/

# 2. インストーラーを実行
sudo bash /www/server/panel/plugin/nfs_free/install.sh install
```

インストーラーは自動的に処理します：

- NFSパッケージのインストール
- mountdのポート20048への固定
- ufwでのファイアウォールポートの開放（有効な場合）
- `/etc/init.d/nfs_free`へのinitサービスの登録
- systemdによる`nfs-server`と`rpcbind`の有効化
- aaPanelの再読み込み

**アンインストール:**

```bash
sudo bash /www/server/panel/plugin/nfs_free/install.sh uninstall
```

> アンインストール時、システムNFSパッケージと`/etc/exports`は**変更されません**。

**依存関係の手動インストール（自動インストーラーが失敗した場合）:**

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y nfs-kernel-server nfs-common rpcbind

# RHEL/CentOS/Rocky/Alma
sudo yum install -y nfs-utils rpcbind
```

---

## 5. ファイル構成

```
nfs_free/
├── info.json              # プラグインメタデータ（名前、バージョン、作者）
├── icon.png               # 512×512 RGBAアイコン
├── index.html             # フロントエンド: CSS + HTML + JavaScript
├── nfs_free_main.py       # バックエンド: nfs_free_mainクラス（32メソッド）
├── nfs_free_service       # 起動時auto_mount()用Pythonラッパー
├── install.sh             # インストールとアンインストール
├── init.sh                # 自動マウント用/etc/init.dスクリプト
├── upgrade.sh             # NFSパッケージの更新とサービス再起動
├── repair.sh              # mountdポートの再設定と再起動
└── config/
    ├── share.json             # 設定済みNFSエクスポート
    ├── mount.json             # 設定済みリモートマウント
    ├── connection_state.json  # 現在の接続状態スナップショット
    └── activity.log.json      # アクティビティログ（最新1000エントリ）
```

---

## 6. ポートとファイアウォール

NFSでは**サーバー**で以下のポートを開放する必要があります：

| ポート | サービス | プロトコル | 説明 |
|-------|---------|-----------|------|
| 111   | rpcbind  | TCP/UDP   | ポートマッパー — RPCサービスを検出 |
| 2049  | nfs      | TCP       | メインNFSプロトコル |
| 20048 | mountd   | TCP/UDP   | マウントリクエスト（固定ポート） |
| 32874 | lockd    | TCP/UDP   | ファイルロック |
| 32876 | statd    | TCP/UDP   | 状態回復 |

デフォルトではmountdはrpcbindが割り当てるランダムポートを使用します。プラグインは`/etc/nfs.conf`を設定してポート**20048**に固定し、サーバー間で予測可能なファイアウォールルールを実現します。

```bash
# ufwで特定のサブネットにポートを開放
sudo ufw allow from 192.168.1.0/24 to any port 111
sudo ufw allow from 192.168.1.0/24 to any port 2049
sudo ufw allow from 192.168.1.0/24 to any port 20048
```

---

## 7. 設定ファイル

### share.json — NFSエクスポート

```json
[
  {
    "share_name": "backups",
    "path": "/www/backup",
    "rw_mode": "rw",
    "sync_mode": "async",
    "squash": "all_squash",
    "user": "nfsnobody",
    "limit_address": "192.168.1.0/24",
    "ps": "日次バックアップ"
  }
]
```

### mount.json — リモートマウント

```json
[
  {
    "mount_name": "production",
    "server_address": "192.168.1.100",
    "nfs_path": "/data/app",
    "mount_path": "/mnt/nfs-prod",
    "proto": "tcp",
    "rw_mode": "rw",
    "hard": 1,
    "rsize": 1048576,
    "wsize": 1048576,
    "timeo": 600,
    "vers": 4,
    "auto_mount": 1
  }
]
```

---

## 8. 起動時の自動マウント

`/etc/init.d/nfs_free`サービスがシステム起動時に`auto_mount=1`のすべてのリソースを自動的にマウントします。

```
システム起動
  → /etc/init.d/nfs_free start
    → nfs_free_service（Python）
      → nfs_free_main.auto_mount()
        → auto_mount=1の各マウントに対して：
            既にマウントされているか確認（mountpoint -q）
            マウントされていない場合: mount -t nfs -o ... を実行
```

```bash
/etc/init.d/nfs_free start    # 開始
/etc/init.d/nfs_free stop     # 停止
/etc/init.d/nfs_free restart  # 再起動
/etc/init.d/nfs_free status   # 状態確認
```

---

## 9. 障害診断

マウントが失敗した場合、システムは自動的に7ステップの検証シーケンスを実行します：

| ステップ | 確認内容 | ツール |
|---------|---------|-------|
| 1 | サーバーへの到達可能性 | `ping -c 1 -W 2` |
| 2 | クライアントの送信元IP | `ip route get` |
| 3 | ポート111、2049、20048 | `/dev/tcp` |
| 4 | サーバーのエクスポートリスト | `showmount -e` |
| 5 | エクスポートにパスが存在するか | showmount出力の解析 |
| 6 | アクセスルールにクライアントIPが含まれるか | `ipaddress.ip_network()` CIDR |
| 7 | カーネルエラーメッセージのヒント | キーワード分析 |

---

## 10. メンテナンススクリプト

```bash
# mountdポートを修復してサービスを再起動
sudo bash /www/server/panel/plugin/nfs_free/repair.sh

# NFSシステムパッケージを更新
sudo bash /www/server/panel/plugin/nfs_free/upgrade.sh
```

---

## 11. バックエンドAPI

`nfs_free_main`クラスは5つのカテゴリに32のメソッドを公開しています：

| カテゴリ | 主なメソッド |
|---|---|
| 共有 | `get_share_list`, `create_share`, `modify_share`, `remove_share`, `show_ip_share_list` |
| マウント | `get_mount_list`, `create_mount`, `modify_mount`, `remove_mount`, `to_mount`, `to_umount`, `auto_mount` |
| サーバー | `get_server_status`, `server_admin`, `get_overview`, `get_nfsstat`, `get_nfsiostat` |
| 接続 | `get_connections`, `get_disk_mounts`, `get_nfs_ports`, `fix_mountd_port` |
| ログ | `get_log`, `clear_log` |

---

## 12. コントリビューション

このプロジェクトは**オープンソース**であり、コミュニティによって支えられています。あなたのコントリビューションを歓迎します！

### コントリビューションの方法

1. リポジトリを**フォーク**する
2. フィーチャーブランチを作成する：
   ```bash
   git checkout -b feature/新機能
   ```
3. 変更を加え、aaPanelでプラグインが動作することを確認する
4. 変更をコミットする：
   ```bash
   git commit -m 'Add: 変更内容の明確な説明'
   ```
5. ブランチにプッシュする：
   ```bash
   git push origin feature/新機能
   ```
6. **プルリクエスト**を開く

### コントリビューションガイドライン

- Pythonコードには[PEP-8](https://pep8.org/)スタイルガイドに従う
- すべてのパブリックメソッドをdocstringで文書化する
- 新機能にはテストを追加する
- 関連するドキュメントを更新する
- aaPanelプラグインインターフェースとの互換性を維持する

### サポートが必要な領域

- 📝 ドキュメントの改善
- 🧪 ユニットテストと統合テスト
- 🎨 パネルUIの改善
- 🔧 新しいNFS機能（Kerberosサポート、追加メトリクス）
- 🌍 ドキュメントの翻訳
- 🐛 バグレポート

---

## 13. サポートとコミュニティ

### サポートが必要ですか？

- 🐛 **バグの報告:** [GitHubでissueを開く](https://github.com/jalexiscv/nfs_free/issues)
- 💡 **機能のリクエスト:** [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)を使用する
- 📧 **直接連絡:** jalexiscv@gmail.com

### コミュニティ

- [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)で会話に参加する
- ["good first issue"ラベルのissue](https://github.com/jalexiscv/nfs_free/labels/good%20first%20issue)を確認する

---

## 14. ライセンス

**MIT**ライセンスの下で配布されます。

> MITライセンスは、元の著作権表示が含まれている限り、制限なしにソフトウェアのコピーを使用、コピー、変更、統合、公開、配布、サブライセンス、販売することを許可します。

---

## 15. 作者

**Jose Alexis Correa Valencia**
*フルスタック開発者 & ソフトウェアアーキテクト*

エンタープライズソフトウェア開発において25年以上の経験を持ち、スケーラブルなアーキテクチャとLinuxインフラストラクチャを専門としています。

- **GitHub:** [@jalexiscv](https://github.com/jalexiscv)
- **LinkedIn:** [Jose Alexis Correa Valencia](https://www.linkedin.com/in/jalexiscv/)
- **メール:** jalexiscv@gmail.com
- **所在地:** コロンビア 🇨🇴

---

## 16. 寄付

このプラグインがあなたやあなたのビジネスに役立った場合は、継続的な開発とメンテナンスへのサポートをご検討ください。

| 方法 | 詳細 |
|------|------|
| **PayPal** | [jalexiscv@gmail.com](https://www.paypal.com/paypalme/jalexiscv) |
| **Nequi（コロンビア）** | `3117977281` |

あなたのサポートは以下の助けになります：
- 新機能の開発を加速する
- より多くのドキュメントと例を作成する
- テストカバレッジを改善する
- プロジェクトをアクティブかつ最新の状態に保つ

*ご支援ありがとうございます！*

---

*Network File System (NFS) Free Edition — Copyright © 2023 Jose Alexis Correa Valencia — 2023年7月17日公開 — MIT License*
