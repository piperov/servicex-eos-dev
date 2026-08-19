from servicex import query, dataset, deliver
import servicex
import glob 
# file = "root://eos.cms.rcac.purdue.edu//store/user/IDAP/RunIISummer20UL16NanoAODv9/TTJets_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/20UL16JMENano_106X_mcRun2_asymptotic_v17-v1/50000/6317D9D2-DB6A-234C-BD51-5E54FC301BD2.root"
# file = "https://xrootd-local.unl.edu:1094//store/user/AGC/nanoAOD/TT_TuneCUETP8M1_13TeV-powheg-pythia8/cmsopendata2015_ttbar_19980_PU25nsData2015v1_76X_mcRun2_asymptotic_v12_ext3-v1_00000_0000.root"
file = "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/GluGluHToWWTo2L2Nu_M125_TuneCP5_13TeV_powheg2_JHUGenV714_pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v2/2520000/24089CF5-9E37-8242-8689-6AF3EC7D9B7F.root"
# file = "root://eos.cms.rcac.purdue.edu:1094//store/user/rasharma/customNanoAOD_GT36/UL2018/SingleMuon_Run2018C/003EFE78-9748-DC43-BB97-14236C25C5FA_NanoAOD.root"
# file2 = "root://eos.cms.rcac.purdue.edu:1094//store/user/rasharma/customNanoAOD_GT36/UL2018/SingleMuon_Run2018C/004F1C23-3CF3-924E-8483-220E7BA15ACE_NanoAOD.root"
# ds = "/eos/purdue/store/user/rasharma/customNanoAOD/UL2018/GluGluHToMuMu_M125_TuneCP5_13TeV-powheg-pythia8/*"
# filelist = glob.glob(ds)
# filelist = [f.replace("/eos/purdue", "root://xcache.cms.rcac.purdue.edu/") for f in filelist]

# eos_dataset = "root://eos.cms.rcac.purdue.edu:1094//store/user/rasharma/customNanoAOD_GT36/UL2018/SingleMuon_Run2018C/*"
# file = "root://eos.cms.rcac.purdue.edu:1094//store/user/rasharma/customNanoAOD_GT36/UL2018/SingleMuon_Run2018C/003EFE78-9748-DC43-BB97-14236C25C5FA_NanoAOD.root"


# print(filelist)

dset = dataset.FileList([file])
# dset = dataset.FileList(filelist)
# dset = dataset.XRootD(eos_dataset)

