from setuptools import setup

setup(
    name          = 'svjgenprod',
    version       = '0.1',
    license       = 'BSD 3-Clause License',
    description   = 'Package for MC generation of semi-visible jet events',
    url           = 'https://github.com/tklijnsma/svjgenprod.git',
    download_url  = 'https://github.com/tklijnsma/svjgenprod/archive/v0_1.tar.gz',
    author        = 'Thomas Klijnsma',
    author_email  = 'tklijnsm@gmail.com',
    packages      = ['svjgenprod'],
    zip_safe      = False,
    tests_require = ['nose'],
    test_suite    = 'nose.collector',
    scripts       = [
        ],
    )
