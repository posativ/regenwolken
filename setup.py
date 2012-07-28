#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import sys
import re

from os.path import join, dirname
from setuptools import setup, find_packages

version = re.search("__version__ = '([^']+)'",
                    open('regenwolken/__init__.py').read()).group(1)

setup(
    name='regenwolken',
    version=version,
    author='posativ',
    author_email='info@posativ.org',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    url='http://pypi.python.org/pypi/regenwolken/',
    license='BSD revised',
    description='open source, self-hosting CloudApp',
    data_files=[
        'README.md',
        'LICENSE.txt'
    ],
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content"
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7"
    ],
    install_requires=[
        'flask>=0.8',
        'pymongo'
    ],
    entry_points={
        'console_scripts':
            ['regenwolken = regenwolken:main',
             'rwctl = regenwolken.manage:main'],
    },
)
