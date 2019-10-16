#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os, shutil, sys, glob, subprocess, re, logging
import os.path as osp
from time import strftime

import svjgenprod
logger = logging.getLogger('root')


#____________________________________________________________________
def get_config(config):
    """
    Guaranteed to return a svjgenprod.Config instance or throws an exception
    """
    if isinstance(config, svjgenprod.Config):
        return config
    elif osp.isfile(config):
        if config.endswith('.yaml'):
            return svjgenprod.Config.from_yaml(config)
        else:
            return svjgenprod.Config.from_file(config)
    else:
        raise TypeError(
            'config parameter should be either a Config instance, '
            'a path to a .yaml file, or a path to a config file.'
            )


#____________________________________________________________________
class FullSimRunnerBase(object):
    """Abstract class to subclass specific runners from"""

    seed = svjgenprod.SVJ_SEED
    _create_workdir_called = False
    _force_renew_workdir = False

    @classmethod
    def for_year(cls, config, *args, **kwargs):
        config = get_config(config)
        subclass_dict = cls.subclass_per_year()
        year = config['year']
        if not year in subclass_dict:
            raise NotImplementedError('Class {0} has no subclass for year {1}'.format(cls, year))
        Subclass = subclass_dict[year]
        return Subclass(config, *args, **kwargs)

    @classmethod
    def subclass_per_year(cls):
        raise NotImplementedError('Call this only from a subclass')

    def __init__(self, config, in_file, n_events):
        super(FullSimRunnerBase, self).__init__()
        self.config = get_config(config)
        self.year = self.config['year']
        self.model_name = self.config.get_model_name()

        self.run_name = 'fullsim_' + self.model_name
        self.fullsim_dir = svjgenprod.RUN_FULLSIM_DIR
        self.workdir = osp.join(self.fullsim_dir, self.run_name)
        self.pileup_filelist_basename = 'pileup_filelist_{0}.txt'.format(self.year)

        self.in_file = osp.abspath(in_file)
        self.n_events = n_events
        self.cfg_file_basename = '{0}_{1}_seed{2}.py'.format(self.model_name, self.substage, self.seed)
        self.cfg_file = osp.join(self.get_cmssw_src(), self.cfg_file_basename)
        self.out_root_file_basename = '{0}_{1}_seed{2}.root'.format(self.model_name, self.substage, self.seed)
        self.out_root_file = osp.join(self.get_cmssw_src(), self.out_root_file_basename)

    def create_workdir(self, dry=False):
        """
        Creates the directory in which the CMSSW(s) are set up
        May re-create once, but should not do anything after that
        """
        if not self._create_workdir_called:
            svjgenprod.utils.create_directory(self.workdir, force=self._force_renew_workdir)
        self._create_workdir_called = True
        self._force_renew_workdir = False

    def setup_cmssw(self):
        self.create_workdir()
        svjgenprod.utils.setup_cmssw(self.workdir, self.cmssw_version, self.arch)

    def copy_pileup_filelist(self):
        file_list = os.path.join(svjgenprod.SVJ_INPUT_DIR, 'pileupfilelists', self.pileup_filelist_basename)
        logger.info('Copying pileup_filelist {0} to workdir'.format(file_list))
        shutil.copy(file_list, osp.join(self.workdir, osp.basename(file_list)))

    def get_cmssw_src(self, stage=None):
        return osp.join(self.workdir, self.cmssw_version, 'src')

    def compile_cmssw(self):
        svjgenprod.utils.compile_cmssw_src(self.get_cmssw_src(), self.arch)

    def source_cmssw_cmds(self, cmssw_src=None):
        """
        Returns commands to go into a CMSSW/src directory and call cmsenv
        Useful for setting up new shell session when multiple commands follow
        """
        cmssw_src = self.get_cmssw_src() if cmssw_src is None else cmssw_src
        cmds = [
            'shopt -s expand_aliases',
            'source /cvmfs/cms.cern.ch/cmsset_default.sh',
            'cd {0}'.format(cmssw_src),
            'eval `scramv1 runtime -sh`',
            ]
        return cmds

    def get_cmsdriver_cmd(self):
        raise NotImplementedError('Use this method only in a subclass')

    def cmsdriver(self):
        cmds = self.source_cmssw_cmds()
        cmds.append(self.get_cmsdriver_cmd())
        svjgenprod.utils.run_multiple_commands(cmds)

    def cmsrun(self):
        cmds = self.source_cmssw_cmds()
        cmds.append('cmsRun {0}'.format(self.cfg_file_basename))
        svjgenprod.utils.run_multiple_commands(cmds)

    def full_chain(self):
        self.setup_cmssw()
        self.cmsdriver()
        self.cmsrun()

    def copy_to_output(self, output_dir=None, dry=False):
        if output_dir is None: output_dir = svjgenprod.SVJ_OUTPUT_DIR
        svjgenprod.utils.create_directory(output_dir)
        dst = osp.join(output_dir, osp.basename(self.out_root_file))
        logger.info('Copying {0} ==> {1}'.format(self.out_root_file, dst))
        if not dry:
            shutil.copyfile(self.out_root_file, dst)

