#!/usr/bin/env python3
"""Umbrel setup UI + API for Buzz Relay owner pubkey.

Serves /umbrel-setup/ (proxied by nginx). Lets the operator set
RELAY_OWNER_PUBKEY to an existing Buzz Desktop identity without SSH.
"""

from __future__ import annotations

import html
import os
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SECRETS = Path(os.environ.get("BUZZ_SECRETS_DIR", "/secrets"))
OVERRIDE = SECRETS / "owner-pubkey.override"
OWNER_PUBKEY_FILE = SECRETS / "owner.pubkey"
OWNER_SECRET_FILE = SECRETS / "owner.secret"
RELAY_ENV = SECRETS / "relay.env"
JOIN_TXT = Path(os.environ.get("BUZZ_SETUP_DIR", "/setup")) / "JOIN.txt"

WS_URL = os.environ.get(
    "BUZZ_WS_URL",
    "ws://umbrel.local:3737",
)
HTTP_ORIGIN = os.environ.get(
    "BUZZ_HTTP_ORIGIN",
    "http://umbrel.local:3737",
)

HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# Minimal Bech32 (BIP-173) for npub → hex. No third-party deps on Umbrel.
_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_GENERATORS = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)


def _polymod(values: list[int]) -> int:
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            if (b >> i) & 1:
                chk ^= _GENERATORS[i]
    return chk


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _bech32_decode(bech: str) -> tuple[str, list[int]] | None:
    if any(ord(c) < 33 or ord(c) > 126 for c in bech):
        return None
    if bech.lower() != bech and bech.upper() != bech:
        return None
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
        return None
    hrp, data_part = bech[:pos], bech[pos + 1 :]
    try:
        data = [_CHARSET.index(c) for c in data_part]
    except ValueError:
        return None
    if _polymod(_hrp_expand(hrp) + data) != 1:
        return None
    return hrp, data[:-6]


def _convertbits(data: list[int], from_bits: int, to_bits: int, pad: bool) -> list[int] | None:
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << to_bits) - 1
    for value in data:
        if value < 0 or value >> from_bits:
            return None
        acc = (acc << from_bits) | value
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (to_bits - bits)) & maxv)
    elif bits >= from_bits or ((acc << (to_bits - bits)) & maxv):
        return None
    return ret


def npub_to_hex(npub: str) -> str | None:
    decoded = _bech32_decode(npub.strip())
    if not decoded:
        return None
    hrp, data = decoded
    if hrp != "npub":
        return None
    raw = _convertbits(data, 5, 8, False)
    if raw is None or len(raw) != 32:
        return None
    return bytes(raw).hex()


