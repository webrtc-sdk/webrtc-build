# Build command for all platforms

## iOS

python ./tools_webrtc/ios/build_ios_libs.py --build_config release --arch arm64 arm x64 x86 --bitcode --extra-gn-args \
      rtc_libvpx_build_vp9=true \
      rtc_include_tests=false \
      rtc_build_examples=false \
      rtc_use_h264=true \
      use_rtti=true \
      libcxx_abi_unstable=false \
      enable_dsyms=false

## macOS X64

```bash
gn gen out/macOS-x64 --args="
      target_os=\"mac\"
      target_cpu=\"x64\"
      mac_deployment_target=\"10.10\"
      enable_stripping=true
      enable_dsyms=false
      is_debug=false
      rtc_include_tests=false
      rtc_build_examples=false
      rtc_use_h264=false
      rtc_libvpx_build_vp9=true
      rtc_enable_symbol_export=true
      is_component_build=false
      use_rtti=true
      libcxx_abi_unstable=false"

ninja -C out/macOS-x64 mac_framework_bundle
```

## macOS arm64

```bash
gn gen out/macOS-arm64 --args="
      target_os=\"mac\"
      target_cpu=\"arm64\"
      mac_deployment_target=\"10.10\"
      enable_stripping=true
      enable_dsyms=false
      is_debug=false
      rtc_include_tests=false
      rtc_build_examples=false
      rtc_use_h264=false
      rtc_libvpx_build_vp9=true
      rtc_enable_symbol_export=true
      is_component_build=false
      use_rtti=true
      libcxx_abi_unstable=false"

ninja -C out/macOS-arm64 mac_framework_bundle
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
