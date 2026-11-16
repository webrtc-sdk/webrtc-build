# webrtc-build

Build scripts and CI for [webrtc-sdk/webrtc](https://github.com/webrtc-sdk/webrtc) binaries.

## Outputs

| Target | Host | Output |
|---|---|---|
| `apple` | macOS | `WebRTC.xcframework.zip` |
| `apple_prefixed` | macOS | `LiveKitWebRTC.xcframework.zip` |
| `apple_prefixed_stripped` | macOS | `LiveKitWebRTC-stripped.xcframework.zip` |
| `android` | Linux | `libwebrtc.aar` |
| `android_prefixed` | Linux | `libwebrtc_prefixed.aar` |
| `android_prefixed_stripped` | Linux | `libwebrtc_prefixed_stripped.aar` |
| `libwebrtc_linux_{x64,arm64}` | Linux | `libwebrtc-linux-<arch>-<config>.zip` |
| `libwebrtc_win_{x64,arm64}` | Windows | `libwebrtc-win-<arch>-<config>.zip` |

Every output is written to `_package/` with a `<name>.shasum` file next to it (`shasum -a 256` format).

## Building

```sh
# All targets passed together share one checkout and one gclient sync.
python3 scripts/build.py build apple apple_prefixed apple_prefixed_stripped
python3 scripts/build.py build android android_prefixed android_prefixed_stripped

# libwebrtc wrapper builds need a webrtc-sdk/libwebrtc checkout.
python3 scripts/build.py build libwebrtc_linux_x64 --libwebrtc-dir ../libwebrtc

# Build and run rtc_unittests (debug) for the host platform.
python3 scripts/build.py test
```

Options:

- `--commit <sha|tag|HEAD>`: the webrtc commit to build. Defaults to `WEBRTC_COMMIT` in [VERSION](VERSION).
- `--debug`: debug build.
- `--no-sync`: rebuild the existing checkout without fetching (local iteration).
- `--work-dir <dir>`: where `_source/` and `_package/` go (the default is the repository root).
- `--jobs <n>`: ninja parallelism.
- `--keep-out`: keep build outputs and the patched tree for incremental local builds. By default every build output under `src/out` is deleted once copied to `_package`, and the tree is reset on exit, so cached checkouts only hold sources.
- `--fresh`: delete the checkout and sync from scratch.
- `--sync-for <targets>`: also sync the dependencies of these targets (keeps shared caches identical across jobs).

Set `GIT_CACHE_PATH` to reuse a gclient git cache across runs.

Test resources (`src/resources`, large raw audio/video downloaded from Google Storage) are only needed by `test`, which downloads and verifies them on every run. They are removed together with build outputs, so source caches never contain them.

Patches applied per target live in [scripts/patches](scripts/patches).

## Releasing

Releases are driven by pull requests:

1. Run the **release-pr** workflow with the new version (e.g. `150.7871.08`). It opens `release/<version>` with [VERSION](VERSION) pointing at the newest commit of the webrtc default branch (or a given commit), and the PR body lists the webrtc commits since the previous release. The PR's `build` checks produce every package.
2. **release-pr-refresh** keeps the PR current: on each webrtc push (`repository_dispatch: webrtc-updated`) and hourly it bumps `WEBRTC_COMMIT` to the newest commit and rewrites the commit list. Add the `pin` label to freeze the commit.
3. Merge the PR. **release** reuses the packages of the PR's last successful build (or rebuilds), creates the `m<version>` release with the commit list, every package with its `.shasum` file, publishes LiveKitWebRTC, and notifies downstream repositories (`repository_dispatch: webrtc-release`).

Configuration:

| Name | Kind | Purpose |
|---|---|---|
| `RELEASE_APP_CLIENT_ID` | variable | Client ID of the release GitHub App. Its tokens push and open the release PRs, so the PRs trigger `build` (without the App: `GITHUB_TOKEN`, which does not), and send `repository_dispatch` to the downstream repositories (skipped without the App). |
| `RELEASE_APP_PRIVATE_KEY` | secret | Private key (`.pem`) of the release GitHub App. |
| `XCFRAMEWORK_PAT` | secret | Publishes LiveKitWebRTC to livekit/webrtc-xcframework. |
| `WEBRTC_REPO` | variable | webrtc repository (`owner/name`), default `webrtc-sdk/webrtc`. |
| `DOWNSTREAM_REPOS` | variable | Space-separated repositories to notify, default `webrtc-sdk/Specs webrtc-sdk/android`. They must share one owner, with the App installed on them. |
