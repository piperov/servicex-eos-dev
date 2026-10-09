from servicex import deliver, query, dataset

import awkward as ak
import uproot
import vector
vector.register_awkward()
import hist

import matplotlib.pyplot as plt


# file = "root://eos.cms.rcac.purdue.edu:1094//store/mc/RunIII2024Summer24NanoAODv15/VBFH-Hto2Mu_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/100000/1d437865-3bfb-4d90-b596-c2f638d398f3.root"
file = "root://eos.cms.rcac.purdue.edu:1094//store/mc/RunIII2024Summer24NanoAODv15/VBFH-Hto2Mu_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2810000/0c56515d-beac-4c33-8e8f-f57b1ba027d1.root"

# other files of the same dataset
# 37009fc8-d8e9-4c29-9dfe-c87bea77af62.root
# 1d437865-3bfb-4d90-b596-c2f638d398f3.root
# fc959f78-5cbc-438c-9d36-6451d53c6f30.root
# f943a3a5-0619-4e0e-9282-b2a5fabe03f0.root
# f05fbcb1-50b6-4d4e-9923-19678675ee4a.root
# e880e7eb-ff47-4ca8-8ef8-4a82525672a5.root
# 2810000/02c62fa6-7e43-484f-af36-bfd1433083c3.root
# 2810000/05a93427-e353-4d81-8805-6d329c94b0c7.root
# 2810000/0c56515d-beac-4c33-8e8f-f57b1ba027d1.root

nanoaod_dataset = dataset.FileList([file])


uproot_raw_query = query.UprootRaw([{
        'treename':'Events',
        'filter_name':
            ["Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", 'Muon_mediumId', 'Muon_charge'],
        'cut': '(nMuon == 2) & all(Muon_mediumId & (Muon_pt > 20) & (abs(Muon_eta) < 2.4)) & (sum(Muon_charge) == 0)'
    }]
)


spec_uproot_raw = {
    'Sample': [{
        'Name': 'UprootRawExample',
        'Dataset': nanoaod_dataset,
        'Query': uproot_raw_query
    }]
}

results_uproot_raw=deliver(spec_uproot_raw)


# Read output file
skimmed_file = results_uproot_raw["UprootRawExample"][0]
with uproot.open(skimmed_file) as f:
    arrays = f["Events"].arrays()

# Compute dimuon mass
muons = ak.zip({
    'pt':   arrays['Muon_pt'],
    'eta':  arrays['Muon_eta'],
    'phi':  arrays['Muon_phi'],
    'mass': arrays['Muon_mass'],
}, with_name='Momentum4D')

dimuon_mass = (muons[:, 0] + muons[:, 1]).mass

# Plot dimuon mass
h = hist.Hist(hist.axis.Regular(50, 100, 150, label=r'$m_{\mu\mu}$ [GeV]'))
h.fill(dimuon_mass)

h.plot()
plt.title('Dimuon Invariant Mass')
plt.ylabel('Events')

plt.tight_layout()
plt.savefig('output.png')
print("Data successfully delivered by ServiceX!")
