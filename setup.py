#!/usr/bin/env python
from distutils.core import setup

setup(
    name='beangulp-simplefin',
    version='0.1.0',
    description='Beangulp importer for SimpleFIN',
    author='Rob Cohen',
    author_email='rob@robcohen.io',
    packages=[],
    py_modules=['beangulp_simplefin'],
    package_data={},
    install_requires=[
        'beangulp',
        'beancount',
    ],
)
