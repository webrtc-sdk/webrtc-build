# Development

## Building locally

WebRTC can be built locally using `run.py`.

```
python3 run.py build <target>
```

Available targets can be found within run.py.

The `--help` flag can be passed to bring up the help reference like so: `python3 run.py --help` or `python3 run.py build --help`

When run, `libwebrtc.a` and relevant libraries will be created in the `_build` directory.

On the first build, WebRTC source and tools will be downloaded and patched according to the target, and built. Subsequent builds will be build only. The source code is not updated, and `gn gen` is not reran.

Specifically, when the build command is ran without any options, the following happens:

- If the source directory is missing, WebRTC is downloaded to the `_source` directory and patched.
- If the ninja files are missing, `gn gen` is run to generate them in the `_build` directory.
- `ninja` is run to build WebRTC.

If WebRTC is edited locally, the build command can be run again to rebuild WebRTC.

### --webrtc-fetch

The flag `--webrtc-fetch` can be used to refetch from the source repo.

```
python3 run.py build <target> --webrtc-fetch
```

WebRTC will reference the `VERSION` file's `WEBRTC_COMMIT` value and fetch from that ref, and patch on top.

**Warning**: This will wipe out any local changes.

Additionally, the flag `--webrtc-fetch-force` can be used to delete the source folder before fetching.

### --commit

The flag `--commit` can be used to specify the commit ref to fetch from, taking priority over the `VERSION` file's `WEBRTC_COMMIT value.

### --webrtc-gen

In the same fashion, the flag `--webrtc-gen` can be used to rerun gn gen.

```
python3 run.py build <target> --webrtc-gen
```

This will regenerate the ninja files.

Additionally, the flag `--webrtc-gen-force` can be used to delete the build directory before `gn gen`.

### --test

The `--test` flag will include rtc tests and run tests after building.

**Note**: this flag may include tests within the final build product, and should not be used for releases.

### iOS and Android builds

iOS's `WebRTC.xcframework`and Android's `webrtc.aar` are built during the build command. However, since they use separate tools, `gn gen` is always run before building.

If these products are not needed, `--webrtc-nobuild-ios-framework` and `--webrtc-nobuild-android-aar` flags can be passed to prevent building the respective products.

### Directory structure

By default:

- WebRTC source is placed under `_source`. 
- Build files are placed under `_build`.
- Targets are separated within the respective source and build directories like so: `_source/<target>/`, `_build/<target>/`
- Build configurations are further separated within the build folder like so: `_build/<target>/<configuration>`

For example:

```
/
|-- _source/
|   |-- ubuntu-20.04_x86_64/
|   |   |-- depot_tools/...
|   |   `-- webrtc/...
|   `-- android/
|       |-- depot_tools/...
|       `-- webrtc/...
`-- _build/
    |-- ubuntu-20.04_x86_64/
    |   |-- debug/
    |   |   `-- webrtc/...
    |   `-- release/
    |       `-- webrtc/...
    `-- android/
        |-- debug/
        |   `-- webrtc/...
        `-- release/
            `-- webrtc/...
```

The source and build directories can be modified with the following flags:

- `--source-dir`: Source directory
  - Default: `<run.py's directory>/_source/<target>` 
- `--webrtc-source-dir`: The specific directory where the WebRTC source will be located. Takes precedence over `--source-dir`.
  - Default: `<source-dir>/webrtc` 
- `--build-dir`: Build directory
  - Default: `<run.py's directory>/_build/<target>/<configuration>` 
- `--webrtc-build-dir`: The specific directory where build products will be located. Takes precedence over `--build-dir`.
  - Default: `<build-dir>/webrtc` 

Relative paths from the current directory can be passed in.

### Build Environment Requirements

Local builds can only be built in the required environments:

- Windows can only build the `windows` target.
- macOS can only build the `macos_x86_64`, `macos_arm64`, and `ios` targets.
- Ubuntu x86_64 can only build the other targets not specified above.
  - ARM libraries such as `android`, `raspberry-pi-os_armv*`, `ubuntu-*_armv8` can be built regardless of Ubuntu version.
  - `ubuntu-18.04_x86_64` requires Ubuntu 18.04.
  - `ubuntu-20.04_x86_64` requires Ubuntu 20.04.
  - Ubuntu must be on x86_64 to build.
- Non-Ubuntu Linux-based OSes cannot build.

## CI

Github Actions acts as the CI for the builds. Builds are run on all available targets. Artifacts are available after each build.

### Builds

Builds are configured run on each push and tag. A build can be manually initiated by going to the Actions tab, selecting the build workflow, and clicking `Run Workflow`. A `webrtc-sdk` commit ref can be specified in the commit hash field.

### Releasing

A release build workflow is run when a tag is pushed with the prefix `m`. A release is created with the name with the tag.
