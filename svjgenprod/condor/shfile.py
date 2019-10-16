#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os.path as osp
import logging, os, collections
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


    def clone(self):
        if self.repo_from_tarball: return self.clone_nogit()
        return [ 'git clone https://github.com/tklijnsma/svjgenprod.git' ]


    def clone_nogit(self):
        """
        No git available on LPC worker nodes;
        extract a provided tarball manually instead.
        Effectively git clone https://github.com/tklijnsma/svjgenprod.git
        """
        sh = [
            'mkdir svjgenprod',
            'tar xf svjgenprod.tar -C svjgenprod/',
            ]
        return sh


    def install(self):
        if self.repo_from_tarball: return self.install_nopip()
        return [ 'pip install --user -e svjgenprod' ]


    def install_nopip(self):
        """
        No pip available on LPC worker nodes;
        install package manually instead.
        Effectively pip install --user -e svjgenprod
        """        
        sh = [
            'export PATH="${PWD}/svjgenprod/bin:${PATH}"',
            'export PYTHONPATH="${PWD}/svjgenprod:${PYTHONPATH}"',
            ]
        return sh


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

        sh.extend(self.clone())

        sh.append('mkdir output')
        echo('ls:')
        sh.append('ls')

        echo('ls svjgenprod:')
        sh.append('ls svjgenprod')

        sh.append('source svjgenprod/env.sh')
        # sh.append('source /cvmfs/sft.cern.ch/lcg/views/LCG_95/x86_64-centos7-gcc7-opt/setup.sh')

        sh.extend(self.install())

        sh.append('python {0}'.format(osp.basename(self.python_file)))

        sh = '\n'.join(sh)
        logger.info('Parsed sh file:\n{0}'.format(sh))
        return sh








