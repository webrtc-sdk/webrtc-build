#!/usr/bin/env python3
"""Build webrtc-sdk/webrtc binaries.

One checkout of webrtc-sdk/webrtc (plus its gclient dependencies) is shared by
every target built on the same host. Targets passed in a single invocation are
synced once and then built one after another; the tree is reset and re-patched
between targets only when their patch sets differ.

Usage:
    python3 scripts/build.py build apple apple_prefixed apple_prefixed_stripped
    python3 scripts/build.py build android android_prefixed android_prefixed_stripped
    python3 scripts/build.py build libwebrtc_linux_x64 --libwebrtc-dir ../libwebrtc
    python3 scripts/build.py build libwebrtc_win_arm64 --work-dir C:\\wb --libwebrtc-dir ..\\libwebrtc
    python3 scripts/build.py test
    python3 scripts/build.py sync android libwebrtc_linux_x64   # checkout only

The webrtc commit defaults to WEBRTC_COMMIT in ./VERSION (repository root).

Layout (relative to --work-dir, default: the repository root):
    _source/depot_tools/        depot_tools checkout
    _source/webrtc/.gclient     gclient solution (target_os grows as needed)
    _source/webrtc/src/         webrtc-sdk/webrtc checkout
    _source/webrtc/src/out/<target>-<config>/   build output (removed after use)
    _package/                   release files (+ .sha256 / .md5 next to each)

Build outputs are deleted once their files are in _package, and the tree is
reset (patches undone, generated files removed) when the script exits, so a
cached _source only ever holds pristine sources. --keep-out keeps them for
local incremental builds.

Set GIT_CACHE_PATH to share a gclient git cache between runs.

Derived from shiguredo/webrtc-build (Apache-2.0, see NOTICE) and the
libwebrtc build scripts from webrtc-sdk/libwebrtc.
"""

import argparse
import hashlib
import json
import logging
import os
import platform
import shutil
import stat
import subprocess
import sys
import zipfile
from typing import Dict, List, NamedTuple, Optional

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
PATCH_DIR = os.path.join(SCRIPT_DIR, 'patches')

WEBRTC_REPO = 'https://github.com/webrtc-sdk/webrtc.git'
DEPOT_TOOLS_REPO = 'https://chromium.googlesource.com/chromium/tools/depot_tools.git'

HOST = platform.system()  # 'Darwin' | 'Linux' | 'Windows'


# ---------------------------------------------------------------------------
# Target definitions
# ---------------------------------------------------------------------------

class Target(NamedTuple):
    kind: str            # 'apple' | 'android' | 'libwebrtc'
    host: str            # platform.system() value the target must be built on
    target_os: List[str]  # gclient target_os entries the target needs
    patches: List[str]   # patches from scripts/patches, applied with -p1 in src
    extra_gn_args: List[str] = []
    package: str = ''    # file name written to the package dir
    prefix: str = ''     # apple: framework name prefix
    os: str = ''         # libwebrtc: 'linux' | 'win'
    cpu: str = ''        # libwebrtc: 'x64' | 'arm64'


# Apple targets only need the host default (mac): target_os 'ios' would also
# check out chromium/src/ios, which the framework builds do not use.

# Software VP9/AV1 removed and optimized for size. H265 stays on Apple: it is
# VideoToolbox-backed there (no size win) and rtc_use_h265=false does not build
# the ObjC factories.
APPLE_STRIPPED_GN_ARGS = [
    'enable_libaom=false',
    'rtc_include_dav1d_in_internal_decoder_factory=false',
    'rtc_libvpx_build_vp9=false',
    'optimize_for_size=true',
]

ANDROID_STRIPPED_GN_ARGS = [
    'enable_libaom=false',
    'rtc_include_dav1d_in_internal_decoder_factory=false',
    'rtc_use_h265=false',
    'rtc_libvpx_build_vp9=false',
    'optimize_for_size=true',
]

ANDROID_PATCHES = [
    'add_license_dav1d.patch',
    'android_webrtc_version.patch',
    'fix_mocks.patch',
]

# Patches live in the libwebrtc checkout (<libwebrtc-dir>/patches) and are
# tied to the WebRTC milestone; update together with libwebrtc.
LIBWEBRTC_PATCHES = {
    'linux': [
        'custom_audio_source_m150.patch',
        'add_libwebrtc_build_target.patch',
        'fix_desktop_capture_compile.patch',
    ],
    'win': [
        'custom_audio_source_m150.patch',
        'add_libwebrtc_build_target.patch',
        'allow_176k4_192k_shared_mode_formats.patch',
    ],
}

