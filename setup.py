"""
Setup script for building the Accountability app as a macOS application using py2app.
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = [
    ('ui/resources', ['accountability/ui/resources/logo.png']),
]
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'LSUIElement': True,  # Make it a menu bar only app (no dock icon)
        'CFBundleName': 'Accountability',
        'CFBundleDisplayName': 'Accountability',
        'CFBundleIdentifier': 'com.accountability.app',
        'CFBundleVersion': '1.0',
        'CFBundleShortVersionString': '1.0',
        'NSHumanReadableCopyright': 'Copyright 2025',
        'NSHighResolutionCapable': True,  # Enable high-resolution mode
    },
    'packages': ['accountability'],
    'iconfile': 'accountability/ui/resources/logo.png',
    'includes': ['PyQt6'],
    'resources': ['accountability/ui/resources/logo.png'],
}

setup(
    name='Accountability',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
