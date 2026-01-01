from setuptools import setup

APP = ['testsetupcode.py']
OPTIONS = {
    'argv_emulation': True,
    'includes': ['customtkinter'],
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