TARGETS: Dict[str, Target] = {
    'apple': Target(
        kind='apple', host='Darwin', target_os=['mac'],
        patches=[],
        package='WebRTC.xcframework.zip'),
    'apple_prefixed': Target(
        kind='apple', host='Darwin', target_os=['mac'],
        patches=['apple_prefix.patch'], prefix='LiveKit',
        package='LiveKitWebRTC.xcframework.zip'),
    # Same module name as apple_prefixed (drop-in), distinct file name.
    'apple_prefixed_stripped': Target(
        kind='apple', host='Darwin', target_os=['mac'],
        patches=['apple_prefix.patch'], prefix='LiveKit',
        extra_gn_args=APPLE_STRIPPED_GN_ARGS,
        package='LiveKitWebRTC-stripped.xcframework.zip'),
    'android': Target(
        kind='android', host='Linux', target_os=['android'],
        patches=ANDROID_PATCHES,
        package='libwebrtc.aar'),
    'android_prefixed': Target(
        kind='android', host='Linux', target_os=['android'],
        patches=[*ANDROID_PATCHES, 'jni_prefix.patch'],
        package='libwebrtc_prefixed.aar'),
    'android_prefixed_stripped': Target(
        kind='android', host='Linux', target_os=['android'],
        patches=[*ANDROID_PATCHES, 'jni_prefix.patch'],
        extra_gn_args=ANDROID_STRIPPED_GN_ARGS,
        package='libwebrtc_prefixed_stripped.aar'),
}
for _cpu in ('x64', 'arm64'):
    TARGETS[f'libwebrtc_linux_{_cpu}'] = Target(
        kind='libwebrtc', host='Linux', target_os=['linux'],
        patches=[], os='linux', cpu=_cpu)
    TARGETS[f'libwebrtc_win_{_cpu}'] = Target(
        kind='libwebrtc', host='Windows', target_os=['win'],
        patches=[], os='win', cpu=_cpu)

# Shared by the android and unit test builds.
COMMON_GN_ARGS = [
    'rtc_use_h264=false',
    'is_component_build=false',
    'rtc_build_examples=false',
    'use_rtti=true',
    'rtc_build_tools=false',
    'rtc_enable_protobuf=false',
]

ANDROID_ARCHS = ['armeabi-v7a', 'arm64-v8a', 'x86_64', 'x86']

TEST_PATCHES = [
    'add_license_dav1d.patch',
    'fix_mocks.patch',
    'fix_build_for_validate_test_registration.patch',
]

