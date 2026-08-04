# Publishing Buzz Relay to Umbrel

## Path A — Community App Store (fastest)

This repository is already shaped like [getumbrel/umbrel-community-app-store](https://github.com/getumbrel/umbrel-community-app-store):

1. Create a **public** GitHub repository and push `main`.
2. On each Umbrel: App Store → ⋮ → **Community App Stores** → add the repo URL.
3. Install **Buzz Relay** from the **Buzz** store.

No Umbrel team review is required for community stores. You control updates by pushing to GitHub; Umbrel devices pull the store metadata on refresh.

### Update flow

1. Bump `buzz-relay/umbrel-app.yml` `version` and `releaseNotes`.
2. Pin new image digests in `docker-compose.yml` (tag + `@sha256:…`, multi-arch index digest).
3. Push to `main`. Users update from the Umbrel UI.

## Path B — Official Umbrel App Store

Follow [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps) (`README.md` + `AGENTS.md` + `.claude/skills/umbrel-package-app`).

### Checklist before opening a PR

- [ ] Copy `buzz-relay/` into a fork of `umbrel-apps` as a top-level app directory (id must stay `buzz-relay`).
- [ ] Omit community-store-only fields if reviewers request it; official packages usually omit `icon` URLs (assets are hosted separately). Keep `gallery: []` for the initial PR.
- [ ] Set `submission:` to the PR URL once opened.
- [ ] Confirm every image is public, pinned `tag@sha256`, and supports `linux/amd64` + `linux/arm64`.
- [ ] Confirm host `port: 3737` is still unused in `umbrel-apps` (re-check at PR time).
- [ ] Run the repo linter: `npm run lint:apps -- buzz-relay --check-images`.
- [ ] Test on real umbrelOS: install → open UI → confirm Join URL in logs/`data/setup/JOIN.txt` → join from Buzz Desktop → restart → data persists.
- [ ] Attach screenshots + logo source in the PR body (do not commit gallery binaries for official apps).
- [ ] Call out `PROXY_AUTH_ADD: "false"` (required for external clients) and the identity-key backup surface.

### App Store product bar

Official apps should open to a useful browser UI without SSH. This package opens the Buzz web UI at `/` and setup details at `/umbrel-setup/`.

## Version pinning policy

- Prefer `ghcr.io/block/buzz:<semver>@sha256:…` from `relay-v*` releases.
- Avoid moving tags (`:main`, `:latest`) in published store packages.
- When bumping, update `umbrel-app.yml` `version` to the same semver users recognize.
