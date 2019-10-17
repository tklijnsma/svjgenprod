#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os, sys
import os.path as osp
import svjgenprod

def read_environment():
    """
    Defines a bunch of global variables of the package based on environment
    """
    env = os.environ

    if 'SVJ_SEED' in env:
        svjgenprod.SVJ_SEED = int(env['SVJ_SEED'])
        logger.info(
            'Taking seed from SVJ_SEED environment variable: {0}'
            .format(svjgenprod.SVJ_SEED)
            )

    # Path to the genproductions repo installation
    try:
        svjgenprod.MG_GENPROD_DIR = env['MG_GENPROD_DIR']
    except KeyError:
        logger.warning(
            '$MG_GENPROD_DIR not set. Tarball generation will not work. '
            'Install the CMSSW genproductions package if you want to generate tarballs.'
            )

    if 'SVJ_BATCH_MODE' in env:
        batch_mode = env['SVJ_BATCH_MODE'].rstrip().lower()
        if batch_mode == 'lpc':
            batch_mode_lpc()
        else:
            raise ValueError(
                'Unknown batch mode {0}. If you are not trying '
                'to run on a batch system, unset the SVJ_BATCH_MODE '
                'environment variable.'
                .format(batch_mode)
                )


def batch_mode_lpc():
    svjgenprod.BATCH_MODE = True
    try:
        scratch_dir = os.environ['_CONDOR_SCRATCH_DIR']
        svjgenprod.MG_MODEL_DIR     = osp.join(scratch_dir, 'svj/models')
        svjgenprod.MG_INPUT_DIR     = osp.join(scratch_dir, 'svj/inputs')
        svjgenprod.RUN_GRIDPACK_DIR = osp.join(scratch_dir, 'svj/rungridpack')
        svjgenprod.RUN_FULLSIM_DIR  = osp.join(scratch_dir, 'svj/runfullsim')
        svjgenprod.SVJ_OUTPUT_DIR   = osp.join(scratch_dir, 'output')
    except KeyError:
        logger.error(
            'Attempted to setup for batch mode (lpc), but ${_CONDOR_SCRATCH_DIR} is not set.'
            )
        raise

