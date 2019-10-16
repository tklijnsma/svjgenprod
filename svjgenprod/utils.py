#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os.path as osp
import logging, subprocess, os, shutil, re, pprint
import numpy as np
from .termcolor import colored
import svjgenprod

logger = logging.getLogger('root')
subprocess_logger = logging.getLogger('subprocess')


class switchdir(object):
    """
    Temporarily changes the working directory
    """
    def __init__(self, newdir, dry=False):
        super(switchdir, self).__init__()
        self.newdir = newdir
        self._backdir = os.getcwd()
        self.dry = dry
        
    def __enter__(self):
        logger.info('chdir to {0}'.format(self.newdir))
        if not self.dry: os.chdir(self.newdir)

    def __exit__(self, type, value, traceback):
        logger.info('chdir back to {0}'.format(self._backdir))
        if not self.dry: os.chdir(self._backdir)


def run_command(cmd, env=None, dry=False, shell=False):
    logger.warning('Issuing command: {0}'.format(' '.join(cmd)))
    if dry: return

    if shell:
        cmd = ' '.join(cmd)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        universal_newlines=True,
        shell=shell
        )

    for stdout_line in iter(process.stdout.readline, ""):
        subprocess_logger.info(stdout_line.rstrip('\n'))
        # print(colored('[subprocess] ', 'red') + stdout_line, end='')
    process.stdout.close()
    process.wait()
    returncode = process.returncode

    if (returncode == 0):
        logger.info('Command exited with status 0 - all good')
    else:
        raise subprocess.CalledProcessError(cmd, returncode)


def run_multiple_commands(cmds, env=None):
    if dry:
        logger.info('Sending:\n{0}'.format(pprint.pformat(cmds)))
        return

    process = subprocess.Popen(
        'bash',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        # universal_newlines=True,
        bufsize=1,
        close_fds=True
        )

    # Break on first error (stdin will still be written but execution will be stopped)
    process.stdin.write('set -e\n')
    process.stdin.flush()

    for cmd in cmds:
        if not(type(cmd) is str):
            cmd = ' '.join(cmd)
        if not(cmd.endswith('\n')):
            cmd += '\n'
        logger.warning('Sending cmd \'{0}\''.format(cmd.replace('\n', '\\n')))
        process.stdin.write(cmd)
        process.stdin.flush()
    process.stdin.close()

    process.stdout.flush()
    for line in iter(process.stdout.readline, ""):
        if len(line) == 0: break
        # print(colored('[subprocess] ', 'red') + line, end='')
        subprocess_logger.info(line.rstrip('\n'))

    process.stdout.close()
    process.wait()
    returncode = process.returncode

    if (returncode == 0):
        logger.info('Command exited with status 0 - all good')
    else:
        raise subprocess.CalledProcessError(cmd, returncode)


def create_directory(dir, force=False, dry=False, must_not_exist=False):
    newly_created = False

    def create():
        logger.warning('Creating {0}'.format(dir))
        if not dry: os.makedirs(dir)

    def delete():
        logger.warning('Removing dir {0}'.format(dir))
        if not dry: shutil.rmtree(dir)

    if osp.isdir(dir):
        if force:
            delete()
            create()
            newly_created = True
        elif must_not_exist:
            raise OSError('{0} already exist but must not exist'.format(dir))
        else:
            logger.info('Already exists: {0}'.format(dir))
    else:
        create()
        newly_created = True

    return newly_created


def make_inode_unique(file):
    if not osp.exists(file): return file
    file += '_{i_attempt}'
    i_attempt = 1
    while osp.exists(file.format(i_attempt=i_attempt)):
        i_attempt += 1
        if i_attempt == 999:
            raise ValueError('Problem making unique directory/file (999 attempts): {0}'.format(file))
    return file.format(i_attempt=i_attempt)


