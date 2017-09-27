#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='dbbk',
    packages=find_packages(),
    scripts=['bin/dbbk_server.py'],
    install_requires=['pandas', 'bokeh', 'tornado', 'jinja2'],
    package_data={
        'dbbk': ['coffee/*.coffee', 'templates/embed.html'],
    },
)
