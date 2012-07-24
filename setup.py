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
    scripts=['bin/regenwolken', 'bin/regenwolkenctl'],
    url='http://pypi.python.org/pypi/regenwolken/',
    license='BSD revised',
    description='open source, self-hosting CloudApp',
    data_files=[
        'README.md',
    ],
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content"
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
    ],
    install_requires=[
        'werkzeug>=0.8',
        'Jinja2>=2.4'
    ],
)