# -*- mode: python -*-
# vi: set ft=python :

import os
import platform
import shlex
import subprocess
from pathlib import Path

import aa_core
import flask_restx


def build_analysis(name, location, binaries=[], datas=[], hiddenimports=[]):
    name_py = name.replace("-", "_")
    location_candidates = [
        location / f"{name_py}/__main__.py",
        location / f"src/{name_py}/__main__.py",
    ]
    try:
        location = next(p for p in location_candidates if p.exists())
    except StopIteration:
        raise Exception(f"Could not find {name} location from {location_candidates}")

    return Analysis(
        [location],
        pathex=[],
        binaries=binaries,
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
    )


def build_collect(analysis, name, console=True):
    """Used to build the COLLECT statements for each module"""
    pyz = PYZ(analysis.pure, analysis.zipped_data)
    exe = EXE(
        pyz,
        analysis.scripts,
        exclude_binaries=True,
        name=name,
        debug=False,
        strip=False,
        upx=True,
        console=console,
        contents_directory=".",
        entitlements_file=entitlements_file,
        codesign_identity=codesign_identity,
    )
    return COLLECT(
        exe,
        analysis.binaries,
        analysis.zipfiles,
        analysis.datas,
        strip=False,
        upx=True,
        name=name,
    )


# Get the current release version
current_release = subprocess.run(
    shlex.split("git describe --tags --abbrev=0"),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    encoding="utf8",
).stdout.strip()
print("bundling activitywatch version " + current_release)

# Get entitlements and codesign identity
entitlements_file = Path(".") / "scripts" / "package" / "entitlements.plist"
codesign_identity = os.environ.get("APPLE_PERSONALID", "").strip()
if not codesign_identity:
    print("Environment variable APPLE_PERSONALID not set. Releases won't be signed.")

aa_core_path = Path(os.path.dirname(aa_core.__file__))
restx_path = Path(os.path.dirname(flask_restx.__file__))

aas_location = Path("aa-server")
aa_server_rust_location = Path("aa-server-rust")
aa_server_rust_bin = aa_server_rust_location / "target/package/aa-server-rust"
aa_sync_bin = aa_server_rust_location / "target/package/aa-sync"
aa_qt_location = Path("aa-qt")
aaa_location = Path("aa-watcher-afk")
aaw_location = Path("aa-watcher-window")
aai_location = Path("aa-watcher-input")
aa_notify_location = Path("aa-notify")

if platform.system() == "Darwin":
    icon = aa_qt_location / "media/logo/logo.icns"
else:
    icon = aa_qt_location / "media/logo/logo.ico"

skip_rust = False
if not aa_server_rust_bin.exists():
    skip_rust = True
    print("Skipping Rust build because aa-server-rust binary not found.")


aa_qt_a = build_analysis(
    "aa-qt",
    aa_qt_location,
    binaries=[(aa_server_rust_bin, "."), (aa_sync_bin, ".")] if not skip_rust else [],
    datas=[
        (aa_qt_location / "resources/aa-qt.desktop", "aa_qt/resources"),
        (aa_qt_location / "media", "aa_qt/media"),
    ],
)
aa_server_a = build_analysis(
    "aa-server",
    aas_location,
    datas=[
        (aas_location / "aa_server/static", "aa_server/static"),
        (restx_path / "templates", "flask_restx/templates"),
        (restx_path / "static", "flask_restx/static"),
        (aa_core_path / "schemas", "aa_core/schemas"),
    ],
)
aa_watcher_afk_a = build_analysis(
    "aa_watcher_afk",
    aaa_location,
    hiddenimports=[
        "Xlib.keysymdef.miscellany",
        "Xlib.keysymdef.latin1",
        "Xlib.keysymdef.latin2",
        "Xlib.keysymdef.latin3",
        "Xlib.keysymdef.latin4",
        "Xlib.keysymdef.greek",
        "Xlib.support.unix_connect",
        "Xlib.ext.shape",
        "Xlib.ext.xinerama",
        "Xlib.ext.composite",
        "Xlib.ext.randr",
        "Xlib.ext.xfixes",
        "Xlib.ext.security",
        "Xlib.ext.xinput",
        "pynput.keyboard._xorg",
        "pynput.mouse._xorg",
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
    ],
)
aa_watcher_input_a = build_analysis("aa_watcher_input", aai_location)
aa_watcher_window_a = build_analysis(
    "aa_watcher_window",
    aaw_location,
    binaries=(
        [
            (
                aaw_location / "aa_watcher_window/aa-watcher-window-macos",
                "aa_watcher_window",
            )
        ]
        if platform.system() == "Darwin"
        else []
    ),
    datas=[
        (aaw_location / "aa_watcher_window/printAppStatus.jxa", "aa_watcher_window")
    ],
)
aa_notify_a = build_analysis(
    "aa_notify", aa_notify_location, hiddenimports=["desktop_notifier.resources"]
)

# https://pythonhosted.org/PyInstaller/spec-files.html#multipackage-bundles
# MERGE takes a bit weird arguments, it wants tuples which consists of
# the analysis paired with the script name and the bin name
MERGE(
    (aa_server_a, "aa-server", "aa-server"),
    (aa_qt_a, "aa-qt", "aa-qt"),
    (aa_watcher_afk_a, "aa-watcher-afk", "aa-watcher-afk"),
    (aa_watcher_window_a, "aa-watcher-window", "aa-watcher-window"),
    (aa_watcher_input_a, "aa-watcher-input", "aa-watcher-input"),
    (aa_notify_a, "aa-notify", "aa-notify"),
)


# aa-server
aas_coll = build_collect(aa_server_a, "aa-server")

# aa-watcher-window
aaw_coll = build_collect(aa_watcher_window_a, "aa-watcher-window")

# aa-watcher-afk
aaa_coll = build_collect(aa_watcher_afk_a, "aa-watcher-afk")

# aa-qt
aaq_coll = build_collect(
    aa_qt_a,
    "aa-qt",
    console=False if platform.system() == "Windows" else True,
)

# aa-watcher-input
aai_coll = build_collect(aa_watcher_input_a, "aa-watcher-input")

aa_notify_coll = build_collect(aa_notify_a, "aa-notify")

if platform.system() == "Darwin":
    app = BUNDLE(
        aaq_coll,
        aas_coll,
        aaw_coll,
        aaa_coll,
        aai_coll,
        aa_notify_coll,
        name="ActivityWatch.app",
        icon=icon,
        bundle_identifier="net.activitywatch.ActivityWatch",
        version=current_release.lstrip("v"),
        info_plist={
            "NSPrincipalClass": "NSApplication",
            "CFBundleExecutable": "MacOS/aa-qt",
            "CFBundleIconFile": "logo.icns",
            "NSAppleEventsUsageDescription": "Please grant access to use Apple Events",
            # This could be set to a more specific version string (including the commit id, for example)
            "CFBundleVersion": current_release.lstrip("v"),
            # Replaced by the 'version' kwarg above
            # "CFBundleShortVersionString": current_release.lstrip('v'),
        },
    )
