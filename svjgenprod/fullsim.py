#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os, shutil, sys, glob, subprocess, re, logging
import os.path as osp
from time import strftime

import svjgenprod
logger = logging.getLogger('root')



def get_config(config):
    """
    Guaranteed to return a svjgenprod.Config instancse or throws an exception
    """
    if isinstance(config, svjgenprod.Config):
        return config
    elif osp.isfile(config):
        return svjgenprod.Config.from_yaml(config)
    else:
        raise TypeError('config parameter should be either a Config instance or a path to a .yaml file.')


class FullSimBase(object):
    """docstring for FullSimBase"""
        
    cmssw_info = {
        2016 : {
            'gensim'     : {'version': 'CMSSW_7_1_38_patch1', 'arch': 'slc6_amd64_gcc481'},  # earlier versions don't have CMSSW plug-ins for dark quark/Z2 filters
            'aod'        : {'version': 'CMSSW_8_0_21', 'arch': 'slc6_amd64_gcc530'},
            'nano'       : {'version': 'CMSSW_9_4_4', 'arch': 'slc6_amd64_gcc630'},
            'new_pythia' : True  # CMSSW_7_1_38_patch1 ships with old Pythia version
            },
        2017 : {
            'gensim'     : {'version': 'CMSSW_9_3_15', 'arch': 'slc7_amd64_gcc630'},  # earlier versions (at least <=9_3_12) don't have CMSSW plug-ins for dark quark/Z2 filters
            'aod'        : {'version': 'CMSSW_9_4_10', 'arch': 'slc7_amd64_gcc630'},
            'nano'       : {'version': 'CMSSW_10_2_15', 'arch': 'slc7_amd64_gcc700'},
            'new_pythia' : False  # CMSSW_9_3_15 already ships with Pythia 8.230            
            },
        2018 : {
            'gensim'     : {'version': 'CMSSW_10_2_15', 'arch': 'slc7_amd64_gcc700'},  # earlier versions (at least <=10_2_3) don't have CMSSW plug-ins for dark quark/Z2 filters
            'aod'        : {'version': 'CMSSW_10_2_15', 'arch': 'slc7_amd64_gcc700'},
            'nano'       : {'version': 'CMSSW_10_2_15', 'arch': 'slc7_amd64_gcc700'},
            'new_pythia' : False  # CMSSW_10_2_15 already ships with Pythia 8.230
            }
        }

    stages = [ 'gensim', 'aod', 'nano' ]
    seed = 1001


    def __init__(self, config):
        super(FullSimBase, self).__init__()
        self.config = get_config(config)

        self.year = self.config['year']
        self.model_name = self.config.get_model_name()

        self.run_name = 'fullsim_' + self.model_name
        self.fullsim_dir = svjgenprod.RUN_FULLSIM_DIR
        self.workdir = osp.join(self.fullsim_dir, self.run_name)
        self.pileup_filelist_basename = 'pileup_filelist_{0}.txt'.format(self.year)


    def get_stage(self, stage=None):
        """
        Attempts to get the stage from self.stage if not provided
        """
        if stage is None:
            if not hasattr(self, 'stage'): raise TypeError('Provide argument stage or set self.stage')
            stage = self.stage
        return stage

    def get_cmssw_version(self, stage=None):
        """
        Returns the CMSSW version to be used for this year and stage
        """
        return self.cmssw_info[self.year][self.get_stage(stage)]['version']

    def get_cmssw_src(self, stage=None):
        """
        Returns the CMSSW_X_Y/src path for this year and stage
        """
        return osp.join(self.workdir, self.get_cmssw_version(), 'src')

    def get_arch(self, stage=None):
        """
        Returns the scram arch to be used for this year and stage
        """
        return self.cmssw_info[self.year][self.get_stage(stage)]['arch']


    def compile_cmssw(self, stage=None):
        svjgenprod.utils.compile_cmssw_src(self.get_cmssw_src(stage), self.get_arch(stage))


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


