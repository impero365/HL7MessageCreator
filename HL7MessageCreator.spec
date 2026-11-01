# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

# hl7apy discovers version libraries with os.listdir() on its package directory.
# A PYZ-only collection leaves that directory missing at runtime, so collect the
# package as real files and pull in every version submodule.
a = Analysis(
    ['HL7MessageCreator.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('procedures.csv', '.'),
        ('staff_names.csv', '.'),
        ('surgeon_names.csv', '.'),
        ('patient_names.csv', '.'),
        ('allergies.csv', '.'),
    ],
    hiddenimports=collect_submodules('hl7apy'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    module_collection_mode={'hl7apy': 'py'},
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HL7MessageCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
