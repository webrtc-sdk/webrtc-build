#!/bin/bash

set -e

cd `dirname $0`
python3 run.py build apple_prefixed --commit "$1" --webrtc-fetch

export PATH="$PWD/_source/apple_prefixed/depot_tools:$PATH"
mkdir -p _package/apple_prefixed_stripped
# Strip the software VP9 and AV1 codecs and optimize for size (mirrors
# android_prefixed_stripped). H265 stays: it is VideoToolbox-backed on Apple
# (no size win) and rtc_use_h265=false does not build the ObjC factories.
STRIPPED_GN_ARGS="
      enable_libaom = false
      rtc_include_dav1d_in_internal_decoder_factory = false
      rtc_libvpx_build_vp9 = false
      optimize_for_size = true"
. apple/xcframework.sh "$2" _source/apple_prefixed/webrtc/src _package/apple_prefixed_stripped LiveKit "$STRIPPED_GN_ARGS" # prefix

# Same module name (drop-in), distinct artifact name.
mv "$OUT_DIR/LiveKitWebRTC.xcframework.zip" "$OUT_DIR/LiveKitWebRTC-stripped.xcframework.zip"
if [[ "$CI" == "true" ]]; then
  echo "framework_name=LiveKitWebRTC-stripped" >> "$GITHUB_OUTPUT"
fi
