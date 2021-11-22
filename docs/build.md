# Build command for all platforms

## iOS

```bash
python ./tools_webrtc/ios/build_ios_libs.py --build_config release --arch device:arm64 simulator:arm64 simulator:x64 --extra-gn-args \ 
      rtc_libvpx_build_vp9=true \
      rtc_include_tests=false \
      rtc_build_examples=false \
      rtc_use_h264=false \
      use_rtti=true \
      libcxx_abi_unstable=false \
      enable_dsyms=false \
      is_debug=false
```

## iOS arm

```bash
gn gen out/ios-arm-device --args="
      target_os = \"ios\"
      ios_enable_code_signing = false
      use_xcode_clang = true
      is_component_build = false
      rtc_include_tests = false
      is_debug = false
      target_environment = \"device\"
      target_cpu = \"arm\"
      ios_deployment_target = \"10.0\"
      rtc_libvpx_build_vp9 = false
      enable_ios_bitcode = false
      use_goma = false
      rtc_enable_symbol_export = true
      rtc_libvpx_build_vp9 = true
      rtc_include_tests = false
      rtc_build_examples = false
      rtc_use_h264 = false
      use_rtti = true
      libcxx_abi_unstable = false
      enable_dsyms = false
      is_debug = false
      enable_dsyms = true
      enable_stripping = true"

ninja -C out/ios-arm-device ios_framework_bundle
```

## iOS arm64

```bash
gn gen out/ios-arm64-device --args="
      target_os = \"ios\"
      ios_enable_code_signing = false
      use_xcode_clang = true
      is_component_build = false
      rtc_include_tests = false
      is_debug = false
      target_environment = \"device\"
      target_cpu = \"arm64\"
      ios_deployment_target = \"10.0\"
      rtc_libvpx_build_vp9 = false
      enable_ios_bitcode = false
      use_goma = false
      rtc_enable_symbol_export = true
      rtc_libvpx_build_vp9 = true
      rtc_include_tests = false
      rtc_build_examples = false
      rtc_use_h264 = false
      use_rtti = true
      libcxx_abi_unstable = false
      enable_dsyms = false
      is_debug = false
      enable_dsyms = true
      enable_stripping = true"

ninja -C out/ios-arm64-device ios_framework_bundle
```

## iOS x64 simulator

```bash
gn gen out/ios-x64-simulator --args="
      target_os = \"ios\"
      ios_enable_code_signing = false
      use_xcode_clang = true
      is_component_build = false
      rtc_include_tests = false
      is_debug = false
      target_environment = \"simulator\"
      target_cpu = \"x64\"
      ios_deployment_target = \"12.0\"
      rtc_libvpx_build_vp9 = false
      enable_ios_bitcode = false
      use_goma = false
      rtc_enable_symbol_export = true
      rtc_libvpx_build_vp9 = true
      rtc_include_tests = false
      rtc_build_examples = false
      rtc_use_h264 = false
      use_rtti = true
      libcxx_abi_unstable = false
      enable_dsyms = false
      is_debug = false
      enable_dsyms = true
      enable_stripping = true"

ninja -C out/ios-x64-simulator ios_framework_bundle
```

## iOS arm64 simulator

```bash
gn gen out/ios-arm64-simulator --args="
      target_os = \"ios\"
      ios_enable_code_signing = false
      use_xcode_clang = true
      is_component_build = false
      rtc_include_tests = false
      is_debug = false
      target_environment = \"simulator\"
      target_cpu = \"arm64\"
      ios_deployment_target = \"12.0\"
      rtc_libvpx_build_vp9 = false
      enable_ios_bitcode = false
      use_goma = false
      rtc_enable_symbol_export = true
      rtc_libvpx_build_vp9 = true
      rtc_include_tests = false
      rtc_build_examples = false
      rtc_use_h264 = false
      use_rtti = true
      libcxx_abi_unstable = false
      enable_dsyms = false
      is_debug = false
      enable_dsyms = true
      enable_stripping = true"

ninja -C out/ios-arm64-simulator ios_framework_bundle
```

## macOS X64

```bash
gn gen out/macOS-x64 --args="
      target_os=\"mac\"
      target_cpu=\"x64\"
      mac_deployment_target=\"10.11\"
      is_component_build = false
      rtc_include_tests = false
      is_debug = false
      target_cpu = \"x64\"
      rtc_libvpx_build_vp9 = false
      use_goma = false
      rtc_enable_symbol_export = true
      rtc_libvpx_build_vp9 = true
      rtc_include_tests = false
      rtc_build_examples = false
      rtc_use_h264 = false
      use_rtti = true
      libcxx_abi_unstable = false
      enable_dsyms = false
      is_debug = false
      enable_dsyms = true
      enable_stripping = true"

ninja -C out/macOS-x64 mac_framework_bundle
```

