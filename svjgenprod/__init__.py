#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path as osp
import os, logging
from termcolor import colored
def setup_custom_logger(name):
    formatter = logging.Formatter(
        fmt = colored('[svj|%(levelname)s|%(asctime)s|%(module)s]:', 'yellow') + ' %(message)s'
        )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

logger = setup_custom_logger('root')

#____________________________________________________________________
# Global variables

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
from .fullsim import (
    FullSimBase,
    FullSimCMSSWSetup,
    FullSimRunnerGenSim,
    FullSimRunnerAOD,
    FullSimRunnerAODstep2,
    FullSimRunnerMiniAOD,
    FullSimRunnerNanoAOD,
    )
from .gensimfragment import GenSimFragment
