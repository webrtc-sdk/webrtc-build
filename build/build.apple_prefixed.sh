#!/bin/bash

set -e

cd `dirname $0`
python3 run.py build apple_prefixed --commit "$1" --webrtc-fetch

export PATH="$PWD/_source/apple_prefixed/depot_tools:$PATH"
mkdir -p _package/apple_prefixed
. apple/xcframework.sh "$2" _source/apple_prefixed/webrtc/src _package/apple_prefixed LiveKit # prefix
