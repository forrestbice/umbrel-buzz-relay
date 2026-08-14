# Buzz Relay for Umbrel

Umbrel Community App Store package that runs a [Buzz](https://buzz.xyz) relay on umbrelOS — the same production shape described in Block’s [Run your own Buzz relay](https://engineering.block.xyz/blog/run-your-own-buzz-relay) guide (relay + Postgres 17 + Redis 7 + MinIO).

## What’s in this repo

| Path | Purpose |
|------|---------|
| `umbrel-app-store.yml` | Community App Store id/name (`buzz`) |
| `buzz-relay/` | Installable Umbrel app package |
| `docs/PUBLISHING.md` | Community store usage + official App Store PR checklist |

Pinned upstream image: `ghcr.io/block/buzz:0.2.0` (linux/amd64 + linux/arm64).

## Install on an Umbrel (Community App Store)

1. Push this repository to GitHub (public).
2. On umbrelOS: **App Store → three-dot menu → Community App Stores → Add** and paste the GitHub repo URL.
3. Install **Buzz Relay** from the Buzz community store.
4. Open the app (port **3737**). You should land on `/umbrel-setup/`. First boot can take a couple of minutes. If you instead see the empty Buzz “This relay is empty” page, open `/umbrel-setup/`.
5. On the setup page, paste your Buzz Desktop **public** key (Settings → Identity → 64-char hex, or `npub1…`) → **Save owner pubkey** → **Restart relay**. This sets `RELAY_OWNER_PUBKEY` the same way as the upstream [self-host guide](https://engineering.block.xyz/blog/run-your-own-buzz-relay).
6. In Buzz Desktop → **Join a Community** (not “Open in Buzz”) → paste the `ws://…` URL from the setup page (e.g. `ws://umbrel.local:3737`).
7. Away from home: install Tailscale on Umbrel and your client. Keep the same Join URL — map `umbrel.local` to the Umbrel’s Tailscale IP in the client hosts file (details on `/umbrel-setup/`). Do not switch the Join URL to a MagicDNS name or raw `100.x` IP; Buzz binds the community to one host:port.

### Optional: set owner via file instead of the setup form

Write your 64-character hex pubkey to:

```text
<data-dir>/secrets/owner-pubkey.override
```

Then restart the app.

## Local layout of the app package

```text
buzz-relay/
  umbrel-app.yml       # Store listing + host port 3737
  docker-compose.yml   # relay, setup-api, postgres, redis, minio, minio-init, proxy
  exports.sh           # Derived DB/Redis/S3/HMAC secrets + public URLs
  hooks/pre-start      # Persist Nostr identity keys + install setup server
  hooks/setup_server.py # /umbrel-setup/ UI to set owner pubkey + restart
  hooks/relay_entrypoint.sh # In-process restart when setup UI requests it
  data/{secrets,postgres,redis,minio,git,setup}/
```

`app_proxy` fronts nginx on port 8080 (`PROXY_AUTH_ADD=false`): `/umbrel-setup/` → `setup-api` (editable owner pubkey), `/` → Buzz relay (WebSocket upgrades). Nginx must forward the full `Host` header including port (`$http_host`) so Buzz can match the community bound to `umbrel.local:3737`.

## Publishing

See [`docs/PUBLISHING.md`](docs/PUBLISHING.md) for:

- Using this repo as a Community App Store
- Opening a PR against [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps) for the official store

## Sources

- Buzz self-host guide: https://engineering.block.xyz/blog/run-your-own-buzz-relay
- Upstream compose: https://github.com/block/buzz/tree/main/deploy/compose
- Umbrel apps README / packaging skills: https://github.com/getumbrel/umbrel-apps
- Community store template: https://github.com/getumbrel/umbrel-community-app-store

## License

App packaging in this repository is provided under Apache-2.0 to match [block/buzz](https://github.com/block/buzz). Upstream Buzz remains copyright its authors.
