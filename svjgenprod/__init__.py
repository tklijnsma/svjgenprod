#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path as osp
import os, logging

from .logger import setup_logger, setup_subprocess_logger, formatter, subprocess_formatter
logger = setup_logger('root')
subprocess_logger = setup_subprocess_logger('subprocess')

#____________________________________________________________________
# Global scope

SVJ_TOP_DIR = osp.abspath(osp.dirname(__file__))


# Possibility of saving all logging in a file
LOG_FILE = None
def set_log_file(log_file):
    log_file = osp.abspath(log_file)
    global LOG_FILE
    LOG_FILE = log_file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # Little bit dangerous; not sure whether logging will open the same file twice
    subprocess_file_handler = logging.FileHandler(log_file)
    subprocess_file_handler.setFormatter(subprocess_formatter)
    subprocess_logger.addHandler(subprocess_file_handler)


# Input files directory for this package
SVJ_INPUT_DIR = osp.join(SVJ_TOP_DIR, 'input')


# Path to the genproductions repo installation
try:
    MG_GENPROD_DIR = os.environ['MG_GENPROD_DIR']
except KeyError:
    logger.warning(
        '$MG_GENPROD_DIR not set. Tarball generation will not work. '
        'Install the CMSSW genproductions package if want to generate tarballs.'
        )


# Paths to store temporary files
MG_MODEL_DIR = '/tmp/svj/models'
MG_INPUT_DIR = '/tmp/svj/inputs'
RUN_GRIDPACK_DIR = '/tmp/svj/rungridpack'
RUN_FULLSIM_DIR = '/tmp/svj/runfullsim'
SVJ_OUTPUT_DIR = '/tmp/svj/output'

# Set different paths for batch mode
BATCH_MODE = False
def batch_mode_lpc():
    global MG_MODEL_DIR
    global MG_INPUT_DIR
    global RUN_GRIDPACK_DIR
    global RUN_FULLSIM_DIR
    global SVJ_OUTPUT_DIR
    global BATCH_MODE
    BATCH_MODE = True
    try:
        scratch_dir = os.environ['_CONDOR_SCRATCH_DIR']
        MG_MODEL_DIR     = osp.join(scratch_dir, 'svj/models')
        MG_INPUT_DIR     = osp.join(scratch_dir, 'svj/inputs')
        RUN_GRIDPACK_DIR = osp.join(scratch_dir, 'svj/rungridpack')
        RUN_FULLSIM_DIR  = osp.join(scratch_dir, 'svj/runfullsim')
        SVJ_OUTPUT_DIR   = osp.join(scratch_dir, 'output')
    except KeyError:
        logger.error(
            'Attempted to setup for batch mode (lpc), but ${_CONDOR_SCRATCH_DIR} is not set.'
            )
        raise

if 'SVJ_BATCH_MODE' in os.environ and os.environ['SVJ_BATCH_MODE'].rstrip().lower() == 'lpc':
    batch_mode_lpc()


#____________________________________________________________________
# Package imports

import utils
from .config import Config
from .gridpackgenerator import GridpackGenerator
from .lhemaker import LHEMaker
import calc_dark_params as cdp

from .gensimfragment import GenSimFragment
from .fullsimbase import FullSimRunnerBase
import fullsimrunners

import condor.jdlfile
import condor.shfile

