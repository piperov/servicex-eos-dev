import sys
import os
sys.path.append("/home/piperov/work/ServiceX/transformer_sidecar/src")

# Configure environment variables for EOS mode
os.environ["OBJECT_STORE_TYPE"] = "eos"
os.environ["EOS_HOST"] = "eos.cms.rcac.purdue.edu"
os.environ["EOS_PATH_PREFIX"] = "/store/user/piperov"

from transformer_sidecar.object_store_manager import ObjectStoreManager

# 1. Create a dummy file locally
local_file = "osm-eos-test.root"
with open(local_file, "w") as f:
    f.write("dummy root file content for integration test")

print("Created local dummy file.")

# 2. Instantiate ObjectStoreManager
manager = ObjectStoreManager()

# 3. Try to upload the file to Purdue EOS
# bucket name: test-bucket-osm
# object name: test-eos-file.root
try:
    print("Uploading file to Purdue's EOS via ObjectStoreManager...")
    manager.upload_file("test-bucket-osm", "test-eos-file.root", local_file)
    print("Upload succeeded!")
except Exception as e:
    print(f"Upload failed: {e}")
