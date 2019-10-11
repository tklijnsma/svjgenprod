#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import yaml, logging, pprint
logger = logging.getLogger('root')


class Config(dict):
    """docstring for Config"""

    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)
        logger.debug('Initialized config with parameters:\n{0}'.format(pprint.pformat(kwargs)))
        
    @classmethod
    def from_yaml(cls, yaml_file):
        logger.info('Initializing from .yaml file {0}'.format(yaml_file))
        confdict = yaml.full_load(open(yaml_file, 'r'))
        inst = cls(**confdict)
        inst.yaml_file = yaml_file
        return inst

    def basic_checks(self):
        m_med = self.get('m_med')
        m_d = self.get('m_d')

        try:
            assert type(self.get('n_events')) is int
            assert type(self.get('n_jobs')) is int
            assert type(m_med) is int
            assert type(m_d) is int

            assert m_med > 0
            assert m_d > 0

            assert m_med > 2*m_d, 'm_med > 2*m_d necessary for on-shell pair production of the dark quarks.'

            assert self.get('process_type') in ['s-channel', 't-channel']

            assert self.get('r_inv') > 0.
            assert self.get('r_inv') < 1.

            assert self.get('year') in [ 2016, 2017, 2018 ]

        except AssertionError:
            logger.error('Encountered problem with basic checks of the config')
            logger.error('Contents: {0}'.format(self))
            raise


    def get_model_name(self):
        channel = self['process_type'][0]
        if channel == 's':
            med_type = 'Zp'
        elif channel == 't':
            med_type = 'Phi'
        else:
            raise NotImplementedError(
                'Channel {0} not implemented'.format(channel)
                )

        model_name = 'SVJ_{channel}_{year}_m{med}{m_med}_mDQ{m_d}_rinv{rinv}_aD{alphad}'.format(
            rinv   = str(self['r_inv']).replace('.', 'p'),
            alphad = str(self['alpha_d']).replace('.', 'p'),
            channel = self['process_type'][0],
            med    = med_type,
            year   = self['year'],
            m_med  = self['m_med'],
            m_d    = self['m_d'],
            )
        return model_name
