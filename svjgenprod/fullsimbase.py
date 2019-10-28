#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os, shutil, sys, glob, subprocess, re, logging
import os.path as osp
from time import strftime

import svjgenprod
logger = logging.getLogger('root')


#____________________________________________________________________
class FullSimRunnerBase(object):
    """Abstract class to subclass specific runners from"""

    seed = svjgenprod.SVJ_SEED
    _create_workdir_called = False
    _force_renew_workdir = False

    @classmethod
    def for_year(cls, config, *args, **kwargs):
        config = svjgenprod.Config.flexible_init(config)
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
        self.config = svjgenprod.Config.flexible_init(config)
        self.year = self.config['year']
        self.model_name = self.config.get_model_name()

        self.run_name = 'fullsim_' + self.model_name
        self.fullsim_dir = svjgenprod.RUN_FULLSIM_DIR
        self.workdir = osp.join(self.fullsim_dir, self.run_name)
        self.pileup_filelist_basename = 'pileup_filelist_{0}.txt'.format(self.year)

        self.in_file = osp.abspath(in_file)
        self.n_events = n_events
        self.cfg_file_basename = '{0}_{1}_N{2}_seed{3}.py'.format(self.model_name, self.substage, self.n_events, self.seed)
        self.cfg_file = osp.join(self.get_cmssw_src(), self.cfg_file_basename)
        self.out_root_file_basename = '{0}_{1}_N{2}_seed{3}.root'.format(self.model_name, self.substage, self.n_events, self.seed)
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

    def edit_cmsdriver_output(self):
        """
        Overwrite this method in case edits need to made to the .cfg output
        of the cmsDriver command before doing cmsRun
        """
        pass

    def cmsrun(self):
        cmds = self.source_cmssw_cmds()
        cmds.append('cmsRun {0}'.format(self.cfg_file_basename))
        svjgenprod.utils.run_multiple_commands(cmds)

    def full_chain(self):
        self.setup_cmssw()
        self.cmsdriver()
        self.edit_cmsdriver_output()
        self.cmsrun()

    def _get_cmsdriver_output(self):
        logger.info('Reading {0}'.format(self.cfg_file))
        with open(self.cfg_file, 'r') as f:
            contents = f.read()
        return contents

    def _overwrite_cmsdriver_output(self, contents):
        logger.warning('Overwriting {0}'.format(self.cfg_file))
        with open(self.cfg_file, 'w') as f:
            f.write(contents)

    def copy_to_output(self, output_dir=None, dry=False):
        if output_dir is None: output_dir = svjgenprod.SVJ_OUTPUT_DIR
        svjgenprod.utils.create_directory(output_dir)
        dst = osp.join(output_dir, osp.basename(self.out_root_file))
        logger.info('Copying {0} ==> {1}'.format(self.out_root_file, dst))
        if not dry:
            shutil.copyfile(self.out_root_file, dst)

    def move_to_output(self, output_dir=None, dry=False):
        if output_dir is None: output_dir = svjgenprod.SVJ_OUTPUT_DIR
        svjgenprod.utils.create_directory(output_dir)
        dst = osp.join(output_dir, osp.basename(self.out_root_file))
        logger.info('Moving {0} ==> {1}'.format(self.out_root_file, dst))
        if not dry:
            shutil.move(self.out_root_file, dst)

    def stageout(self, stageout_directory=None):
        """
        Stages out a file to the lpc SE
        """
        if stageout_directory is None:
            # Make something reasonable
            if svjgenprod.BATCH_MODE:
                condor_cluster = os.environ['$CONDOR_CLUSTER']
            else:
                condor_cluster = 'local'
            stageout_directory = (
                '/store/user/{user}/semivis/{condor_cluster}_{substage}_{model_name}'
                .format(
                    user = os.environ['USER'],
                    condor_cluster = condor_cluster,
                    substage = self.substage,
                    model_name = self.model_name
                    )
                )
        dst = osp.join(stageout_directory, 'N{0}_seed{1}.root'.format(self.n_events, self.seed))
        semanager = svjgenprod.SEManager()
        semanager.copy_to_se(self.out_root_file, dst, create_parent_directory=True)