#____________________________________________________________________
class FullSimCMSSWSetup(FullSimBase):
    """docstring for FullSimCMSSWSetup"""

    def __init__(self, config):
        super(FullSimCMSSWSetup, self).__init__(config)
        self.force_renew_workdir = False
        self._create_workdir_called = False
        logger.info('Setting up CMSSWs in workdir: {0}'.format(self.workdir))


    def create_workdir(self, dry=False):
        """
        Creates the directory in which the CMSSW(s) are set up
        May re-create once, but should not do anything after that
        """
        if not self._create_workdir_called:
            svjgenprod.utils.create_directory(self.workdir, force=self.force_renew_workdir)
        self._create_workdir_called = True


    def setup_cmssws(self):
        self.create_workdir()
        for stage in self.stages:
            logger.info('Stage: {0}'.format(stage))
            svjgenprod.utils.setup_cmssw(self.workdir, self.get_cmssw_version(stage), self.get_arch(stage))


    def copy_pileup_filelist(self):
        self.create_workdir()
        file_list = os.path.join(svjgenprod.SVJ_INPUT_DIR, 'pileupfilelists', self.pileup_filelist_basename)
        logger.info('Copying pileup_filelist {0} to workdir'.format(file_list))
        shutil.copy(file_list, osp.join(self.workdir, osp.basename(file_list)))


#____________________________________________________________________
class FullSimRunner(FullSimBase):
    """Abstract class to subclass specific runners from"""

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
        super(FullSimRunner, self).__init__(config)
        self.in_file = osp.abspath(in_file)
        self.n_events = n_events
        self.cfg_file_basename = '{0}_{1}_{2}.py'.format(self.model_name, self.substage, self.seed)
        self.cfg_file = osp.join(self.get_cmssw_src(), self.cfg_file_basename)
        self.out_root_file_basename = '{0}_{1}_{2}.root'.format(self.model_name, self.substage, self.seed)
        self.out_root_file = osp.join(self.get_cmssw_src(), self.out_root_file_basename)

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


#____________________________________________________________________

# class FullSimRunnerGenSimFactory(object):
#     """docstring for FullSimRunnerGenSimFactory"""
#     def __init__(self, config, *args, **kwargs):
#         super(FullSimRunnerGenSimFactory, self).__init__()
#         config = get_config(config)

#     subclass_per_year = {
#         # 2016: FullSimRunnerGenSim2016,
#         2017: FullSimRunnerGenSim2017,
#         2018: FullSimRunnerGenSim2018,
#         }

        

class FullSimRunnerGenSim(FullSimRunner):
    """docstring for FullSimRunnerGenSim"""

    stage = 'gensim'
    substage = 'GEN_SIM'

    @classmethod
    def subclass_per_year(cls):
        return {
            # 2016: FullSimRunnerGenSim2016,
            2017: FullSimRunnerGenSim2017,
            2018: FullSimRunnerGenSim2018,
            }

    def __init__(self, *args, **kwargs):
        super(FullSimRunnerGenSim, self).__init__(*args, **kwargs)
        self.gensimfragment_basename = 'SVJGenSimFragment.py'
        self.gensimfragment_dir = osp.join(self.get_cmssw_src(), 'Configuration/GenProduction/python')
        self.gensimfragment_file = osp.join(self.gensimfragment_dir, self.gensimfragment_basename)

    def add_gensimfragment(self):
        """
        Creates the gensimfragment
        """
        svjgenprod.utils.create_directory(self.gensimfragment_dir)
        gensimfragment = svjgenprod.GenSimFragment(self.config)
        gensimfragment.to_file(self.gensimfragment_file)
        self.compile_cmssw()

    def cmsdriver(self):
        super(FullSimRunnerGenSim, self).cmsdriver()
        self.small_edits_gensim_cfg_file(self.cfg_file)

    def small_edits_gensim_cfg_file(self, cfg_file):
        """
        Takes the cfg file generated by cmsDriver.py, edits some lines, and re-saves
        Based on simple string replacement, somewhat fragile code
        """
        logger.warning('Doing dangerous replacements on {0}; fragile code!'.format(cfg_file))
        with open(cfg_file, 'r') as f:
            contents = f.read()

        def replace_exactly_once(string, to_replace, replace_by):
            if not to_replace in string:
                raise ValueError('Substring "{0}" not found'.format(string))
            return string.replace(to_replace, replace_by, 1)

        # Add to CMSSW config in case stringent hadronisation cuts remove all events from a job
        contents = replace_exactly_once(contents,
            'process.options = cms.untracked.PSet(\n',
            ( 
                'process.options = cms.untracked.PSet(\n'
                '    SkipEvent = cms.untracked.vstring(\'ProductNotFound\'),\n'
                )
            )

        # Add to CMSSW config to ensure Z2 and dark quark filters are used
        contents = replace_exactly_once(contents,
            'seq = process.generator',
            'seq = (process.generator + process.darkhadronZ2filter + process.darkquarkFilter)'
            )

        logger.warning('Overwriting {0}'.format(cfg_file))
        with open(cfg_file, 'w') as f:
            f.write(contents)