columns = [
    'run',
    'luminosityBlock',
    'event',
    'genWeight',

    "HLT_IsoMu24",
    "HLT_IsoTkMu24",
    "HLT_IsoMu27",

    "TrigObj_id",
    "TrigObj_filterBits",
    "TrigObj_pt",
    "TrigObj_eta",
    "TrigObj_phi",

    "nMuon",
    "Muon_bsConstrainedChi2",
    "Muon_bsConstrainedPt",
    "Muon_bsConstrainedPtErr",
    "Muon_charge",
    "Muon_eta",
    "Muon_phi",
    "Muon_isGlobal",
    "Muon_isTracker",
    "Muon_mediumId",
    "Muon_miniPFRelIso_all",
    "Muon_pt",
    "Muon_ptErr",
    "Muon_pfRelIso04_all",
    "Muon_fsrPhotonIdx",
    "Muon_genPartIdx",
    "Muon_matched_fsrPhoton_relIso03",
    "Muon_matched_fsrPhoton_dROverEt2",
    "Muon_matched_fsrPhoton_pt",
    "Muon_matched_fsrPhoton_eta",
    "Muon_mass",
#    "Muon_nTrackerLayers",
    
    "nJet",
    "Jet_eta",
    "Jet_phi",
    "Jet_jetId",
    "Jet_puId",
    "Jet_pt",
    "Jet_mass",
    "Jet_rawFactor",
    "Jet_btagDeepFlavB",
    "Jet_btagDeepB",
    "Jet_btagRobustParTAK4B",
    "Jet_btagPNetQvG",
    "Jet_genJetIdx",
    "Jet_matched_gen_pt",
    "Jet_muonIdx1",
    "Jet_muonIdx2",
    "Jet_chEmEF",
    "Jet_neEmEF",
    "Jet_jetId",
    "Jet_area",
    "Jet_partonFlavour",
    
    "fixedGridRhoFastjetAll",
    "Rho_fixedGridRhoFastjetAll",
    
    "MET_pt",
    "MET_sumEt",
    
    "Electron_pt",
    "Electron_eta",
    "Electron_mvaFall17V2Iso_WP90",
    "Electron_mvaIso_WP90",

    "nFsrPhoton",
    "FsrPhoton_mass",
    "FsrPhoton_pt",
    "FsrPhoton_eta",
    "FsrPhoton_phi",
    "FsrPhoton_relIso03",
    "FsrPhoton_dROverEt2",

    "PV_npvs",
    "PV_npvsGood",
    "Pileup_nTrueInt",

    "PuppiMET_pt",
    "PuppiMET_phi",
    "PuppiMET_sumEt",
    
    "SoftActivityJet_eta",
    "SoftActivityJet_phi",
    "SoftActivityJet_pt",
    "nSoftActivityJet",
    "SoftActivityJetHT",
    "SoftActivityJetHT10",
    "SoftActivityJetHT2",
    "SoftActivityJetHT5",
    "SoftActivityJetNjets10",
    "SoftActivityJetNjets2",
    "SoftActivityJetNjets5",
    
    "Flag_BadPFMuonFilter",
    "Flag_EcalDeadCellTriggerPrimitiveFilter",
    "Flag_HBHENoiseFilter",
    "Flag_HBHENoiseIsoFilter",
    "Flag_globalSuperTightHalo2016Filter",
    "Flag_goodVertices",
    "Flag_BadPFMuonDzFilter",  # UL addition
    "Flag_eeBadScFilter",
    "Flag_ecalBadCalibFilter",

    "LHEPart_eta",
    "LHEPart_incomingpz",
    "LHEPart_mass",
    "LHEPart_pdgId",
    "LHEPart_phi",
    "LHEPart_pt",
    "LHEPart_spin",
    "LHEPart_status",
    "nLHEPart",
    "GenPart_eta",
    "GenPart_genPartIdxMother",
    "GenPart_mass",
    "GenPart_pdgId",
    "GenPart_phi",
    "GenPart_pt",
    "GenPart_status",
    "GenPart_statusFlags",
    "nGenPart",
    "GenJet_eta",
    # "GenJet_hadronFlavour",
    "GenJet_mass",
    "GenJet_partonFlavour",
    "GenJet_phi",
    "GenJet_pt",
    "nGenJet",

    "HTXS_Higgs_pt",
    "HTXS_Higgs_y",
    "HTXS_njets25",
    "HTXS_njets30",

    "LHEScaleWeight",
    "nLHEScaleWeight",
    "LHEPdfWeight",
    "nLHEPdfWeight",
    "HTXS_stage1_1_cat_pTjet25GeV",
    "HTXS_stage1_1_cat_pTjet30GeV",
    "HTXS_stage1_1_cat_pTjet25GeV",
    "HTXS_stage1_1_cat_pTjet30GeV",
    "HTXS_stage1_1_fine_cat_pTjet25GeV",
    "HTXS_stage1_1_fine_cat_pTjet30GeV",
    "HTXS_stage1_2_cat_pTjet25GeV",
    "HTXS_stage1_2_cat_pTjet30GeV",
    "HTXS_stage1_2_fine_cat_pTjet25GeV",
    "HTXS_stage1_2_fine_cat_pTjet30GeV",
    "HTXS_stage_0",
    "HTXS_stage_1_pTjet25",
    "HTXS_stage_1_pTjet30",
]


spec = {
    'General': {
        'Delivery': 'URLs',
    },
    'Sample': [
        {
            'Name': 'query',
            'Dataset': dset,
            'Query': query.UprootRaw(
                [
                    {
                        "treename": "Events",
                        "filter_name": columns,
                        "fail_on_missing_trees": True
                    },
                    {
                        "treename": "LuminosityBlocks"
                    },
                    {
                        "treename": "Runs"
                    },
                ]
            ),
        },
    ],
}

files = deliver(spec, fail_if_incomplete=True, ignore_local_cache=True)
print(f"Files: {files}")
