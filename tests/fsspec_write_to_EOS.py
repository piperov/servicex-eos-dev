import fsspec
import uproot

# Instantiate the XRootD protocol client
fs = fsspec.filesystem("root", hostid="eos.cms.rcac.purdue.edu")
# fs = fsspec.filesystem("root", asynchronous=False, hostid="eos.cms.rcac.purdue.edu")

local_path = "my-local-result.root"
remote_path = "/store/user/piperov/test-remote-upload.root"

# Create the file locally using uproot
with uproot.recreate(local_path) as f:
    f["tree"] = {"branch": [1, 2, 3, 4]}

# Upload the file cleanly
## fs.put(local_path, remote_path)
# Replace fs.put(local_path, remote_path) with:
with open(local_path, 'rb') as f_in:
    with fs.open(remote_path, 'wb') as f_out:
        f_out.write(f_in.read())

