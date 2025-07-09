#!/bin/bash

set -e

cd `dirname $0`
python3 run.py build apple --commit "$1" --webrtc-fetch

export PATH="$PWD/_source/apple/depot_tools:$PATH"
. apple/xcframework.sh release "$PWD/_source/apple/webrtc/src" "$PWD/_package/apple"