TEST_GN_ARGS = {
    'Linux': [
        'target_os="linux"',
        'rtc_use_pipewire=false',
    ],
    'Darwin': [
        'target_os="mac"',
        'target_cpu="arm64"',
        'enable_stripping=true',
        'enable_dsyms=true',
        'rtc_libvpx_build_vp9=true',
        'rtc_enable_symbol_export=true',
        'rtc_enable_objc_symbol_export=false',
        # The clang module build of libc++ needs the include config that
        # use_custom_libcxx=false removes ("unknown type name 'size_t'").
        'use_custom_libcxx=true',
        'treat_warnings_as_errors=false',
        'clang_use_chrome_plugins=false',
        'use_lld=false',
    ],
    'Windows': [
        'target_os="win"',
        'target_cpu="x64"',
        'is_clang=true',
        'symbol_level=1',
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(args: List[str], cwd: Optional[str] = None, check: bool = True,
        capture: bool = False) -> subprocess.CompletedProcess:
    exe = shutil.which(args[0]) or args[0]
    logging.info('+ %s%s', ' '.join(args), f'  (cwd={cwd})' if cwd else '')
    return subprocess.run(
        [exe, *args[1:]], cwd=cwd, check=check,
        stdout=subprocess.PIPE if capture else None,
        encoding='utf-8' if capture else None)


def capture(args: List[str], cwd: Optional[str] = None) -> str:
    return run(args, cwd=cwd, capture=True).stdout.strip()


def _on_rm_error(func, path, _exc_info):
    # git objects are read-only on Windows.
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rm_rf(path: str):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path, onerror=_on_rm_error)


def mkdir_p(path: str):
    os.makedirs(path, exist_ok=True)


def read_version_file(path: str) -> Dict[str, str]:
    result = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip().strip('"')
    return result


def add_path(path: str):
    os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')


def write_checksums(path: str):
    """Write <path>.sha256 and <path>.md5 in `shasum` format."""
    for algo in ('sha256', 'md5'):
        h = hashlib.new(algo)
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        with open(f'{path}.{algo}', 'w', newline='\n') as f:
            f.write(f'{h.hexdigest()}  {os.path.basename(path)}\n')
        logging.info('%s %s: %s', algo, os.path.basename(path), h.hexdigest())


def zip_dir(src_dir: str, zip_path: str):
    """Zip src_dir, keeping its basename as the top-level directory."""
    rm_rf(zip_path)
    base = os.path.dirname(src_dir)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for name in files:
                full = os.path.join(root, name)
                zf.write(full, os.path.relpath(full, base))


def gn_args_str(args: List[str]) -> str:
    return ' '.join(args)


# ---------------------------------------------------------------------------
# Source checkout
# ---------------------------------------------------------------------------

class Context:
    def __init__(self, args):
        self.work_dir = os.path.abspath(args.work_dir)
        self.source_dir = os.path.join(self.work_dir, '_source')
        self.gclient_dir = os.path.join(self.source_dir, 'webrtc')
        self.src_dir = os.path.join(self.gclient_dir, 'src')
        self.depot_tools_dir = os.path.join(self.source_dir, 'depot_tools')
        self.package_dir = os.path.abspath(
            args.package_dir or os.path.join(self.work_dir, '_package'))
        # Unit tests always build debug.
        self.debug = getattr(args, 'debug', False) or args.op == 'test'
        self.config = 'debug' if self.debug else 'release'
        self.jobs = args.jobs
        self.libwebrtc_dir = os.path.abspath(
            args.libwebrtc_dir) if getattr(args, 'libwebrtc_dir', None) else None

        self.version = read_version_file(os.path.join(ROOT_DIR, 'VERSION'))
        self.commit = args.commit or self.version['WEBRTC_COMMIT']
        # Patch set currently applied to the tree; None means unknown/dirty.
        self.applied: Optional[tuple] = None

    def out_dir(self, name: str) -> str:
        # build_aar.py requires the build dir to be under src; src/out is
        # ignored by the webrtc checkout.
        return os.path.join(self.src_dir, 'out', f'{name}-{self.config}')


def setup_environment(ctx: Context):
    if not os.path.isdir(ctx.depot_tools_dir):
        mkdir_p(ctx.source_dir)
        run(['git', 'clone', '--depth', '1', DEPOT_TOOLS_REPO, ctx.depot_tools_dir])
    add_path(ctx.depot_tools_dir)
    if HOST == 'Windows':
        os.environ['DEPOT_TOOLS_WIN_TOOLCHAIN'] = '0'
        os.environ['GYP_MSVS_VERSION'] = '2022'
        os.environ['PYTHONIOENCODING'] = 'utf-8'


def read_gclient_target_os(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    scope: Dict = {}
    with open(path) as f:
        exec(f.read(), {}, scope)  # .gclient is a Python file we wrote.
    return list(scope.get('target_os', []))


def merged_target_os(ctx: Context, target_os: List[str]) -> List[str]:
    # Only grow target_os: removing an OS would make `gclient sync -D` delete
    # its dependencies from a cached checkout.
    path = os.path.join(ctx.gclient_dir, '.gclient')
    return sorted(set(read_gclient_target_os(path)) | set(target_os))


def write_gclient(ctx: Context, merged: List[str]):
    path = os.path.join(ctx.gclient_dir, '.gclient')
    content = (
        'solutions = [\n'
        '  {\n'
        '    "name": "src",\n'
        f'    "url": "{WEBRTC_REPO}",\n'
        '    "deps_file": "DEPS",\n'
        '    "managed": False,\n'
        '    "custom_deps": {},\n'
        '  },\n'
        ']\n'
        f'target_os = {merged!r}\n'
    )
    with open(path, 'w', newline='\n') as f:
        f.write(content)
    logging.info('.gclient target_os = %s', merged)


def stamp_path(ctx: Context) -> str:
    return os.path.join(ctx.gclient_dir, '.sync_stamp.json')


def read_stamp(ctx: Context) -> Dict:
    try:
        with open(stamp_path(ctx)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def is_full_sha(ref: str) -> bool:
    return len(ref) == 40 and all(c in '0123456789abcdef' for c in ref.lower())


def sync(ctx: Context, target_os: List[str]) -> bool:
    """Check out ctx.commit with its dependencies.

    Returns False when the checkout already matches (same commit and
    target_os as the last successful sync) and nothing was changed, so a
    persisted source cache is only updated when the commit changes.
    """
    mkdir_p(ctx.gclient_dir)
    if HOST == 'Windows':
        run(['git', 'config', '--global', 'core.longpaths', 'true'])
    merged = merged_target_os(ctx, target_os)
    src = ctx.src_dir
    stamp = read_stamp(ctx)
    have_src = os.path.isdir(os.path.join(src, '.git'))

    def up_to_date(sha: str) -> bool:
        return (have_src and stamp.get('commit') == sha
                and stamp.get('target_os') == merged)

    # Full SHA: decide without touching the network.
    if is_full_sha(ctx.commit) and up_to_date(ctx.commit.lower()):
        logging.info('checkout already synced at %s %s; skipping sync', ctx.commit, merged)
        # A previous build may have left patches applied.
        ctx.applied = None
        return False

    if not have_src:
        rm_rf(src)
        run(['git', 'clone', WEBRTC_REPO, src])

    run(['git', 'fetch', 'origin'], cwd=src)
    if ctx.commit == 'HEAD':
        run(['git', 'remote', 'set-head', 'origin', '-a'], cwd=src)
        ref = 'origin/HEAD'
    else:
        ref = ctx.commit
        exists = run(['git', 'cat-file', '-e', f'{ref}^{{commit}}'],
                     cwd=src, check=False).returncode == 0
        if not exists:
            # Commits not reachable from a branch (e.g. PR heads).
            run(['git', 'fetch', 'origin', ref], cwd=src)
    sha = capture(['git', 'rev-parse', f'{ref}^{{commit}}'], cwd=src)
    if up_to_date(sha):
        logging.info('checkout already synced at %s %s; skipping sync', sha, merged)
        ctx.applied = None
        return False

    # Fast path: dependency revisions are pinned in DEPS, so when DEPS (and
    # target_os) did not change since the last complete sync, the deps are
    # already right and only src needs the new commit. Hooks still run:
    # lastchange and landmines depend on the src revision; the download hooks
    # are no-ops when their files are current.
    old = stamp.get('commit')
    deps_unchanged = (
        have_src and old and stamp.get('target_os') == merged
        and run(['git', 'cat-file', '-e', f'{old}^{{commit}}'],
                cwd=src, check=False).returncode == 0
        and run(['git', 'diff', '--quiet', old, sha, '--', 'DEPS'],
                cwd=src, check=False).returncode == 0)

    # Invalidate first so an interrupted sync is never taken as complete.
    rm_rf(stamp_path(ctx))
    write_gclient(ctx, merged)
    run(['git', 'checkout', '-f', sha], cwd=src)
    run(['git', 'clean', '-df'], cwd=src)
    if deps_unchanged:
        logging.info('DEPS unchanged since %s; fast sync (src checkout + runhooks)', old)
        run(['gclient', 'runhooks'], cwd=ctx.gclient_dir)
        # gclient did not reset the dependency repos; reset_tree() undoes any
        # patches a killed job may have left in third_party.
        ctx.applied = None
    else:
        run(['gclient', 'sync', '-D', '--force', '--reset',
             '--with_branch_heads', '--jobs=8'], cwd=ctx.gclient_dir)
        ctx.applied = ()
    with open(stamp_path(ctx), 'w') as f:
        json.dump({'commit': sha, 'target_os': merged}, f)
    logging.info('webrtc synced at %s', sha)
    return True


def reset_tree(ctx: Context):
    """Undo patches and generated files from a previous target."""
    run(['git', 'reset', '--hard', '--quiet'], cwd=ctx.src_dir)
    # jni_prefix.patch touches third_party/jni_zero (separate repo). Do not
    # `git clean` there: dependency checkouts live under it.
    third_party = os.path.join(ctx.src_dir, 'third_party')
    if os.path.isdir(os.path.join(third_party, '.git')):
        run(['git', 'reset', '--hard', '--quiet'], cwd=third_party)
    rm_rf(os.path.join(ctx.src_dir, 'libwebrtc'))
    rm_rf(android_version_java_path(ctx))
    ctx.applied = ()


def apply_patches(ctx: Context, patches: List[str], key: tuple):
    """Bring the tree to the given patch set, resetting only when needed."""
    if ctx.applied == key:
        return
    if ctx.applied != ():
        reset_tree(ctx)
    for patch in patches:
        path = os.path.join(PATCH_DIR, patch)
        if HOST == 'Windows':
            run(['git', 'apply', '-p1', '--ignore-space-change',
                 '--ignore-whitespace', '--whitespace=nowarn', path], cwd=ctx.src_dir)
        else:
            with open(path) as stdin:
                logging.info('+ patch -p1 < %s', path)
                subprocess.run(['patch', '-p1'], stdin=stdin, cwd=ctx.src_dir, check=True)
    ctx.applied = key


def gn_gen(ctx: Context, out_dir: str, args: List[str]):
    run(['gn', 'gen', out_dir, '--args=' + gn_args_str(args)], cwd=ctx.src_dir)


def ninja(ctx: Context, out_dir: str, targets: List[str]):
    jobs = ['-j', str(ctx.jobs)] if ctx.jobs else []
    run(['autoninja', '-C', out_dir, *jobs, *targets], cwd=ctx.src_dir)


def publish(ctx: Context, path: str, name: str) -> str:
    mkdir_p(ctx.package_dir)
    dst = os.path.join(ctx.package_dir, name)
    rm_rf(dst)
    shutil.copy2(path, dst)
    write_checksums(dst)
    return dst


# ---------------------------------------------------------------------------
# Apple: xcframework for iOS / macOS / Catalyst / tvOS / visionOS
# ---------------------------------------------------------------------------

APPLE_PLATFORMS = [
    ('iOS-arm64-device', ['target_os="ios"', 'target_environment="device"',
                          'target_cpu="arm64"', 'ios_deployment_target="13.0"']),
    ('iOS-arm64-simulator', ['target_os="ios"', 'target_environment="simulator"',
                             'target_cpu="arm64"', 'ios_deployment_target="13.0"']),
    ('iOS-x64-simulator', ['target_os="ios"', 'target_environment="simulator"',
                           'target_cpu="x64"', 'ios_deployment_target="13.0"']),
    ('macOS-arm64', ['target_os="mac"', 'target_cpu="arm64"',
                     'mac_deployment_target="10.15"']),
    ('macOS-x64', ['target_os="mac"', 'target_cpu="x64"',
                   'mac_deployment_target="10.15"']),
    ('catalyst-arm64', ['target_os="ios"', 'target_environment="catalyst"',
                        'target_cpu="arm64"', 'ios_deployment_target="14.0"']),
    ('catalyst-x64', ['target_os="ios"', 'target_environment="catalyst"',
                      'target_cpu="x64"', 'ios_deployment_target="14.0"']),
    ('tvOS-arm64-device', ['target_os="ios"', 'target_environment="appletv"',
                           'target_cpu="arm64"', 'ios_deployment_target="17.0"']),
    ('tvOS-arm64-simulator', ['target_os="ios"', 'target_environment="appletvsimulator"',
                              'target_cpu="arm64"', 'ios_deployment_target="17.0"']),
    ('xrOS-arm64-device', ['target_os="ios"', 'target_environment="xrdevice"',
                           'target_cpu="arm64"', 'ios_deployment_target="26.0"']),
    ('xrOS-arm64-simulator', ['target_os="ios"', 'target_environment="xrsimulator"',
                              'target_cpu="arm64"', 'ios_deployment_target="26.0"']),
]

# (merged dir, slice whose bundle is copied, slices whose binaries are lipo'd)
APPLE_UNIVERSAL = [
    ('macOS-lib', 'macOS-x64', ['macOS-arm64', 'macOS-x64']),
    ('catalyst-lib', 'catalyst-arm64', ['catalyst-arm64', 'catalyst-x64']),
    ('iOS-device-lib', 'iOS-arm64-device', ['iOS-arm64-device']),
    ('iOS-simulator-lib', 'iOS-arm64-simulator', ['iOS-arm64-simulator', 'iOS-x64-simulator']),
]

APPLE_XCFRAMEWORK_SLICES = [
    'iOS-device-lib',
    'iOS-simulator-lib',
    'macOS-lib',
    'catalyst-lib',
    'tvOS-arm64-device',
    'tvOS-arm64-simulator',
    'xrOS-arm64-device',
    'xrOS-arm64-simulator',
]


def apple_common_gn_args(debug: bool) -> List[str]:
    d = 'true' if debug else 'false'
    return [
        'enable_dsyms=true',
        'enable_libaom=true',
        'enable_stripping=true',
        'ios_enable_code_signing=false',
        'is_component_build=false',
        f'is_debug={d}',
        'rtc_build_examples=false',
        'rtc_enable_protobuf=false',
        'rtc_enable_symbol_export=true',
        'rtc_include_dav1d_in_internal_decoder_factory=true',
        'rtc_include_tests=false',
        'rtc_libvpx_build_vp9=true',
        'rtc_use_h264=false',
        f'strip_absolute_paths_from_debug_symbols={"false" if debug else "true"}',
        'treat_warnings_as_errors=true',
        'use_rtti=true',
    ]


def build_apple(ctx: Context, name: str, t: Target):
    apply_patches(ctx, t.patches, tuple(t.patches))
    fw = f'{t.prefix}WebRTC'
    out = ctx.out_dir(name)

    for platform_name, platform_args in APPLE_PLATFORMS:
        print(f'::group::{name}: {platform_name}', flush=True)
        slice_dir = os.path.join(out, platform_name)
        # Target-specific args last: GN keeps the last assignment.
        gn_gen(ctx, slice_dir, [*apple_common_gn_args(ctx.debug), *platform_args,
                                *t.extra_gn_args])
        bundle = 'mac_framework_bundle' if 'macOS' in platform_name else 'ios_framework_bundle'
        ninja(ctx, slice_dir, [bundle])
        print('::endgroup::', flush=True)

    # Universal binaries.
    for lib, base, slices in APPLE_UNIVERSAL:
        lib_dir = os.path.join(out, lib)
        rm_rf(lib_dir)
        mkdir_p(lib_dir)
        shutil.copytree(os.path.join(out, base, f'{fw}.framework'),
                        os.path.join(lib_dir, f'{fw}.framework'), symlinks=True)
        run(['lipo', '-create', '-output', os.path.join(lib_dir, f'{fw}.framework', fw),
             *[os.path.join(out, s, f'{fw}.framework', fw) for s in slices]])
        if os.path.isdir(os.path.join(out, base, f'{fw}.dSYM')):
            shutil.copytree(os.path.join(out, base, f'{fw}.dSYM'),
                            os.path.join(lib_dir, f'{fw}.dSYM'), symlinks=True)
            dwarf = os.path.join('Contents', 'Resources', 'DWARF', fw)
            run(['lipo', '-create', '-output', os.path.join(lib_dir, f'{fw}.dSYM', dwarf),
                 *[os.path.join(out, s, f'{fw}.dSYM', dwarf) for s in slices]])

    # XCFramework with debug symbols.
    xcframework = os.path.join(out, f'{fw}.xcframework')
    rm_rf(xcframework)
    xc_args = ['xcodebuild', '-create-xcframework']
    for s in APPLE_XCFRAMEWORK_SLICES:
        slice_dir = os.path.join(out, s)
        xc_args += ['-framework', os.path.join(slice_dir, f'{fw}.framework')]
        # Xcode names dSYM bundles <Framework>.framework.dSYM; Chromium emits <Framework>.dSYM.
        dsym = os.path.join(slice_dir, f'{fw}.framework.dSYM')
        chromium_dsym = os.path.join(slice_dir, f'{fw}.dSYM')
        if os.path.isdir(chromium_dsym):
            rm_rf(dsym)
            os.rename(chromium_dsym, dsym)
        if not os.path.isdir(dsym):
            raise RuntimeError(f'missing dSYM {chromium_dsym}')
        xc_args += ['-debug-symbols', dsym]
    run([*xc_args, '-output', xcframework])

    shutil.copy2(os.path.join(ctx.src_dir, 'LICENSE'), xcframework)

    # macOS and Catalyst frameworks must use the versioned bundle layout.
    for slice_id in ('macos-arm64_x86_64', 'ios-arm64_x86_64-maccatalyst'):
        fw_dir = os.path.join(xcframework, slice_id, f'{fw}.framework')
        os.replace(os.path.join(fw_dir, fw), os.path.join(fw_dir, 'Versions', 'A', fw))
        os.symlink(os.path.join('Versions', 'Current', fw), os.path.join(fw_dir, fw))

    zip_path = os.path.join(out, f'{fw}.xcframework.zip')
    rm_rf(zip_path)
    # zip(1) keeps the symlinks the versioned bundles rely on.
    run(['zip', '--symlinks', '-9', '-r', '-q', zip_path, f'{fw}.xcframework'], cwd=out)
    publish(ctx, zip_path, t.package)


# ---------------------------------------------------------------------------
# Android: libwebrtc.aar
# ---------------------------------------------------------------------------

def android_version_java_path(ctx: Context) -> str:
    return os.path.join(ctx.src_dir, 'sdk', 'android', 'api', 'org', 'webrtc',
                        'WebrtcBuildVersion.java')


def write_android_version_java(ctx: Context):
    # Compiled in through android_webrtc_version.patch.
    parts = ctx.version['WEBRTC_BUILD_VERSION'].split('.')
    branch = f'M{parts[0]}' if len(parts) >= 3 else ''
    commit = parts[2] if len(parts) >= 3 else ''
    maint = parts[3] if len(parts) >= 4 else ''
    revision = capture(['git', 'rev-parse', 'HEAD'], cwd=ctx.src_dir)
    lines = [
        'package org.webrtc;',
        'public interface WebrtcBuildVersion {',
        f'    public static final String webrtc_branch = "{branch}";',
        f'    public static final String webrtc_commit = "{commit}";',
        f'    public static final String webrtc_revision = "{revision}";',
        f'    public static final String maint_version = "{maint}";',
        '}',
    ]
    with open(android_version_java_path(ctx), 'w', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def build_android(ctx: Context, name: str, t: Target):
    apply_patches(ctx, t.patches, tuple(t.patches))
    write_android_version_java(ctx)
    d = 'true' if ctx.debug else 'false'
    gn_args = [
        f'is_debug={d}',
        f'is_java_debug={d}',
        'treat_warnings_as_errors=false',
        *COMMON_GN_ARGS,
        *t.extra_gn_args,
    ]
    out = ctx.out_dir(name)
    mkdir_p(out)
    aar = os.path.join(out, 'libwebrtc.aar')
    cmd = [sys.executable, os.path.join('tools_webrtc', 'android', 'build_aar.py'),
           '--build-dir', out,
           '--output', aar,
           '--arch', *ANDROID_ARCHS,
           '--extra-gn-args', gn_args_str(gn_args)]
    if ctx.jobs:
        # '=' form: argparse would read a bare '-j8' as an option.
        cmd += [f'--extra-ninja-switches=-j{ctx.jobs}']
    run(cmd, cwd=ctx.src_dir)
    publish(ctx, aar, t.package)


# ---------------------------------------------------------------------------
# libwebrtc: portable C++ wrapper for Linux / Windows
# ---------------------------------------------------------------------------

LIBWEBRTC_ITEMS = ['include', 'src', 'patches', 'test', 'BUILD.gn', 'LICENSE']


def build_libwebrtc(ctx: Context, name: str, t: Target):
    if not ctx.libwebrtc_dir or not os.path.isfile(
            os.path.join(ctx.libwebrtc_dir, 'BUILD.gn')):
        raise RuntimeError('--libwebrtc-dir must point to a webrtc-sdk/libwebrtc checkout')

    patches = LIBWEBRTC_PATCHES[t.os]
    key = ('libwebrtc', ctx.libwebrtc_dir, *patches)
    if ctx.applied != key:
        if ctx.applied != ():
            reset_tree(ctx)
        dst = os.path.join(ctx.src_dir, 'libwebrtc')
        mkdir_p(dst)
        for item in LIBWEBRTC_ITEMS:
            src = os.path.join(ctx.libwebrtc_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(dst, item))
            else:
                shutil.copy2(src, dst)
        for patch in patches:
            run(['git', 'apply', '-v', '--ignore-space-change', '--ignore-whitespace',
                 '--whitespace=nowarn', os.path.join(ctx.libwebrtc_dir, 'patches', patch)],
                cwd=ctx.src_dir)
        ctx.applied = key

    d = 'true' if ctx.debug else 'false'
    common = [
        f'is_debug={d}',
        f'target_cpu="{t.cpu}"',
        'rtc_enable_protobuf=false',
        'rtc_include_tests=true',
        'rtc_build_tools=false',
        'rtc_build_examples=false',
        'rtc_libvpx_build_vp9=true',
        'enable_libaom=true',
        'is_component_build=false',
        'ffmpeg_branding="Chrome"',
        'rtc_use_h264=true',
        'rtc_use_h265=true',
        'symbol_level=0',
        'enable_iterator_debugging=false',
    ]
    if t.os == 'linux':
        run([sys.executable, os.path.join('build', 'linux', 'sysroot_scripts',
                                          'install-sysroot.py'), f'--arch={t.cpu}'],
            cwd=ctx.src_dir)
        # use_clang_modules=false avoids C++ module compile failures that leave
        # the build incomplete.
        gn_args = [*common,
                   'target_os="linux"',
                   'treat_warnings_as_errors=false',
                   'use_llvm_libatomic=false',
                   'use_custom_libcxx=true',
                   'use_custom_libcxx_for_host=true',
                   'use_clang_modules=false',
                   'enable_stripping=true',
                   'rtc_use_pipewire=true',
                   'use_rtti=true',
                   'rtc_use_x11=true']
    else:
        gn_args = [*common,
                   'is_clang=true',
                   'use_custom_libcxx=false']

    out = ctx.out_dir(name)
    gn_gen(ctx, out, gn_args)
    ninja(ctx, out, ['libwebrtc', 'libwebrtc_cpp_api_unittests'])

    # Directory names inside the zips are kept from the old libwebrtc releases.
    if t.os == 'linux':
        stage_name = f'linux-{t.cpu}-{ctx.config}'
        libs = ['libwebrtc.so']
    else:
        stage_name = f'libwebrtc-{t.cpu}-{ctx.config}'
        libs = ['libwebrtc.dll.lib', 'libwebrtc.dll']
    stage = os.path.join(out, 'package', stage_name)
    rm_rf(stage)
    mkdir_p(os.path.join(stage, 'lib'))
    for lib in libs:
        shutil.copy2(os.path.join(out, lib), os.path.join(stage, 'lib'))
    shutil.copy2(os.path.join(ctx.libwebrtc_dir, 'LICENSE'), stage)
    shutil.copytree(os.path.join(ctx.libwebrtc_dir, 'include'), os.path.join(stage, 'include'),
                    ignore=shutil.ignore_patterns('.*'))

    zip_name = f'libwebrtc-{t.os}-{t.cpu}-{ctx.config}.zip'
    zip_path = os.path.join(out, 'package', zip_name)
    zip_dir(stage, zip_path)
    publish(ctx, zip_path, zip_name)


# ---------------------------------------------------------------------------
# Unit tests (rtc_unittests, debug) on the host platform
# ---------------------------------------------------------------------------

def run_tests(ctx: Context):
    apply_patches(ctx, TEST_PATCHES, ('test', *TEST_PATCHES))
    gn_args = [
        'is_debug=true',
        'rtc_include_tests=true',
        *[a for a in COMMON_GN_ARGS if not a.startswith('rtc_enable_protobuf=')],
        'rtc_enable_protobuf=true',
        *TEST_GN_ARGS[HOST],
    ]
    out = ctx.out_dir('rtc_unittests')
    gn_gen(ctx, out, gn_args)
    ninja(ctx, out, ['rtc_unittests'])
    # file_utils_override.cc takes the project root as two levels above the
    # binary, i.e. src/ for src/out/<dir>, where gclient puts resources/.
    if not os.path.isdir(os.path.join(ctx.src_dir, 'resources')):
        raise RuntimeError('src/resources missing; gclient sync did not fetch test resources')
    exe = 'rtc_unittests.exe' if HOST == 'Windows' else 'rtc_unittests'
    run([os.path.join(out, exe)], cwd=ctx.src_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

BUILDERS = {
    'apple': build_apple,
    'android': build_android,
    'libwebrtc': build_libwebrtc,
}


def add_common_args(p: argparse.ArgumentParser):
    p.add_argument('--commit',
                   help='webrtc-sdk/webrtc commit, tag or "HEAD" (default: WEBRTC_COMMIT in VERSION)')
    p.add_argument('--work-dir', default=ROOT_DIR,
                   help='directory for _source and _package (default: %(default)s)')
    p.add_argument('--package-dir', help='output directory (default: <work-dir>/_package)')
    p.add_argument('--no-sync', action='store_true',
                   help='build the existing checkout without fetching or gclient sync')
    p.add_argument('--fresh', action='store_true',
                   help='delete the existing checkout (and depot_tools) and sync from scratch')
    p.add_argument('--jobs', type=int, help='ninja parallelism (default: autoninja)')
    p.add_argument('--sync-for', nargs='+', default=[], choices=list(TARGETS), metavar='TARGET',
                   help='also sync for these targets (their target_os), so a checkout or git '
                        'cache shared with their jobs stays identical')
    p.add_argument('--keep-out', action='store_true',
                   help='keep build outputs (src/out) and the patched tree for local '
                        'incremental builds; by default both are cleaned')


def clean_outputs(ctx: Context):
    rm_rf(os.path.join(ctx.src_dir, 'out'))


def cleanup(ctx: Context):
    """Leave only pristine sources behind: no build outputs, no patches."""
    if not os.path.isdir(os.path.join(ctx.src_dir, '.git')):
        return
    clean_outputs(ctx)
    if ctx.applied != ():
        reset_tree(ctx)


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='op', required=True)

    bp = sub.add_parser('build', help='build release targets')
    bp.add_argument('targets', nargs='+', choices=list(TARGETS), metavar='TARGET',
                    help=', '.join(TARGETS))
    bp.add_argument('--debug', action='store_true')
    bp.add_argument('--libwebrtc-dir',
                    help='webrtc-sdk/libwebrtc checkout (libwebrtc_* targets)')
    add_common_args(bp)

    tp = sub.add_parser('test', help='build and run rtc_unittests (debug) for the host')
    add_common_args(tp)

    sp = sub.add_parser('sync', help='fetch and gclient sync the checkout for the given targets')
    sp.add_argument('targets', nargs='+', choices=list(TARGETS), metavar='TARGET',
                    help=', '.join(TARGETS))
    add_common_args(sp)

    args = parser.parse_args()

    if args.op in ('build', 'sync'):
        targets = list(dict.fromkeys(args.targets))
        sync_targets = [*targets, *args.sync_for]
    else:
        if HOST not in TEST_GN_ARGS:
            parser.error(f'unit tests are not supported on {HOST}')
        targets = []
        sync_targets = args.sync_for
    wrong_host = [n for n in sync_targets if TARGETS[n].host != HOST]
    if wrong_host:
        parser.error(f'cannot build {", ".join(wrong_host)} on {HOST}')
    target_os = sorted({os_ for n in sync_targets for os_ in TARGETS[n].target_os})

    ctx = Context(args)
    if args.fresh:
        if args.no_sync:
            parser.error('--fresh and --no-sync are mutually exclusive')
        # Remove the children, not _source itself: it may be a cache mount.
        rm_rf(ctx.gclient_dir)
        rm_rf(ctx.depot_tools_dir)
    setup_environment(ctx)
    if args.no_sync and not os.path.isdir(ctx.src_dir):
        parser.error(f'--no-sync: {ctx.src_dir} does not exist')
    if not args.keep_out:
        # Leftovers from a job that was killed before its cleanup ran.
        clean_outputs(ctx)

    try:
        if not args.no_sync:
            sync(ctx, target_os)

        if args.op == 'test':
            run_tests(ctx)
        elif args.op == 'build':
            for name in targets:
                t = TARGETS[name]
                logging.info('=== build %s (%s) ===', name, ctx.config)
                BUILDERS[t.kind](ctx, name, t)
                if not args.keep_out:
                    # Its files are in _package now; free the disk for the next target.
                    rm_rf(ctx.out_dir(name))
            logging.info('Packages in %s:', ctx.package_dir)
            for name in sorted(os.listdir(ctx.package_dir)):
                logging.info('  %s', name)
    finally:
        if not args.keep_out:
            cleanup(ctx)


if __name__ == '__main__':
    main()
