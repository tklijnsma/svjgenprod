#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os.path as osp
import logging, subprocess, os, shutil, yaml, re, collections, copy
import svjgenprod
logger = logging.getLogger('root')


class SHBase(object):
    """docstring for SHBase"""
    def __init__(self):
        super(SHBase, self).__init__()

    def to_file(self, file, dry=False):
        parsed = self.parse()
        logger.info('Writing to {0}'.format(file))
        if not dry:
            with open(file, 'w') as f:
                f.write(parsed)


class SHClean(SHBase):
    """docstring for SHClean"""
    def __init__(self):
        super(SHClean, self).__init__()
        self.lines = [
            'rm *.stdout',
            'rm *.stderr',
            'rm *.log'
            ]

    def parse(self):
        return '\n'.join(self.lines)


class SHStandard(SHBase):
    """docstring for SHStandard"""
    def __init__(self, python_file, svjgenprod_tarball=None):
        super(SHStandard, self).__init__()
        self.python_file = python_file

        self.repo_from_tarball = False
        if not(svjgenprod_tarball is None):
            self.repo_from_tarball = True
            self.svjgenprod_tarball = svjgenprod_tarball


    def parse(self):
        sh = []
        echo = lambda text: sh.append('echo "{0}"'.format(text))

        sh.append('#!/bin/bash')
        sh.append('set -e')
        echo('##### HOST DETAILS #####')
        echo('hostname:')
        sh.append('hostname')
        echo('date:')
        sh.append('date')
        echo('pwd:')
        sh.append('pwd')

        if self.repo_from_tarball:
            sh.append('mkdir svjgenprod')
            sh.append('tar xf svjgenprod.tar -C svjgenprod/')
        else:
            sh.append('git clone https://github.com/tklijnsma/svjgenprod.git')

        sh.append('mkdir output')
        echo('ls:')
        sh.append('ls')

        echo('ls svjgenprod:')
        sh.append('ls svjgenprod')

        sh.append('source svjgenprod/env.sh')

        echo('Installing setuptools')
        sh.append('wget https://bootstrap.pypa.io/ez_setup.py -O - | python - --user')

        sh.append('pip install --user svjgenprod')
        sh.append('python {0}'.format(osp.basename(self.python_file)))

        sh = '\n'.join(sh)
        logger.info('Parsed sh file:\n{0}'.format(sh))
        return sh








