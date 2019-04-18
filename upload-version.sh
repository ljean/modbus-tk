#!/usr/bin/env bash
# python -m pip install --upgrade setuptools wheel
# pip install --upgrade twine
python3 setup.py sdist bdist_wheel
python -m twine upload dist/*
rm -r dist
rm -r build
