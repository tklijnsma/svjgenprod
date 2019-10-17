#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import logging, pprint
from ConfigParser import ConfigParser
logger = logging.getLogger('root')


class Config(dict):
    """docstring for Config"""

    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)
        logger.debug('Initialized config with parameters:\n{0}'.format(pprint.pformat(kwargs)))
        self.tags = []

    @classmethod
    def from_file(cls, config_file, section='default'):
        logger.info(
            'Initializing from config file {0}, section {1}'
            .format(config_file, section)
            )
        configp = ConfigParser()
        configp.read(config_file)
        config = dict(configp.items(section))
        # Unfortunately ConfigParser does not do typing
        config['year']         = configp[section].getint('year')
        config['alpha_d']      = configp[section].getfloat('alpha_d')
        config['m_med']        = configp[section].getint('m_med')
        config['m_d']          = configp[section].getint('m_d')
        config['n_f']          = configp[section].getint('n_f')
        config['r_inv']        = configp[section].getfloat('r_inv')
        return cls(**config)

    @classmethod
    def from_yaml(cls, yaml_file):
        logger.info('Initializing from .yaml file {0}'.format(yaml_file))
        try:
            import yaml
        except ImportError:
            logger.error(
                'PyYAML is not installed; install it with '
                '\'pip install PyYAML\', or use another initialization '
                'method.'
                )
            raise
        confdict = yaml.full_load(open(yaml_file, 'r'))
        inst = cls(**confdict)
        inst.yaml_file = yaml_file
        return inst

    @classmethod
    def flexible_init(cls, config):
        """
        Guaranteed to return a Config instance or throws an exception
        """
        if isinstance(config, Config):
            return config
        elif isinstance(config, dict):
            return cls(config)
        elif osp.isfile(config):
            if config.endswith('.yaml'):
                return cls.from_yaml(config)
            else:
                return cls.from_file(config)
        else:
            raise TypeError(
                'config parameter should be either a Config instance, '
                'a path to a .yaml file, or a path to a config file.'
                )

    def basic_checks(self):
        m_med = self.get('m_med')
        m_d = self.get('m_d')

        try:
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
            logger.error('Contents: {0}'.format(pprint.pformat(self)))
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