## macOS arm64

```bash
gn gen out/macOS-arm64 --args="
      target_os=\"mac\"
      target_cpu=\"x64\"
      mac_deployment_target=\"10.11\"
      is_component_build = false
      rtc_include_tests = false
      is_debug = false
      target_cpu = \"arm64\"
      rtc_libvpx_build_vp9 = false
      use_goma = false
      rtc_enable_symbol_export = true
      rtc_libvpx_build_vp9 = true
      rtc_include_tests = false
      rtc_build_examples = false
      rtc_use_h264 = false
      use_rtti = true
      libcxx_abi_unstable = false
      enable_dsyms = false
      is_debug = false
      enable_dsyms = true
      enable_stripping = true"

ninja -C out/macOS-arm64 mac_framework_bundle
```

## Create xcframework

Merge the arm64 and x64 libraries of macOS.

```bash
mkdir -p out/mac-x64-arm64-lib
cp -R out/macOS-x64/WebRTC.framework out/mac-x64-arm64-lib/WebRTC.framework
lipo -create -output out/mac-x64-arm64-lib/WebRTC.framework/WebRTC out/macOS-x64/WebRTC.framework/WebRTC out/macOS-arm64/WebRTC.framework/WebRTC
```

Merge the arm64 and arm libraries of iOS.

```bash
mkdir -p out/ios-device-arm-arm64-lib
cp -R out/ios-arm64-device/WebRTC.framework out/ios-device-arm-arm64-lib/WebRTC.framework
lipo -create -output out/ios-device-arm-arm64-lib/WebRTC.framework/WebRTC out/ios-arm-device/WebRTC.framework/WebRTC out/ios-arm64-device/WebRTC.framework/WebRTC
```

Merge the arm64 and x64 libraries of iOS simulator.

```bash
mkdir -p out/ios-simulator-arm64-x64-lib
cp -R out/ios-arm64-simulator/WebRTC.framework out/ios-simulator-arm64-x64-lib/WebRTC.framework
lipo -create -output out/ios-simulator-arm64-x64-lib/WebRTC.framework/WebRTC out/ios-arm64-simulator/WebRTC.framework/WebRTC out/ios-x64-simulator/WebRTC.framework/WebRTC
```

Create xcframework

```bash
xcodebuild -create-xcframework \
        -framework out/ios-device-arm-arm64-lib/WebRTC.framework \
        -framework out/ios-simulator-arm64-x64-lib/WebRTC.framework \
        -framework out/mac-x64-arm64-lib/WebRTC.framework \
        -output out/WebRTC.xcframework
cp LICENSE out/WebRTC.xcframework/
```

Fix symbolic links issue for macOS

```
cd out/WebRTC.xcframework/macos-arm64_x86_64/WebRTC.framework/
mv WebRTC Versions/A/WebRTC
ln -s Versions/Current/WebRTC WebRTC
```

Create a release zip file

```
cd out/
zip --symlinks -9 -r WebRTC.xcframework.zip WebRTC.xcframework
# hash
shasum -a 256 WebRTC.xcframework.zip
```

## Android

```bash
vpython ./tools_webrtc/android/build_aar.py --build-dir webrtc_android --output ./webrtc_android/libwebrtc.aar --arch armeabi-v7a arm64-v8a x86_64 x86 --extra-gn-args 'is_java_debug=false rtc_include_tests=false rtc_use_h264=false is_component_build=false use_rtti=true rtc_build_examples=false treat_warnings_as_errors=false'
```

## Linux

```bash
gn gen out/Linux-x64 --args="target_os=\"linux\" target_cpu=\"x64\" is_debug=false rtc_include_tests=false rtc_use_h264=false is_component_build=false use_rtti=true use_custom_libcxx=false rtc_enable_protobuf=false"
gn gen out/Linux-x86 --args="target_os=\"linux\" target_cpu=\"x86\" is_debug=false rtc_include_tests=false rtc_use_h264=false is_component_build=false use_rtti=true use_custom_libcxx=false rtc_enable_protobuf=false"
```

## Windows

```console
set DEPOT_TOOLS_WIN_TOOLCHAIN=0
gn gen out/Windows-x64 --args="target_os=\"win\" target_cpu=\"x64\" is_debug=false rtc_include_tests=false rtc_use_h264=false is_component_build=false use_rtti=true use_custom_libcxx=false rtc_enable_protobuf=false"
gn gen out/Windows-x86 --args="target_os=\"win\" target_cpu=\"x86\" is_debug=false rtc_include_tests=false rtc_use_h264=false is_component_build=false use_rtti=true use_custom_libcxx=false rtc_enable_protobuf=false"
```