class FullSimRunnerGenSim2017(FullSimRunnerGenSim):
    def get_cmsdriver_cmd(self):
        return [
            'cmsDriver.py Configuration/GenProduction/python/{0}'.format(self.gensimfragment_basename),
            '--filein file:{0}'.format(self.in_file),
            '--fileout file:{0}'.format(self.out_root_file_basename),
            '--mc',
            '--eventcontent RAWSIM',
            '--datatier GEN-SIM',
            '--conditions 93X_mc2017_realistic_v3',
            '--beamspot Realistic25ns13TeVEarly2017Collision',
            '--step GEN,SIM',
            '--geometry DB:Extended',
            '--era Run2_2017',
            '--customise Configuration/DataProcessing/Utils.addMonitoring',
            '--python_filename {0}'.format(self.cfg_file_basename),
            '--no_exec',
            '-n {0}'.format(self.n_events),
            ]

class FullSimRunnerGenSim2018(FullSimRunnerGenSim):
    def get_cmsdriver_cmd(self):
        return [
            'cmsDriver.py Configuration/GenProduction/python/{0}'.format(self.gensimfragment_basename),
            '--filein file:{0}'.format(self.in_file),
            '--fileout file:{0}'.format(self.out_root_file_basename),
            '--mc',
            '--eventcontent RAWSIM',
            '--datatier GEN-SIM',
            '--conditions 102X_upgrade2018_realistic_v11',
            '--beamspot Realistic25ns13TeVEarly2018Collision',
            '--step GEN,SIM',
            '--geometry DB:Extended',
            '--era Run2_2018',
            '--customise Configuration/DataProcessing/Utils.addMonitoring',
            '--python_filename {0}'.format(self.cfg_file_basename),
            '--no_exec',
            '-n {0}'.format(self.n_events),
            ]


#____________________________________________________________________
class FullSimRunnerAOD(FullSimRunner):
    stage = 'aod'
    substage = 'AOD_step1'
    @classmethod
    def subclass_per_year(cls):
        return {
        # 2016: FullSimRunnerAOD2016,
        2017: FullSimRunnerAOD2017,
        # 2018: FullSimRunnerAOD2018,
        }

class FullSimRunnerAOD2017(FullSimRunnerAOD):
    def get_cmsdriver_cmd(self):
        return [
            'cmsDriver.py step1',
            '--filein file:{0}'.format(self.in_file),
            '--fileout file:{0}'.format(self.out_root_file_basename),
            '--pileup_input filelist:"{0}"'.format(osp.join(self.workdir, self.pileup_filelist_basename)),
            '--mc',
            '--eventcontent PREMIXRAW',
            '--datatier GEN-SIM-RAW',
            '--conditions 94X_mc2017_realistic_v11',
            '--step DIGIPREMIX_S2,DATAMIX,L1,DIGI2RAW,HLT:2e34v40',
            '--datamix PreMix',
            '--era Run2_2017',
            '--customise Configuration/DataProcessing/Utils.addMonitoring',
            '--python_filename {0}'.format(self.cfg_file_basename),
            '--no_exec',
            '-n {0}'.format(self.n_events),
            ]