def check_proxy():
    # cmd = 'voms-proxy-info -exists -valid 168:00' # Check if there is an existing proxy for a full week
    try:
        proxy_valid = subprocess.check_output(['grid-proxy-info', '-exists', '-valid', '168:00']) == 0
        logger.info('Found a valid proxy')
    except subprocess.CalledProcessError:
        logger.error(
            'Grid proxy is not valid for at least 1 week. Renew it using:\n'
            'voms-proxy-init -voms cms -valid 192:00'
            )
        raise


def crosssection_from_file(file, m_med):
    logger.debug('Loading xsec list from file {0}'.format(file))
    m_meds, crosssections = np.loadtxt(file).T
    index, = np.where(m_meds == m_med)
    if index == []:
        raise ValueError(
            'Could not find cross section for m_med = {0} in {1}'
            .format(m_med, file)
            )
    xs = crosssections[index[0]]
    logger.debug('Found xs = {0}'.format(xs))
    return xs


def get_model_name_from_tarball(tarball):
    match = re.search(r'(.*)_slc[67]', osp.basename(tarball))
    if not match:
        raise ValueError(
            'Could not determine model_name from {0}'
            .format(tarball)
            )
    model_name = match.group(1)
    logger.info('Retrieved model_name {0} from {1}'.format(model_name, tarball))
    return model_name


def setup_cmssw(workdir, version, arch):
    """
    Generic function to set up CMSSW in workdir
    """

    if osp.isdir(osp.join(workdir, version)):
        logger.info('{0} already exists, skipping'.format(version))
        return
    logger.info('Setting up {0} {1} in {2}'.format(version, arch, workdir))
    cmds = [
        'cd {0}'.format(workdir),
        'shopt -s expand_aliases',
        'source /cvmfs/cms.cern.ch/cmsset_default.sh',
        'export SCRAM_ARCH={0}'.format(arch),
        'cmsrel {0}'.format(version),
        'cd {0}/src'.format(version),
        'cmsenv',
        'scram b',
        ]
    run_multiple_commands(cmds)
    logger.info('Done setting up {0} {1} in {2}'.format(version, arch, workdir))


def compile_cmssw_src(cmssw_src, arch):
    """
    Generic function to (re)compile a CMSSW setup
    """
    if not osp.abspath(cmssw_src).endswith('src'):
        raise ValueError('cmssw_src {0} does not end with "src"'.format(cmssw_src))

    logger.info('Compiling {0} with scram arch {1}'.format(cmssw_src, arch))
    cmds = [
        'shopt -s expand_aliases',
        'source /cvmfs/cms.cern.ch/cmsset_default.sh',
        'export SCRAM_ARCH={0}'.format(arch),
        'cd {0}'.format(cmssw_src),
        'cmsenv',
        'scram b',
        ]
    run_multiple_commands(cmds)
    logger.info('Done compiling {0} with scram arch {1}'.format(cmssw_src, arch))


def compile_cmssw(workdir, version, arch):
    """
    As compile_cmssw_src but takes separated arguments
    """
    compile_cmssw_src(osp.join(workdir, version))


def remove_file(file):
    """
    Removes a file only if it exists, and logs
    """
    if osp.isfile(file):
        logger.warning('Removing {0}'.format(file))
        os.remove(file)
    else:
        logger.info('No file {0} to remove'.format(file))


def remove_dir(directory):
    """
    Removes a dir only if it exists, and logs
    """
    if osp.isdir(directory):
        logger.warning('Removing dir {0}'.format(directory))
        shutil.rmtree(directory)
    else:
        logger.info('No directory {0} to remove'.format(directory))


def tarball_head(outfile=None):
    """
    Creates a tarball of the latest commit
    """

    if outfile is None:
        outfile = osp.join(os.getcwd(), 'svjgenprod.tar')
    outfile = osp.abspath(outfile)

    with switchdir(osp.join(svjgenprod.SVJ_TOP_DIR, '..')):
        run_command(['git', 'archive', '-o', outfile, 'HEAD'])

