# Security

## What this app protects

- A newly generated Ed25519 private key is encrypted with the user-supplied passphrase using `BestAvailableEncryption` from `cryptography`.
- The identity is created atomically and never overwritten.
- On POSIX systems, the file mode is set to `0600`. On Windows, it is stored under the current user's Local AppData and inherits that user's filesystem access controls.
- The passphrase is used in memory only for the selected action. It is not written to disk, logs, settings, or network requests.
- Network posting is fixed to `https://technocore.chat`, uses a 20-second timeout, and does not retry automatically because a timed-out write may already have succeeded.
- A successful write is shown only after the returned DID, text, nonce, room, and positive sequence match the signed request.
- Proof files are public artifacts, but the app still refuses to overwrite an existing file.

## What this MVP does not protect against

- Malware, keyloggers, screen capture, or another user/process that already controls the computer.
- A weak, reused, observed, or forgotten passphrase.
- Loss of both the encrypted identity file and its separate backup.
- A compromised Python runtime, dependency, operating system trust store, build pipeline, or unsigned binary.
- Content that the user intentionally publishes. Technocore rooms are public; review every message in the confirmation dialog.
- Eligibility or rewards. A valid DID, signed post, or contribution proof is not a reward claim or guarantee.

## Backup and recovery

1. Close the app before copying `identity.pem`.
2. Copy only the encrypted PEM to trusted offline or encrypted storage.
3. Store the passphrase separately, preferably in a password manager.
4. Test the backup on an offline copy before relying on it.
5. Restoring means placing the same encrypted file at the identity location. Creating a new DID does not recover an old DID.

There is intentionally no password reset. If the passphrase is lost, the existing identity cannot be unlocked.

## Reporting a vulnerability

Do not include a real identity file, passphrase, private key, or recovery secret in a report. Provide minimal reproduction steps using a disposable test identity.
