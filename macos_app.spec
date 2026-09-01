# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[
        (
            "technocore_easy_setup/assets/technocore-background.png",
            "technocore_easy_setup/assets",
        ),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# The console bootloader is compatible with both python.org and conda-forge Tk
# builds. build_macos.sh places this one-folder runtime behind a small app-bundle
# launcher; Finder does not create a Terminal window for that launcher.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TechnocoreEasySetupRuntime",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TechnocoreEasySetupRuntime",
)
