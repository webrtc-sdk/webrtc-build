## Manual compilation steps for Windows

Before You Start
First, be sure to install the [prerequisite](https://webrtc.googlesource.com/src/+/main/docs/native-code/development/prerequisite-sw/index.md) software.
Recommend to use vs2019 Community Edition

### Prepare the compilation directory

```
mkdir webrtc-sdk-checkout
cd webrtc-sdk-checkout
```

### Create .gclient

```
solutions = [
  { 
    "name"        : 'src',
    "url"         : 'https://github.com/webrtc-sdk/webrtc.git',
    "deps_file"   : 'DEPS',
    "managed"     : False,
    "custom_deps" : {
    },
    "custom_vars": {},
  },
]
target_os  = ['win']
```

### Synchronize source code

```
gclient sync
```

### Generate ninja compilation directory

```
set DEPOT_TOOLS_WIN_TOOLCHAIN=0
set GYP_MSVS_VERSION=2019
set GYP_GENERATORS=ninja,msvs-ninja
set GYP_MSVS_OVERRIDE_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community
cd src
gn gen out/Windows-x64-debug --args="target_os=\"win\" target_cpu=\"x64\" is_component_build=false is_clang=true is_debug=true rtc_use_h264=true ffmpeg_branding=\"Chrome\" rtc_include_tests=false rtc_build_examples=false" --ide=vs2019
gn gen out/Windows-x64-release --args="target_os=\"win\" target_cpu=\"x64\" is_component_build=false is_clang=true is_debug=false rtc_use_h264=true ffmpeg_branding=\"Chrome\" rtc_include_tests=false rtc_build_examples=false" --ide=vs2019
```

### Compile
```
ninja -C out/Windows-x64-debug
ninja -C out/Windows-x64-release
```

### Compile steps for libwebrtc
Confirm that it is currently in the `src`.

```
git clone https://github.com/webrtc-sdk/libwebrtc
```

Modify BUILD.gn to add libwebrtc subdirectory
``` patch
diff --git a/BUILD.gn b/BUILD.gn
index bc51df7c07..c3573a8737 100644
--- a/BUILD.gn
+++ b/BUILD.gn
@@ -29,7 +29,7 @@ if (!build_with_chromium) {
   # 'ninja default' and then 'ninja all', the second build should do no work.
   group("default") {
     testonly = true
-    deps = [ ":webrtc" ]
+    deps = [ ":webrtc", "//libwebrtc:libwebrtc", ]
     if (rtc_build_examples) {
       deps += [ "examples" ]
     }
```


``` Regenerate the compilation directory
gn gen out/Windows-x64-debug --args="target_os=\"win\" target_cpu=\"x64\" is_component_build=false is_clang=true is_debug=true rtc_use_h264=true ffmpeg_branding=\"Chrome\" rtc_include_tests=false rtc_build_examples=false" --ide=vs2019
gn gen out/Windows-x64-release --args="target_os=\"win\" target_cpu=\"x64\" is_component_build=false is_clang=true is_debug=false rtc_use_h264=true ffmpeg_branding=\"Chrome\" rtc_include_tests=false rtc_build_examples=false" --ide=vs2019
```

Compile the `libwebrtc.dll`
```
ninja -C out/Windows-x64-debug libwebrtc
ninja -C out/Windows-x64-release libwebrtc
```
