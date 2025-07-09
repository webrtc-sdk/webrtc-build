#!/bin/bash

set -e
cd `dirname $0`
python3 run.py build apple_prefixed --commit "$1" --webrtc-fetch
# Temporary solution for a complete XCFramework build
export PATH="$PWD/_source/apple/depot_tools:$PATH"; printenv
. apple/build_xcframework_dynamic_livekit.sh release _source/apple_prefixed/webrtc/src _package/apple_prefixed LiveKit # prefix
