#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os.path as osp
import logging, subprocess, os, shutil, re, pprint, csv
import svjgenprod

logger = logging.getLogger('root')


def split_mgm(filename):
    if not filename.startswith('root://'):
        raise ValueError(
            'Cannot split mgm; passed filename: {0}'
            .format(filename)
            )
    elif not '/store' in filename:
        raise ValueError(
            'No substring \'/store\' in filename {0}'
            .format(filename)
            )
    i = filename.index('/store')
    mgm = filename[:i]
    lfn = filename[i:]
    return mgm, lfn


class SEManager(object):
    """docstring for SEManager"""
    def __init__(self, mgm='root://cmseos.fnal.gov'):
        super(SEManager, self).__init__()
        self.mgm = mgm

    def _safe_split_mgm(self, path, mgm=None):
        """
        Returns the mgm and lfn that the user most likely intended to
        if path starts with 'root://', the mgm is taken from the path
        if mgm is passed, it is used as is
        if mgm is None and path has no mgm, the class var is taken
        """
        if path.startswith('root://'):
            _mgm, lfn = split_mgm(path)
            if not(mgm is None) and not _mgm == mgm:
                raise ValueError(
                    'Conflicting mgms determined from path and passed argument: '
                    'From path {0}: {1}, from argument: {2}'
                    .format(path, _mgm, mgm)
                    )
            mgm = _mgm
        elif mgm is None:
            mgm = self.mgm
            lfn = path
        else:
            lfn = path
        # Some checks
        if not mgm == self.mgm:
            logger.warning(
                'Using mgm {0}, which is not the class mgm {1}'
                .format(mgm, self.mgm)
                )
        if not lfn.startswith('/store'):
            raise ValueError(
                'LFN {0} does not start with \'/store\'; something is wrong'
                .format(lfn)
                )
        return mgm, lfn

    def _join_mgm_lfn(self, mgm, lfn):
        """
        Joins mgm and lfn, ensures correct formatting
        """
        if not mgm.endswith('/'): mgm += '/'
        return mgm + lfn

    def create_directory(self, directory):
        """
        Creates a directory on the SE
        Does not check if directory already exists
        """
        mgm, directory = self._safe_split_mgm(directory)
        logger.warning('Creating directory on SE: {0}'.format(self._join_mgm_lfn(mgm, directory)))
        cmd = [ 'xrdfs', mgm, 'mkdir', '-p', directory ]
        svjgenprod.utils.run_command(cmd)

    def is_directory(self, directory):
        """
        Returns a boolean indicating whether the directory exists
        """
        mgm, directory = self._safe_split_mgm(directory)
        cmd = [ 'xrdfs', mgm, 'stat', '-q', 'IsDir', directory ]
        status = (subprocess.check_output(cmd) == 0)
        if not status:
            logger.info('Directory {0} does not exist'.format(self._join_mgm_lfn(mgm, directory)))
        return status

    def copy_to_se(self, src, dst, create_parent_directory=True):
        """
        Copies a file `src` to the storage element
        """
        mgm, dst = self._safe_split_mgm(dst)
        dst = self._join_mgm_lfn(mgm, dst)
        if create_parent_directory:
            parent_directory = osp.dirname(dst)
            self.create_directory(parent_directory)
        logger.warning('Copying {0} to {1}'.format(src, dst))
        cmd = [ 'xrdcp', '-s', src, dst ]
        svjgenprod.utils.run_command(cmd)

