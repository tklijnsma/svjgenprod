#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os.path as osp
import logging, os, collections
from time import strftime
import svjgenprod
logger = logging.getLogger('root')


class JDLBase(object):
    """docstring for JDLBase"""

    default_scram_arch = 'slc7_amd64_gcc493'

    def __init__(self):
        super(JDLBase, self).__init__()
        self.environment = {
            'SCRAM_ARCH': self.default_scram_arch,
            'CONDOR_CLUSTER_NUMBER' : '$(Cluster)',
            'CONDOR_PROCESS_ID' : '$(Process)',
            'USER' : os.environ['USER'],
            'CLUSTER_SUBMISSION_TIMESTAMP' : strftime('%Y%m%d_%H%M%S'),
            'CLUSTER_SUBMISSION_TIMESTAMP_SHORT' : strftime('%Y-%m-%d'),
            'CLUSTER_SUBMISSION_TIMESTAMP_VERBOSE' : strftime('%b %d %H:%M:%S (%Y)'),
            }
        self.options = collections.OrderedDict()
        self.options['universe'] = 'vanilla'
        self.options['environment'] = self.environment
        self.queue = 'queue'

    def to_file(self, file, dry=False):
        parsed = self.parse()
        logger.info('Writing to {0}'.format(file))
        if not dry:
            with open(file, 'w') as f:
                f.write(parsed)

    def parse(self):
        self.subparse()
        jdl = []
        for key, value in self.options.iteritems():
            if key == 'environment':
                jdl.append('environment = "{0}"'.format(self.parse_environment()))
            else:
                jdl.append('{0} = {1}'.format(key, value))
        jdl.append(self.queue)
        jdl = '\n'.join(jdl)
        logger.info('Parsed the following jdl file:\n{0}'.format(jdl))
        return jdl


    def parse_environment(self):
        env_str = [ '{0}=\'{1}\''.format(key, value) for key, value in self.environment.iteritems() ]
        return ' '.join(env_str)



class JDLStandard(JDLBase):
    """docstring for JDLStandard"""

    starting_seed = 1001

    def __init__(self,
        sh_file,
        python_file,
        n_jobs,
        n_events_per_job,
        infiles = None,
        ):
        super(JDLStandard, self).__init__()

        self.sh_file = osp.basename(sh_file)
        self.python_file = osp.abspath(python_file)
        self.n_jobs = n_jobs
        self.n_events_per_job = n_events_per_job
        self.environment['SVJ_NEVENTS'] = n_events_per_job
        self.environment['SVJ_BATCH_MODE'] = 'lpc'

        if type(infiles) == str:
            self.infiles = [ f.strip() for f in infiles.split(',') ]
        elif infiles is None:
            self.infiles = []
        else:
            self.infiles = infiles


    def subparse(self):
        self.options['executable'] = self.sh_file

        self.options['should_transfer_files'] = 'YES'  # May not be needed if staging out to SE!
        self.options['when_to_transfer_output'] = 'ON_EXIT'
        self.options['transfer_output_files'] = 'output'  # Should match with what is defined in svjgenprod.SVJ_OUTPUT_DIR
        self.options['on_exit_hold'] = '(ExitBySignal == True) || (ExitCode != 0)' # Hold job on failure

        self.parse_infiles()

        python_basename = osp.basename(self.python_file).replace('.py', '')
        self.options['output'] = '{0}_$(Cluster)_$(Process).stdout'.format(python_basename)
        self.options['error']  = '{0}_$(Cluster)_$(Process).stderr'.format(python_basename)
        self.options['log']    = '{0}_$(Cluster)_$(Process).log'.format(python_basename)

        # Queue one job per seed
        seeds = [ str(self.starting_seed + i) for i in range(self.n_jobs) ]
        self.queue = 'queue 1 arguments in {0}'.format(', '.join(seeds))


    def parse_infiles(self):
        transfer_input_files = [self.python_file]
        svj_infiles = []
        for file in self.infiles:
            if file.startswith('root:'):
                # SE files do not need to be transferred
                svj_infiles.append(file)
            else:
                transfer_input_files.append(osp.abspath(file))
                svj_infiles.append(osp.basename(file))

        if len(svj_infiles) > 0:
            self.environment['SVJ_INFILES'] = ','.join(svj_infiles)
        if len(transfer_input_files) > 0:
            self.options['transfer_input_files'] = ','.join(transfer_input_files)



# universe = vanilla
# executable = sleep.sh
# should_transfer_files = YES
# when_to_transfer_output = ON_EXIT
# input = inputtext.txt
# output = sleep_$(Cluster)_$(Process).stdout
# error = sleep_$(Cluster)_$(Process).stderr
# log = sleep_$(Cluster)_$(Process).log

# queue 1 arguments in 1001, 1002, 1003