def parse_owner_input(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if HEX_RE.match(value):
        return value.lower()
    if value.lower().startswith("npub1"):
        return npub_to_hex(value)
    return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def current_owner_pubkey() -> str:
    if OVERRIDE.is_file():
        return read_text(OVERRIDE)
    return read_text(OWNER_PUBKEY_FILE)


def bootstrap_secret() -> str:
    if OVERRIDE.is_file():
        return ""
    return read_text(OWNER_SECRET_FILE)


def update_relay_env(owner_pubkey: str) -> None:
    lines: list[str] = []
    if RELAY_ENV.is_file():
        for line in RELAY_ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith("RELAY_OWNER_PUBKEY="):
                continue
            if line.strip():
                lines.append(line)
    else:
        lines.append("BUZZ_RELAY_PRIVATE_KEY=")
    lines.append(f"RELAY_OWNER_PUBKEY={owner_pubkey}")
    RELAY_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    RELAY_ENV.chmod(0o600)


def write_join_txt(owner_pubkey: str, owner_secret: str) -> None:
    body = (
        "Buzz Relay — Umbrel join info\n"
        "=============================\n\n"
        f"Web UI:     {HTTP_ORIGIN}/\n"
        f"WebSocket:  {WS_URL}\n\n"
        "Owner pubkey (hex):\n"
        f"{owner_pubkey}\n\n"
    )
    if owner_secret:
        body += (
            "Bootstrap owner secret key (back this up):\n"
            f"{owner_secret}\n\n"
        )
    else:
        body += "Bootstrap owner secret: not shown (owner-pubkey.override is set).\n\n"
    JOIN_TXT.write_text(body, encoding="utf-8")
    try:
        JOIN_TXT.chmod(0o600)
    except OSError:
        pass


def set_owner_pubkey(owner_pubkey: str) -> None:
    SECRETS.mkdir(parents=True, exist_ok=True)
    OVERRIDE.write_text(owner_pubkey + "\n", encoding="utf-8")
    OWNER_PUBKEY_FILE.write_text(owner_pubkey + "\n", encoding="utf-8")
    update_relay_env(owner_pubkey)
    write_join_txt(owner_pubkey, "")


def clear_owner_override() -> str | None:
    """Remove override and restore bootstrap owner pubkey from files."""
    if not OVERRIDE.is_file():
        return None
    OVERRIDE.unlink()
    pubkey = read_text(OWNER_PUBKEY_FILE)
    secret = read_text(OWNER_SECRET_FILE)
    if not pubkey:
        return None
    update_relay_env(pubkey)
    write_join_txt(pubkey, secret)
    return pubkey


def page(
    *,
    message: str | None = None,
    error: str | None = None,
    restart_needed: bool = False,
) -> str:
    owner = current_owner_pubkey()
    secret = bootstrap_secret()
    using_override = OVERRIDE.is_file()
    msg_html = (
        f'<div class="ok">{html.escape(message)}</div>' if message else ""
    )
    err_html = (
        f'<div class="err">{html.escape(error)}</div>' if error else ""
    )
    restart_html = ""
    if restart_needed:
        restart_html = (
            '<div class="callout"><strong>Restart required.</strong> '
            "In the Umbrel UI, stop and start <em>Buzz Relay</em> "
            "(or Restart) so the relay loads the new owner pubkey. "
            "Then Join a Community with the same Desktop identity.</div>"
        )
    secret_block = ""
    if secret:
        secret_block = (
            "<p class=\"warn\">Bootstrap owner secret (generated on first start). "
            "Only needed if you import this identity into Desktop instead of "
            "using your existing one. Treat it like a password.</p>"
            f"<code>{html.escape(secret)}</code>"
        )
    elif using_override:
        secret_block = (
            "<p><em>Bootstrap secret hidden — owner pubkey override is active "
            "(your Desktop identity).</em></p>"
        )

    clear_form = ""
    if using_override:
        clear_form = """
  <form method="post" action="clear-owner" class="card" onsubmit="return confirm('Remove the override and return to the generated bootstrap owner?');">
    <h2>Revert to bootstrap owner</h2>
    <p>Removes <code style="display:inline;padding:0.1rem 0.3rem">owner-pubkey.override</code> and restores the generated owner pubkey from first install.</p>
    <button type="submit">Clear override</button>
  </form>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Buzz Relay — Umbrel setup</title>
  <style>
    :root {{ color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; padding: 2rem; line-height: 1.45; max-width: 46rem; }}
    h1 {{ margin-top: 0; font-size: 1.6rem; }}
    .card {{ border: 1px solid #8884; border-radius: 12px; padding: 1rem 1.1rem; margin: 1rem 0; }}
    code {{ display: block; overflow-wrap: anywhere; word-break: break-all; padding: 0.75rem; border-radius: 8px; background: #8882; }}
    .warn {{ color: #b45309; }}
    .ok {{ border-left: 4px solid #15803d; background: #15803d14; padding: 0.85rem 1rem; margin: 1rem 0; border-radius: 0 8px 8px 0; }}
    .err {{ border-left: 4px solid #b91c1c; background: #b91c1c14; padding: 0.85rem 1rem; margin: 1rem 0; border-radius: 0 8px 8px 0; }}
    .callout {{ border-left: 4px solid #b45309; background: #b4530914; padding: 0.85rem 1rem; margin: 1rem 0; border-radius: 0 8px 8px 0; }}
    a {{ color: inherit; }}
    label {{ display: block; font-weight: 600; margin: 0.75rem 0 0.35rem; }}
    input[type=text] {{ width: 100%; box-sizing: border-box; padding: 0.65rem 0.75rem; border-radius: 8px; border: 1px solid #8886; font: inherit; }}
    button {{ margin-top: 0.85rem; padding: 0.55rem 1rem; border-radius: 8px; border: 1px solid #8886; font: inherit; cursor: pointer; }}
    ol.setup {{ padding-left: 1.2rem; }}
    ol.setup li {{ margin: 0.4rem 0; }}
  </style>
</head>
<body>
  <h1>Buzz Relay — join from here</h1>
  <p>Your self-hosted Buzz workspace is running on this Umbrel. Set the relay owner to your existing Buzz Desktop identity, then join with that same profile.</p>
  {msg_html}{err_html}{restart_html}

  <div class="callout">
    <strong>The empty “This relay is empty” page cannot invite you.</strong>
    “Open in Buzz” / “you need an invite” is expected until you are the owner below.
  </div>

  <div class="card">
    <h2>1. Join URL (Buzz Desktop)</h2>
    <p>Paste this WebSocket URL in <strong>Join a Community</strong> (scheme, host, and port must match):</p>
    <code>{html.escape(WS_URL)}</code>
    <p>On a pure LAN install use <code style="display:inline;padding:0.1rem 0.3rem">ws://</code>, not <code style="display:inline;padding:0.1rem 0.3rem">wss://</code>.</p>
  </div>

  <div class="card">
    <h2>2. Set relay owner (Desktop identity)</h2>
    <p>Same idea as <code style="display:inline;padding:0.1rem 0.3rem">RELAY_OWNER_PUBKEY</code> in the
    <a href="https://engineering.block.xyz/blog/run-your-own-buzz-relay">self-host guide</a>:
    paste your <strong>public</strong> key from Buzz Desktop → Settings → Identity.
    Never paste a secret/nsec here.</p>
    <p>Current owner public key (hex):</p>
    <code>{html.escape(owner) if owner else "(not set yet)"}</code>
    {secret_block}
    <form method="post" action="set-owner">
      <label for="pubkey">Owner public key (64-char hex or npub1…)</label>
      <input id="pubkey" name="pubkey" type="text" autocomplete="off" spellcheck="false"
             placeholder="Paste hex pubkey or npub1…" value="" />
      <button type="submit">Save owner pubkey</button>
    </form>
  </div>
  {clear_form}

  <div class="card">
    <h2>3. After saving</h2>
    <ol class="setup">
      <li>Restart Buzz Relay in Umbrel.</li>
      <li>Desktop → Join a Community → paste the Join URL above (same Desktop profile whose pubkey you saved).</li>
      <li>Web UI: <a href="/">{html.escape(HTTP_ORIGIN)}/</a></li>
    </ol>
  </div>

  <div class="card">
    <h2>Backups</h2>
    <ul>
      <li><code style="display:inline;padding:0.1rem 0.3rem">data/secrets/</code> — relay identity + owner keys</li>
      <li><code style="display:inline;padding:0.1rem 0.3rem">data/postgres/</code> — event database</li>
      <li><code style="display:inline;padding:0.1rem 0.3rem">data/minio/</code> — media</li>
      <li><code style="display:inline;padding:0.1rem 0.3rem">data/git/</code> — git volume</li>
    </ul>
  </div>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys_stderr = __import__("sys").stderr
        print(f"App: buzz-relay-setup - {self.address_string()} {fmt % args}", file=sys_stderr)

    def _send(self, code: int, body: str, content_type: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html", ""):
            self._send(200, page())
            return
        self._send(404, page(error="Not found."))

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path.strip("/")
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = urllib.parse.parse_qs(raw, keep_blank_values=True)

        if path == "set-owner":
            pubkey_raw = (form.get("pubkey") or [""])[0]
            parsed = parse_owner_input(pubkey_raw)
            if not parsed:
                self._send(
                    400,
                    page(
                        error="Invalid key. Paste a 64-character hex public key "
                        "or an npub1… from Buzz Desktop → Settings → Identity."
                    ),
                )
                return
            try:
                set_owner_pubkey(parsed)
            except OSError as exc:
                self._send(500, page(error=f"Failed to write secrets: {exc}"))
                return
            self._send(
                200,
                page(
                    message=f"Owner pubkey saved: {parsed}",
                    restart_needed=True,
                ),
            )
            return

        if path == "clear-owner":
            try:
                restored = clear_owner_override()
            except OSError as exc:
                self._send(500, page(error=f"Failed to clear override: {exc}"))
                return
            if not restored:
                self._send(
                    400,
                    page(error="No override to clear, or bootstrap owner pubkey is missing."),
                )
                return
            self._send(
                200,
                page(
                    message=f"Override cleared. Bootstrap owner restored: {restored}",
                    restart_needed=True,
                ),
            )
            return

        self._send(404, page(error="Not found."))


def main() -> None:
    host = os.environ.get("BUZZ_SETUP_BIND", "0.0.0.0")
    port = int(os.environ.get("BUZZ_SETUP_PORT", "8090"))
    SECRETS.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"App: buzz-relay-setup - listening on {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
