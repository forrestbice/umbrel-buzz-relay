# Buzz Relay for Umbrel

Umbrel Community App Store package that runs a [Buzz](https://buzz.xyz) ([GitHub](https://github.com/block/buzz)) relay on umbrelOS — the same production shape described in Block’s [Run your own Buzz relay](https://engineering.block.xyz/blog/run-your-own-buzz-relay) guide (relay + Postgres 17 + Redis 7 + MinIO).

Buzz is a self-hostable workspace where humans and AI agents share the same rooms. It is a Nostr relay: messages, reactions, workflows, and git events are signed events in one log, on a relay you own. Self-hosting on Umbrel is for people who already run a home server and want **their** community — data, identity, and invite surface on hardware they control — instead of joining someone else’s hosted relay.

## Is this a fork of Buzz?

**No.** This repo does not fork or reimplement the relay. The app runs the official image `ghcr.io/block/buzz` plus the same Postgres / Redis / MinIO stack as Block’s self-host compose ([`deploy/compose/compose.yml`](https://github.com/block/buzz/tree/main/deploy/compose)). Same env contract (`RELAY_OWNER_PUBKEY`, `RELAY_URL`, S3 path-style, git volume, auto-migrate).

What this package adds is **Umbrel glue**, not a custom relay:

1. **First-run setup UI** (`/umbrel-setup/`) — paste your Desktop pubkey. Upstream expects you to edit `.env`. Umbrel’s App Store bar is: doable from the browser, no SSH.
2. **`pre-start` secret generation** — `buzz-admin generate-key` once, persist under `data/secrets/`. Upstream: fill `.env` by hand.
3. **nginx + `app_proxy`** — Umbrel requires `app_proxy`. We set `PROXY_AUTH_ADD: "false"` so Desktop can WebSocket in without Umbrel cookies, and we preserve `Host:port` so the community URL matches.
4. **Relay entrypoint** — re-exec `buzz-relay` when you hit Save, because the app must not (and cannot) talk to the host Docker socket.

Do not strip that glue to look more like “compose-only.” The setup page is why first-run works on Umbrel; without it, operators would edit env files over SSH, which Umbrel rejects for App Store apps.

Honest one-liner: *Umbrel packaging around the official Buzz relay image — not a fork.*

## What’s in this repo

| Path | Purpose |
|------|---------|
| `umbrel-app-store.yml` | Community App Store id/name (`buzz`) |
| `buzz-relay/` | Installable Umbrel app package |
| `docs/PUBLISHING.md` | Community store usage + official App Store PR checklist |

Pinned upstream image: `ghcr.io/block/buzz:0.2.0` (linux/amd64 + linux/arm64), digest-pinned in `docker-compose.yml` and `hooks/pre-start`.

Package version in `umbrel-app.yml` (currently **0.2.13**) is the **Umbrel packaging** semver. It is independent of the upstream relay image tag — bump the package when glue/setup changes; bump the image pin when adopting a newer `relay-v*` release from [block/buzz](https://github.com/block/buzz).

## Install on an Umbrel (Community App Store)

1. On umbrelOS: **App Store → three-dot menu → Community App Stores → Add** and paste `https://github.com/forrestbice/umbrel-buzz-relay`.
2. Install **Buzz Relay** from the Buzz community store.
3. Open the app (port **3737**). You should land on `/umbrel-setup/`. First boot can take a couple of minutes. If you instead see the empty Buzz “This relay is empty” page, open `/umbrel-setup/`.
4. On the setup page, paste your Buzz Desktop **public** key (Settings → Identity → 64-char hex, or `npub1…`) → **Save owner pubkey** (this also restarts the relay). This sets `RELAY_OWNER_PUBKEY` the same way as the upstream [self-host guide](https://engineering.block.xyz/blog/run-your-own-buzz-relay). To change owner later, paste a different pubkey and save again.
5. In Buzz Desktop → **Join a Community** (not “Open in Buzz”) → paste the `ws://…` URL from the setup page (e.g. `ws://umbrel.local:3737`).
6. Away from home: install Tailscale on Umbrel and your client. Keep the same Join URL — map `umbrel.local` to the Umbrel’s Tailscale IP in the client hosts file (details on `/umbrel-setup/`). Do not switch the Join URL to a MagicDNS name or raw `100.x` IP; Buzz binds the community to one host:port.

First install still generates a **bootstrap owner keypair** under `data/secrets/` so the relay has an owner before you choose one. After you save your Desktop pubkey, the setup page hides the bootstrap secret (it no longer matches the active owner). Prefer your normal Desktop identity as owner; only import the bootstrap secret if you intentionally want that generated identity.

### Optional: set owner via file instead of the setup form

Write your 64-character hex pubkey to:

```text
<data-dir>/secrets/owner-pubkey.override
```

Then restart the app (or use **Save owner pubkey** on `/umbrel-setup/`, which writes the same override and restarts the relay).

## Local layout of the app package

```text
buzz-relay/
  umbrel-app.yml            # Store listing + host port 3737
  docker-compose.yml        # relay, setup-api, postgres, redis, minio, minio-init, proxy
  exports.sh                # Derived DB/Redis/S3/HMAC secrets + public URLs
  hooks/pre-start           # Persist Nostr identity keys + install setup/entrypoint
  hooks/setup_server.py     # /umbrel-setup/ UI (copied into data/setup on start)
  hooks/relay_entrypoint.sh # In-process restart when setup UI requests it
  icon.svg / icon.png       # Community-store launcher icon
  data/{secrets,postgres,redis,minio,git,setup}/
```

`app_proxy` fronts nginx on port 8080 (`PROXY_AUTH_ADD=false`): `/umbrel-setup/` → `setup-api` (editable owner pubkey), `/` → Buzz relay (WebSocket upgrades). Nginx must forward the full `Host` header including port (`$http_host`) so Buzz can match the community bound to `umbrel.local:3737`.

## Publishing

See [`docs/PUBLISHING.md`](docs/PUBLISHING.md) for:

- Using this repo as a Community App Store
- Opening a PR against [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps) for the official store

Official App Store submission (in progress): https://github.com/getumbrel/umbrel-apps/pull/5993

## Sources

- Buzz product: https://buzz.xyz
- Buzz self-host guide: https://engineering.block.xyz/blog/run-your-own-buzz-relay
- Upstream compose: https://github.com/block/buzz/tree/main/deploy/compose
- Umbrel apps README / packaging skills: https://github.com/getumbrel/umbrel-apps
- Community store template: https://github.com/getumbrel/umbrel-community-app-store

## License

App packaging in this repository is provided under Apache-2.0 to match [block/buzz](https://github.com/block/buzz). Upstream Buzz remains copyright its authors.
