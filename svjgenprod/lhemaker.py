#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os, shutil, sys, glob, subprocess, re, logging
import os.path as osp
from time import strftime

import svjgenprod

logger = logging.getLogger('root')

#____________________________________________________________________
class LHEMaker(object):
    """docstring for LHEMaker"""
    def __init__(self,
            tarball,
            process_type = None,
            total_events = 20,
            n_jobs = 2
            ):
        super(LHEMaker, self).__init__()

        self.tarball = tarball
        self.total_events = total_events
        self.model_name = svjgenprod.utils.get_model_name_from_tarball(tarball)
        self.process_type = self.get_process_type() if process_type is None else process_type

        self.run_gridpack_dir = svjgenprod.RUN_GRIDPACK_DIR
        self.lhe_outdir = svjgenprod.LHE_OUT

        self.log_file = osp.join(osp.dirname(self.tarball), self.model_name + '.log')
        self.xs = self.get_mg_cross_section()

        self.seed = svjgenprod.SVJ_SEED
        self.force_renew_tarball = True


    def get_process_type(self):
        match = re.match(r'\w+?_(\w)', osp.basename(self.tarball))
        if not match:
            raise ValueError(
                'Could not determine process_type from {0}'
                .format(self.tarball)
                )
        process_type = match.group(1)

        if process_type == 's' or process_type == 't':
            process_type += '-channel'
        else:
            raise ValueError('Cannot make process_type based on channel \'{0}\''.format(process_type))

        logger.info('Retrieved process_type {0} from {1}'.format(process_type, self.tarball))
        return process_type


    def get_mg_cross_section(self):
        """Gets the madgraph cross section from the log file that was created when creating the gridpack"""
        with open(self.log_file) as f:
            match = re.search(r'(?<=Cross-section :   )(\d*.\d+)', f.read())
            if not match:
                raise ValueError(
                    'Could not determine cross section from log_file {0}'.format(self.log_file)
                    )
        xs = match.group(1)
        logger.info('Found cross section {0} from log_file'.format(xs))
        return xs


    def extract_and_run_tarball(self):
        copied_tarball = osp.join(self.run_gridpack_dir, osp.basename(self.tarball))
        extracted_tarball = copied_tarball.replace('.tar.xz', '')
        self.copy_tarball(copied_tarball)
        self.extract_tarball(copied_tarball, dst = extracted_tarball)
        self.run_lhe_generation(extracted_tarball)
        self.move_lhe(osp.join(extracted_tarball, 'cmsgrid_final.lhe'))


    def copy_tarball(self, dst):
        def copy():
            logger.warning('Copying {0} ==> {1}'.format(self.tarball, dst))
            shutil.copyfile(self.tarball, dst)

        svjgenprod.utils.create_directory(osp.dirname(dst))

        if osp.isfile(dst):
            if self.force_renew_tarball:
                logger.warning('Removing previously existing {0}'.format(dst))
                os.remove(dst)
                copy()
            else:
                logger.warning('Not copying tarball; {0} already exists'.format(dst))
        else:
            copy()
        return dst


    def extract_tarball(self, tarball, dst=None):
        if not tarball.endswith('.tar.xz'):
            raise ValueError('Unexpected file extension for tarball {0}'.format(tarball))
        if dst is None: dst = tarball.replace('.tar.xz', '')

        newly_created = svjgenprod.utils.create_directory(dst, force=self.force_renew_tarball)
        if newly_created:
            logger.warning('Extracting tarball')
            cmd = [ 'tar', 'xf', tarball, '--directory', dst ]
            svjgenprod.utils.run_command(cmd)
            logger.info('Done extracting tarball')

        return dst


    def run_lhe_generation(self, extracted_tarball):
        if not osp.isfile(osp.join(extracted_tarball, 'runcmsgrid.sh')):
            raise RuntimeError(
                'File \'runcmsgrid.sh\' does not exist in {0}'
                .format(extracted_tarball)
                )

        _return_dir = os.getcwd()
        try:
            logger.info('Changing dir to {0}'.format(extracted_tarball))
            os.chdir(extracted_tarball)
            cmd = [ 'bash', 'runcmsgrid.sh', str(self.total_events), str(self.seed) ]
            svjgenprod.utils.run_command(cmd)

        except subprocess.CalledProcessError:
            logger.error('Error running cmd {0}'.format(' '.join(cmd)))
            raise

        finally:
            os.chdir(_return_dir)


    def create_new_lhe_dir(self, dry=False):
        outdir = osp.join(self.lhe_outdir, strftime('lhe-%y%m%d-%H%M-{0}'.format(self.model_name)))
        outdir = svjgenprod.utils.make_inode_unique(outdir)
        svjgenprod.utils.create_directory(outdir, must_not_exist=True, dry=dry)
        return outdir


    def move_lhe(self, lhe_file):
        if lhe_file is None: lhe_file = osp.join(extracted_tarball, 'cmsgrid_final.lhe')
        if not osp.isfile(lhe_file):
            logger.error('lhe_file does not exist: {0}'.format(lhe_file))
            return

        outdir = self.create_new_lhe_dir()
        dst = osp.join(outdir, 'lhe-N{0}.lhe'.format(self.total_events))
        dst = svjgenprod.utils.make_inode_unique(dst)

        logger.warning('Moving {0} ==> {1}'.format(lhe_file, dst))
        shutil.move(lhe_file, dst)
        