#____________________________________________________________________
class FullSimRunnerAODstep2(FullSimRunner):
    stage = 'aod'
    substage = 'AOD_step2'
    @classmethod
    def subclass_per_year(cls):
        return {
        # 2016: FullSimRunnerAODstep22016,
        2017: FullSimRunnerAODstep22017,
        # 2018: FullSimRunnerAODstep22018,
        }

class FullSimRunnerAODstep22017(FullSimRunnerAODstep2):
    def get_cmsdriver_cmd(self):
        return [
            'cmsDriver.py step2',
            '--filein file:{0}'.format(self.in_file),
            '--fileout file:{0}'.format(self.out_root_file),
            '--mc',
            '--eventcontent AODSIM',
            '--runUnscheduled',
            '--datatier AODSIM',
            '--conditions 94X_mc2017_realistic_v11',
            '--step RAW2DIGI,RECO,RECOSIM,EI',
            '--era Run2_2017',
            '--customise Configuration/DataProcessing/Utils.addMonitoring',
            '--python_filename {0}'.format(self.cfg_file_basename),
            '--no_exec',
            '-n {0}'.format(self.n_events),
            ]


#____________________________________________________________________
class FullSimRunnerMiniAOD(FullSimRunner):
    stage = 'aod'
    substage = 'MiniAOD'
    @classmethod
    def subclass_per_year(cls):
        return {
        # 2016: FullSimRunnerMiniAOD2016,
        2017: FullSimRunnerMiniAOD2017,
        # 2018: FullSimRunnerMiniAOD2018,
        }

class FullSimRunnerMiniAOD2017(FullSimRunnerMiniAOD):
    def get_cmsdriver_cmd(self):
        return [
            'cmsDriver.py',
            '--filein file:{0}'.format(self.in_file),
            '--fileout file:{0}'.format(self.out_root_file_basename),
            '--mc',
            '--eventcontent MINIAODSIM',
            '--runUnscheduled',
            '--datatier MINIAODSIM',
            '--conditions 94X_mc2017_realistic_v14',
            '--step PAT',
            '--scenario pp',
            '--era Run2_2017,run2_miniAOD_94XFall17',
            '--customise Configuration/DataProcessing/Utils.addMonitoring',
            '--python_filename {0}'.format(self.cfg_file_basename),
            '--no_exec',
            '-n {0}'.format(self.n_events),
            ]


#____________________________________________________________________
class FullSimRunnerNanoAOD(FullSimRunner):
    stage = 'nano'
    substage = 'NanoAOD'
    @classmethod
    def subclass_per_year(cls):
        return {
        # 2016: FullSimRunnerNanoAOD2016,
        2017: FullSimRunnerNanoAOD2017,
        # 2018: FullSimRunnerNanoAOD2018,
        }

class FullSimRunnerNanoAOD2017(FullSimRunnerNanoAOD):
    def get_cmsdriver_cmd(self):
        return [
            'cmsDriver.py',
            '--filein file:{0}'.format(self.in_file),
            '--fileout file:{0}'.format(self.out_root_file_basename),
            '--mc',
            '--eventcontent NANOAODSIM',
            '--datatier NANOAODSIM',
            '--conditions 102X_mc2017_realistic_v7',
            '--step NANO',
            '--era Run2_2017,run2_nanoAOD_94XMiniAODv2',
            '--customise Configuration/DataProcessing/Utils.addMonitoring',
            '--python_filename {0}'.format(self.cfg_file_basename),
            '--no_exec',
            '-n {0}'.format(self.n_events),
            ]


