#!/usr/bin/env python

import sys
import pencil
from setuptools import setup, find_packages

required = [
    # 'gevent>=1.0.0' not yet in PYPI.
]

if sys.version_info[:2] < (2,6):
    required.append('simplejson')

setup(
    name='pencil',
    version=pencil.__version__,
    description='A gevent based statsd replacement.',
    long_description=open('README.rst').read(),
    author='Oz Katz',
    author_email='ozkatz100@gmail.com',
    url='',
    install_requires=required,
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['README.rst']},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)