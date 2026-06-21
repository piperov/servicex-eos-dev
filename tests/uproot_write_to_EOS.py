import uproot
from XRootD import client
from XRootD.client.flags import OpenFlags

# 1. Write the file locally
local_path = "output.root"
with uproot.recreate(local_path) as f:
    f["tree"] = {"branch": [1, 2, 3]}

# 2. Transfer via XRootD client
with client.File() as f_remote:
    # status, _ = f_remote.open("root://eos.cms.rcac.purdue.edu//store/user/piperov/test-remote.root", client.flags.OpenFlags.DELETE)
    status, _ = f_remote.open("root://eos.cms.rcac.purdue.edu//store/user/piperov/test-remote.root", OpenFlags.NEW | OpenFlags.UPDATE)
    if status.ok:
        with open(local_path, "rb") as f_local:
            f_remote.write(f_local.read())

