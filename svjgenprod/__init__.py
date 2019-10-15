#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path as osp
import os, logging

from .logger import setup_logger, setup_subprocess_logger, formatter, subprocess_formatter
logger = setup_logger('root')
subprocess_logger = setup_subprocess_logger('subprocess')

#____________________________________________________________________
# Global scope

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

# Input files for this package
SVJ_INPUT_DIR = osp.join(osp.dirname(__file__), 'input')

# Path to the genproductions repo installation
MG_GENPROD_DIR = '/uscms/home/klijnsma/nobackup/semivis/genprod/genproductions/bin/MadGraph5_aMCatNLO'

# Output paths
TARBALL_OUT = '/uscms/home/klijnsma/nobackup/semivis/tarballs'
LHE_OUT = '/uscms/home/klijnsma/nobackup/semivis/lheoutput'

# Temporary paths
MG_MODEL_DIR = '/tmp/svj/models'
MG_INPUT_DIR = '/tmp/svj/inputs'
RUN_GRIDPACK_DIR = '/tmp/svj/rungridpack'
# RUN_FULLSIM_DIR = '/uscms/home/klijnsma/nobackup/semivis/fullsim'
RUN_FULLSIM_DIR = '/tmp/svj/runfullsim'

# MG_MODEL_DIR = os.environ['SVJ_MODELS_DIR']
# MG_INPUT_DIR = os.environ['SVJ_MG_INPUT_DIR']
# MG_GENPROD_DIR = os.environ['MG_GENPROD_DIR']


#____________________________________________________________________
import utils
from .config import Config
from .gridpackgenerator import GridpackGenerator
from .lhemaker import LHEMaker
import calc_dark_params as cdp

from .gensimfragment import GenSimFragment
from .fullsimbase import FullSimRunnerBase
import fullsimrunners
