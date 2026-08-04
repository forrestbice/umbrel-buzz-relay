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
4. Open the app, then visit `/umbrel-setup/` for the WebSocket URL and bootstrap owner key.
5. In Buzz Desktop → **Join a Community** → paste the `ws://…` URL exactly.

### Optional: use your existing Buzz Desktop identity as owner

Before the first start (or on a fresh data dir), write your 64-character hex pubkey to:

```text
<data-dir>/secrets/owner-pubkey.override
```

Then start/restart the app. Get the pubkey from Buzz Desktop → Settings → Identity → Public key.

## Local layout of the app package

```text
buzz-relay/
  umbrel-app.yml       # Store listing + host port 3737
  docker-compose.yml   # proxy, web, postgres, redis, minio, minio-init
  exports.sh           # Derived DB/Redis/S3/HMAC secrets + public URLs
  hooks/pre-start      # Persist Nostr identity keys + render setup page
  data/proxy/nginx.conf
  data/{secrets,postgres,redis,minio,git,setup}/
```

`app_proxy` fronts nginx (`PROXY_AUTH_ADD=false` so Buzz Desktop can connect without Umbrel cookies). nginx serves `/umbrel-setup/` and reverse-proxies everything else (including WebSockets) to the Buzz relay.

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
