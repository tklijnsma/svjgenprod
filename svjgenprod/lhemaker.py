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
            config,
            tarball,
            n_events,
            seed = svjgenprod.SVJ_SEED,
            process_type = None,
            ):
        super(LHEMaker, self).__init__()

        self.config = svjgenprod.Config.flexible_init(config)
        self.tarball = tarball
        self.n_events = n_events
        self.seed = seed
        self.model_name = svjgenprod.utils.get_model_name_from_tarball(tarball)
        self.process_type = self.get_process_type() if process_type is None else process_type

        self.run_gridpack_dir = svjgenprod.RUN_GRIDPACK_DIR

        self.log_file = osp.join(osp.dirname(self.tarball), self.model_name + '.log')
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
        with svjgenprod.utils.switchdir(extracted_tarball):
            cmd = [ 'bash', 'runcmsgrid.sh', str(self.n_events), str(self.seed) ]
            svjgenprod.utils.run_command(cmd)
        self.out_lhe_file = osp.join(extracted_tarball, 'cmsgrid_final.lhe')
        self.replace_pids(self.out_lhe_file)

    def replace_pids(self, lhe_file):
        logger.info('Going to replace pids. Opening {0} and reading contents'.format(lhe_file))
        with open(lhe_file, 'r') as f:
            contents = f.read()
        def replace(contents, src, dst):
            logger.info('Replacing "{0}" ==> "{1}"'.format(src, dst))
            return contents.replace(src, dst)
        if self.config['process_type'].startswith('s'):
            contents = replace(contents, '5000521', '4900101')
        else:
            raise NotImplementedError
        logger.warning('Overwriting {0} with replacements'.format(lhe_file))
        with open(lhe_file, 'w') as f:
            f.write(contents)

    def _get_dst(self, output_dir, dry):
        """
        Makes an output directory if not yet existing and comes up with
        a better file name for the just-created .lhe file
        """
        if output_dir is None: output_dir = svjgenprod.SVJ_OUTPUT_DIR
        svjgenprod.utils.create_directory(output_dir, dry=dry)
        dst = osp.join(
            output_dir,
            'lhe_{0}_N{1}_seed{2}.lhe'.format(self.model_name, self.n_events, self.seed)
            )
        return dst

    def copy_to_output(self, output_dir=None, dry=False):
        dst = self._get_dst(output_dir, dry)
        logger.info('Copying {0} ==> {1}'.format(self.out_lhe_file, dst))
        if not dry: shutil.copyfile(self.out_lhe_file, dst)

    def move_to_output(self, output_dir=None, dry=False):
        dst = self._get_dst(output_dir, dry)
        logger.info('Moving {0} ==> {1}'.format(self.out_lhe_file, dst))
        if not dry: shutil.move(self.out_lhe_file, dst)

