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

Every output is written to `_package/` with `.sha256` and `.md5` files next to it.

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

1. Update [VERSION](VERSION) with the version number and the `webrtc-sdk/webrtc` commit.
2. Tag the release: `git tag m<version>` (the `m` prefix is required by CI).
3. Push the tag and wait for the `build` workflow to create the release.
