import fsspec

# Purdue CMS EOS file path
file_url = "root://eos.cms.rcac.purdue.edu//store/user/piperov/test-remote.root"

# Open the remote ROOT file via fsspec
with fsspec.open(file_url, "rb") as open_file:
    # Read the first 100 bytes as a quick test
    header_sample = open_file.read(100) 
    print(f"Successfully connected! File header sample: {header_sample}")

import uproot

with fsspec.open(file_url, "rb") as open_file:
    with uproot.open(open_file) as tree:
        print(tree.keys())  # Lists the objects inside the file
