# Technocore Easy Setup

**English** | [日本語](README.ja.md)

A bilingual desktop GUI that lets non-technical users create a Technocore DID and publish signed messages without using terminal commands for each action.

The MVP includes:

- Create DID
- Show DID
- Join `lobby`
- Post a signed message
- Register a public contribution URL
- Generate a contribution proof for a full Git commit

This is an independent community project. It is not an official Flop Labs tool and does not guarantee rewards, `$FLOP`, eligibility, or allocation.

## Security model

The app creates one Ed25519 key and stores it as an encrypted PKCS#8 PEM file in your local user profile. The identity file is never overwritten. A passphrase of at least 12 characters is required and is never saved.

Only these public values are sent to `https://technocore.chat` when you explicitly confirm a post:

- public DID
- Ed25519 signature
- nonce
- normalized message text

The private key and passphrase are never included in a network request. The MVP is pinned to the Technocore HTTPS host and does not expose a custom-server field.

Identity location:

- macOS: `~/Library/Application Support/Technocore Easy Setup/identity.pem`
- Windows: `%LOCALAPPDATA%\Technocore Easy Setup\identity.pem`

Back up the encrypted `identity.pem` and its passphrase separately. Never publish the PEM file, add it to Git, send it by chat, or upload it to a reward/claim page. The public `did:key:z6Mk...` is safe to share.

See [SECURITY.md](SECURITY.md) for the full boundary and recovery notes.

## Desktop downloads

Preview packages for macOS Apple silicon, macOS Intel, and Windows x64 are published on the
[Releases page](https://github.com/244whopper-cyber/technocore-easy-setup/releases). They include Python and Tk, so users do not need to install Python separately.

The preview packages are not yet Apple Developer ID/notarization or Windows Authenticode signed. Read `README-FIRST.txt` inside the ZIP and verify the accompanying SHA-256 checksum. Do not disable operating-system security globally. The source-based method below remains the recommended option until signed packages are available.

If macOS displays **“TechnocoreEasySetup Not Opened”**, only continue after confirming that the ZIP came from this repository's Releases page and its SHA-256 matches the accompanying `.sha256` file:

1. Click **Done** in the warning.
2. Open **System Settings → Privacy & Security**.
3. Scroll to Security and click **Open Anyway** for `TechnocoreEasySetup`.
4. Authenticate with your Mac login and click **Open** in the final prompt.

This creates an exception for this app only. Never disable Gatekeeper or macOS security globally. See [Apple's official guidance](https://support.apple.com/102445).

## Run from source

This MVP uses the same Python 3.12 baseline and `cryptography` versions as `technocore-did-starter` v1.0.0.

Download the repository with Git, or use **Code → Download ZIP** on
[`244whopper-cyber/technocore-easy-setup`](https://github.com/244whopper-cyber/technocore-easy-setup).

```sh
git clone https://github.com/244whopper-cyber/technocore-easy-setup.git
```

### macOS

1. Install Python 3.12 from [python.org](https://www.python.org/downloads/macos/). The python.org installer includes Tk, which this GUI needs.
2. Download or clone this repository.
3. Double-click `start_macos.command`.

If macOS opens the script in a text editor, open Terminal in this folder and run:

```sh
./start_macos.command
```

The script creates a private `.venv`, installs the pinned dependency, and opens the GUI. It does not create a DID until you press **Create DID**.

### Windows

1. Install Python 3.12 from [python.org](https://www.python.org/downloads/windows/) and enable **Add python.exe to PATH**.
2. Download or clone this repository.
3. Double-click `start_windows.bat`.

The script creates a private `.venv`, installs the pinned dependency, and opens the GUI. It does not create a DID until you press **Create DID**.

## Using the six actions

1. **Create DID** — enter and confirm a new 12+ character passphrase. This is a one-time action; an existing identity is never replaced.
2. **Show DID** — unlock the local encrypted key and copy the public DID.
3. **Join lobby** — review the public message and destination, then sign and publish once.
4. **Post signed message** — choose a valid room and review the message before publishing.
5. **Register contribution URL** — enter a public HTTPS URL and a short description. The app follows the starter guide by posting a signed URL announcement to the `technocore` room; there is no separate registration API.
6. **Generate contribution proof** — for Git-based work only, enter the public repository URL and the complete 40- or 64-character commit ID. The app writes a new public JSON file, verifies its signature, and refuses to overwrite a file.

Already used `technocore-did-starter`? Before creating a new DID, choose **Use an existing identity.pem** in the identity status panel. The app verifies the passphrase and Ed25519 key, copies the encrypted file into its local application folder, and leaves the source file unchanged. This preserves your existing public DID and participation history.

For an X post, video, article, or graphic that is not stored in Git, action 5 is sufficient; a Git contribution proof is optional and should not be fabricated.

## Build desktop packages

Maintainers can create an unsigned local build with:

```sh
./scripts/build_macos.sh
```

or on Windows PowerShell:

```powershell
.\scripts\build_windows.ps1
```

The macOS artifact appears at `dist/TechnocoreEasySetup.app`; the Windows artifact appears under `dist/Technocore Easy Setup/`. Public releases should be code-signed, notarized on macOS, Authenticode-signed on Windows, malware-scanned, and accompanied by SHA-256 checksums. Do not ask users to disable operating-system security globally.

## Test

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
```

The tests cover encrypted local identity creation, overwrite refusal, protocol normalization, canonical proof generation and verification, outbound-field minimization, and strict receipt matching. No test posts to Technocore.

## Compatibility baseline

Protocol behavior was matched against [`zunmax/technocore-did-starter`](https://github.com/zunmax/technocore-did-starter) v1.0.0 at commit `3cc03a6e908e8776de9fdd465c53d23d31db2e9f`:

- `did:key` construction: Ed25519 multicodec `0xed01` + base58btc
- signed payload: `room|nonce|normalized-text`
- signature: unpadded base64url Ed25519
- network write: `POST /r/{room}?format=json`
- proof schema: `technocore-contribution-proof-v1`

The onboarding wording and safety notes align with [`244whopper-cyber/technocore-japanese-guide`](https://github.com/244whopper-cyber/technocore-japanese-guide) at commit `a5ec4e021f6a70ae4ad7cd5b6303f7e78730b838`.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
