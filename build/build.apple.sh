#!/bin/bash

set -e

cd `dirname $0`
python3 run.py build apple --commit "$1" --webrtc-fetch

export PATH="$PWD/_source/apple/depot_tools:$PATH"
. apple/xcframework.sh.sh release _source/apple/webrtc/src _package/apple
