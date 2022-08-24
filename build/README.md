# WebRTC-Build

[![GitHub tag (latest SemVer)](https://img.shields.io/github/tag/webrtc-sdk/webrtc-build.svg)](https://github.com/webrtc-sdk/webrtc-build)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Actions Status](https://github.com/webrtc-sdk/webrtc-build/workflows/build/badge.svg)](https://github.com/webrtc-sdk/webrtc-build/actions)

## About webrtc-build

WebRTC builds for various platforms.

## Usage

See our [Releases](https://github.com/webrtc-sdk/webrtc-build/releases) to download the binaries.

We also publish the libraries for:

- [Android](https://github.com/webrtc-sdk/android), accessible through Maven/Gradle.
- [iOS/MacOS](https://github.com/webrtc-sdk/specs), accessible through Swift Package Manager/Cocoapods.

## Contents included for each platform

- WebRTC Library (webrtc.lib or libwebrtc.a)
- WebRTC include headers
- WebRTC version info (commit hash)

## Current supported platforms

- windows_x86_64
- windows_arm64
- macos_arm64
- macos_x86_64
- android_arm64
- ios_arm64

### Contributors

- melpon - *Original Author*
    - Android support
    - iOS support
    - CentOS 8 support
- tnoho - *Original Author*
    - AV1 for macOS support
    - H.265 for macOS support
- hakobera
    - Ubuntu 20.04 x86_64 support
    - macOS 11 arm64 support
- enm10k
    - iOS debug build
- soudegesu
    - ObjC headers for macOS
