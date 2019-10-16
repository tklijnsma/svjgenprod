#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os.path as osp
import logging

import svjgenprod
from .mass_runner import MassRunner

logger = logging.getLogger('root')


#____________________________________________________________________
class GenSimFragment(object):
    """docstring for GenSimFragment"""

    @classmethod
    def from_yaml(cls, yaml_file):
        config = svjgenprod.Config.from_yaml(yaml_file)
        return cls(config)

    @classmethod
    def from_file(cls, file):
        config = svjgenprod.Config.from_file(file)
        return cls(config)

    def __init__(self, config):
        super(GenSimFragment, self).__init__()
        config.basic_checks()
        self.config = config
        self.set_class_vars()        

        # Probably not in init
        self.set_dark_params()
        self.get_lambda_d()
        self.get_xsec()
        self.get_pythia_info()


    def set_class_vars(self):
        # self.model_name = self.config['model_name']
        self.m_med = self.config['m_med']
        self.m_d = self.config['m_d']
        self.n_f = self.config['n_f']
        self.r_inv = self.config['r_inv']
        self.alpha_d = self.config['alpha_d']
        self.process_type = self.config['process_type']
        self.year = self.config['year']


    def set_dark_params(self):
        self.n_c = 2
        self.m_dark_meson = 2 * self.m_d
        # Calculate mass of stable dark matter particles
        self.m_dark_stable = self.m_d - 0.1


    def get_lambda_d(self):
        """ Calculate Lambda_d (confinement scale) """
        if isinstance(self.alpha_d, str):
            _Lambda_d = svjgenprod.cdp.calc_lambda_d_from_str(self.n_c, self.n_f, self.alpha_d, self.m_dark_meson)
        else:
            _Lambda_d = svjgenprod.cdp.calc_lambda_d(self.n_c, self.n_f, self.alpha_d)
        self.Lambda_d = round(_Lambda_d, 4)
        logger.info('Confinement scale Lambda_d = {0}'.format(self.Lambda_d))

        # Rescale Lambda_d if too low (should be >= m_d), then recalc alpha_d
        #if Lambda_d < m_d:
        #    Lambda_d = 1.1 * m_d
        #    alpha_d = svjgenprod.cdp.calc_alpha_d(n_c, n_f, Lambda_d)
        #    print(Fore.MAGENTA + "Recalculated alpha_d =", alpha_d)


    def get_xsec(self):
        if self.process_type.startswith('s'):
            self.x_sec = svjgenprod.utils.crosssection_from_file(
                osp.join(svjgenprod.SVJ_INPUT_DIR, 'xsecs_s-channel.txt'),
                self.m_med
                )
        else:
            raise NotImplementedError


    def get_pythia_info(self):
        if self.year == 2016:
            self.tune_module = 'Pythia8CUEP8M1Settings_cfi'
            self.tune_block = 'pythia8CUEP8M1SettingsBlock'
            self.pythia_settings = 'pythia8CUEP8M1Settings'
        else:
            self.tune_module = 'MCTunes2017.PythiaCP5Settings_cfi'
            self.tune_block = 'pythia8CP5SettingsBlock'
            self.pythia_settings = 'pythia8CP5Settings'


    def to_file(self, out):
        fragment = self.compile_fragment()
        if osp.isfile(out): logger.warning('Overwriting {0}'.format(out))
        with open(out, 'w') as f:
            f.write(fragment)


    def compile_fragment(self):
        fragment = []

        header = (
            "import FWCore.ParameterSet.Config as cms\n"
            "from Configuration.Generator.Pythia8CommonSettings_cfi import *\n"
            "from Configuration.Generator.{tune_module} import *\n"
            "from Configuration.Generator.Pythia8aMCatNLOSettings_cfi import *\n"
            "generator = cms.EDFilter('Pythia8HadronizerFilter',\n"
            "    maxEventsToPrint = cms.untracked.int32(1),\n"
            "    pythiaPylistVerbosity = cms.untracked.int32(1),\n"
            "    filterEfficiency = cms.untracked.double(1.0),\n"
            "    pythiaHepMCVerbosity = cms.untracked.bool(False),\n"
            "    crossSection = cms.untracked.double({cross_section:f}),\n"
            "    comEnergy = cms.double(13000.),\n"
            "    PythiaParameters = cms.PSet(\n"
            "        pythia8CommonSettingsBlock,\n"
            "        {tune_block},\n"
            "        pythia8aMCatNLOSettingsBlock,\n"
            "        JetMatchingParameters = cms.vstring(\n"
            "            'JetMatching:setMad = off', # if 'on', merging parameters are set according to LHE file\n"
            "            'JetMatching:scheme = 1', # 1 = scheme inspired by Madgraph matching code\n"
            "            'JetMatching:merge = on', # master switch to activate parton-jet matching. when off, all external events accepted\n"
            "            'JetMatching:jetAlgorithm = 2', # 2 = SlowJet clustering\n"
            "            'JetMatching:etaJetMax = 5.', # max eta of any jet\n"
            "            'JetMatching:coneRadius = 1.0', # gives the jet R parameter\n"
            "            'JetMatching:slowJetPower = 1', # -1 = anti-kT algo, 1 = kT algo. Only kT w/ SlowJet is supported for MadGraph-style matching\n"
            "            'JetMatching:qCut = 125.', # this is the actual merging scale. should be roughly equal to xqcut in MadGraph\n"
            "            'JetMatching:nJetMax = 2', # number of partons in born matrix element for highest multiplicity\n"
            "            'JetMatching:doShowerKt = off', # off for MLM matching, turn on for shower-kT matching\n"
            "            ),\n"
            .format(
                cross_section = self.x_sec,
                tune_block = self.tune_block,
                tune_module = self.tune_module
                )
            )
        fragment.append(header)

        fragment.append(
            "        processParameters = cms.vstring(\n"
            )

        if self.process_type.startswith('s'):
            fragment.append(
                "            '4900023:m0 = {}', # explicitly stating Z' mass in case it's not picked up properly by Pythia\n"
                "            '4900023:oneChannel = 1 0.982 102 4900101 -4900101', # explicitly stating Z' to dark quarks in case it's not picked up properly by Pythia\n"
                "            '4900023:addChannel = 1 0.003 102 1 -1', # including small branching ratios to SM quarks for realism\n"
                "            '4900023:addChannel = 1 0.003 102 2 -2',\n"
                "            '4900023:addChannel = 1 0.003 102 3 -3',\n"
                "            '4900023:addChannel = 1 0.003 102 4 -4',\n"
                "            '4900023:addChannel = 1 0.003 102 5 -5',\n"
                "            '4900023:addChannel = 1 0.003 102 6 -6',\n"
                .format(self.m_med)
                )
        else:
            raise NotImplementedError

        remain_br = self.remaining_br_democratic(5)
        fragment.append(
            "            '4900101:m0 = {m_dq}', # explicitly stating dark quark mass in case it's not picked up properly by Pythia\n"
            "            '4900113:m0 = {m_dmeson}', # Dark meson mass. PDGID corresponds to rhovDiag HV spin-1 meson that can decay into SM particles\n"
            "            '51:m0 = {m_dmatter}', # Stable dark particle mass. PDGID corresponds to spin-0 dark matter\n"
            "            '51:isResonance = false',\n"
            "            '4900113:oneChannel = 1 {r_inv} 51 -51', # Dark meson decay into stable dark particles with branching fraction r_inv\n"
            "            '4900113:addChannel = 1 {remain_br} 91 1 -1', # Dark meson decay into SM quarks\n"
            "            '4900113:addChannel = 1 {remain_br} 91 2 -2',\n"
            "            '4900113:addChannel = 1 {remain_br} 91 3 -3',\n"
            "            '4900113:addChannel = 1 {remain_br} 91 4 -4',\n"
            "            '4900113:addChannel = 1 {remain_br} 91 5 -5',\n"
            .format(
                m_dq = self.m_d,
                m_dmeson = self.m_dark_meson,
                m_dmatter = self.m_dark_stable,
                r_inv = self.r_inv,
                remain_br = remain_br
                )
            )

        fragment.append(self.get_extra_decays(self.n_f))

        fragment.append(
            "            'HiddenValley:probVector = {prob_vector}', # Ratio of number of vector mesons over scalar meson\n"
            # "            'HiddenValley:ffbar2Zv = on', # Production of f fbar -> Zv (4900023). It works only in the case of narrow width approx\n"
            "            'HiddenValley:fragment = on', # Enable hidden valley fragmentation\n"
            "            'HiddenValley:Ngauge = 2', # As dark sector is SU(2)\n"
            # "            'HiddenValley:spinFv = 0', # Spin of the HV partners of the SM fermions\n"
            "            'HiddenValley:FSR = on', # Enable final-state shower of HV gammav\n"
            # "            'HiddenValley:NBFlavRun = 0', # Number of bosonic flavor for running\n"
            # "            'HiddenValley:NFFlavRun = 2', # Number of fermionic flavor for running\n"
            "            'HiddenValley:alphaOrder = 1', # Order at which running coupling runs\n"
            "            'HiddenValley:Lambda = {Lambda_dark}', # Dark confinement scale\n"
            "            'HiddenValley:nFlav = {nFlav:.0f}', # This dictates what kind of hadrons come out of the shower. If nFlav = 2, for example, there will be many different flavor of hadrons\n"
            "            'HiddenValley:pTminFSR = {pTminFSR:.2f}', # Cut-off for the showering, should be roughly confinement scale\n"
            # "            'TimeShower:nPartonsInBorn = 2', # Number of coloured particles (before resonance decays) in born matrix element\n"
            "            ),\n"
            "        parameterSets = cms.vstring('pythia8CommonSettings',\n"
            "                                    '{pythia_settings}',\n"
            "                                    'pythia8aMCatNLOSettings',\n"
            "                                    'processParameters',\n"
            "                                    'JetMatchingParameters',\n"
            "                                    )\n"
            "        )\n"
            "    )\n"
            .format(
                prob_vector = 0.0 if self.n_f == 1 else 0.75,
                Lambda_dark = self.Lambda_d,
                nFlav = self.n_f,
                pTminFSR = 1.1*self.Lambda_d,
                pythia_settings = self.pythia_settings
                )
            )

        fragment.append(self.insert_filters())
        fragment = '\n'.join([ e.rstrip('\n') for e in fragment ]) + '\n'
        logger.debug('Finished fragment:\n{0}'.format(fragment))
        return fragment


    def get_quark_mass_dict(self):
        """ Return dictionary of quark rest masses """
        quark_masses = {  # PDGID: mass (GeV)
            1: 0.0048,    # down
            2: 0.0023,    # up
            3: 0.095,     # strange
            4: 1.275,     # charm
            5: 4.18,      # bottom
        }

        # Check if dark hadron mass > b quark. If so, all quarks are in the mix. Otherwise remove b from calculations
        if (self.m_dark_meson > quark_masses[5]):
            return quark_masses
        else:
            return {k: v for k, v in quark_masses.items() if k < 5}


    def remaining_br_democratic(self, n_quarks):
        """ Democratically allocate remaining BR (1 - r_inv)/n_quarks """
        # Can expand this in the future to take the running b- and c-quark masses into account
        return (1.0 - self.r_inv) / float(n_quarks)


    def remaining_br_mass_insertion(self, quark_id):
        """ Calculating running quark masses and use to calculate branching ratio """
        m_q_dict = self.get_quark_mass_dict()
        normaliser = sum([MassRunner(mass, len(m_q_dict), self.m_dark_meson, self.n_f).m_run ** 2 for mass in m_q_dict.values()])
        try:
            m_run = MassRunner(m_q_dict[quark_id], len(m_q_dict), self.m_dark_meson, self.n_f).m_run
            remain_br = (1.0 - self.r_inv) * (m_run ** 2) / normaliser
        except KeyError:  # i.e., if m_dark_meson < b quark
            remain_br = 0
        return remain_br


    def get_extra_decays(self, n_f):
        """ Compile string to include extra dark mesons and their decays, depending on value of n_f """
        if n_f == 2:
            ret = (
                "            '4900111:m0 = {m_dmeson}', # Dark meson mass. PDGID corresponds to pivDiag HV spin-0 meson that can decay into SM particles\n"
                "            '4900211:m0 = {m_dmeson}', # Dark meson mass. PDGID corresponds to pivUp HV spin-0 meson that is stable and invisible by default\n"
                "            '4900213:m0 = {m_dmeson}', # Dark meson mass. PDGID corresponds to rhovUp HV spin-1 meson that is stable and invisible by default\n"
                "            '53:m0 = {m_dmatter}', # Stable dark particle mass. PDGID corresponds to spin-1 dark matter\n"
                "            '53:isResonance = false',\n"
                "            '4900111:oneChannel = 1 {r_inv} 0 51 -51',\n"
                "            '4900111:addChannel = 1 {remain_BR_c:.5f} 91 4 -4', # Dark meson decay into c quarks with BR set by running mass\n"
                "            '4900111:addChannel = 1 {remain_BR_b:.5f} 91 5 -5', # Dark meson decay into b quarks with BR set by running mass\n"
                "            '4900211:oneChannel = 1 {r_inv} 0 51 -51',\n"
                "            '4900211:addChannel = 1 {remain_BR_c:.5f} 91 4 -4',\n"
                "            '4900211:addChannel = 1 {remain_BR_b:.5f} 91 5 -5',\n"
                "            '4900213:oneChannel = 1 {r_inv} 0 53 -53', # Dark meson decay into stable dark particles with branching fraction r_inv\n"
                "            '4900213:addChannel = 1 {remain_BR_democ} 91 1 -1',\n"
                "            '4900213:addChannel = 1 {remain_BR_democ} 91 2 -2',\n"
                "            '4900213:addChannel = 1 {remain_BR_democ} 91 3 -3',\n"
                "            '4900213:addChannel = 1 {remain_BR_democ} 91 4 -4',\n"
                "            '4900213:addChannel = 1 {remain_BR_democ} 91 5 -5',\n"
                .format(
                    m_dmeson = self.m_dark_meson,
                    m_dmatter = self.m_dark_stable,
                    r_inv = self.r_inv,
                    remain_BR_democ = self.remaining_br_democratic(5),
                    remain_BR_c = self.remaining_br_mass_insertion(quark_id=4),
                    remain_BR_b=self.remaining_br_mass_insertion(quark_id=5)
                    )
                )
        elif n_f == 1:
            ret = ""
        else:
            raise ValueError("The value of n_f = {} specified is not allowed. Please choose either n_f = 1 or n_f = 2".format(n_f))

        logger.info("Extra decays added to gen fragment")
        return ret


    def insert_filters(self):
        """ Include Z2 symmmetry filter (enforce pair production of stable dark particles)
        and dark quark filter (reject events where Z' decays directly to SM particles) """
        ret = (
            "darkhadronZ2filter = cms.EDFilter('MCParticleModuloFilter',\n"
            "    moduleLabel = cms.InputTag('generator'{smear}),\n"
            "    absID = cms.bool(True),\n"
            "    multipleOf = cms.uint32({two_n_dmatter:.0f}),  # 2x number of stable dark particles\n"
            "    particleIDs = cms.vint32(51{extra_dmatter}),  # PDGIDs of stable dark particles\n"
            "    )\n"
            "darkquarkFilter = cms.EDFilter('MCParticleModuloFilter',\n"
            "    status = cms.int32(23),\n"
            "    min = cms.uint32(2),\n"
            "    moduleLabel = cms.InputTag('generator'{smear}),\n"
            "    absID = cms.bool(True),\n"
            "    multipleOf = cms.uint32(2),\n"
            "    particleIDs = cms.vint32(4900101),  # PDGID of dark quark\n"
            "    )\n"
            .format(
                two_n_dmatter=2*self.n_f,
                extra_dmatter=', 53' if self.n_f == 2 else '',
                smear='' if self.year == 2016 else ', "unsmeared"'
                )
            )
        logger.info("Extra filters added to gen fragment")
        return ret

