import os
import sys
import uproot
import fsspec

# Ensure we can import transformer_sidecar
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../transformer_sidecar/src")))

from transformer_sidecar.object_store_manager import ObjectStoreManager

def main():
    print("=== End-to-End EOS Upload & Verification Test ===")
    
    # 1. Configuration
    eos_host = os.environ.get("EOS_HOST", "eos.cms.rcac.purdue.edu")
    path_prefix = os.environ.get("EOS_PATH_PREFIX", "/store/user/piperov")
    
    os.environ["OBJECT_STORE_TYPE"] = "eos"
    os.environ["EOS_HOST"] = eos_host
    os.environ["EOS_PATH_PREFIX"] = path_prefix
    
    local_file = "integration-test-local.root"
    remote_file_name = "integration-test-uploaded.root"
    bucket = "real-test-bucket"
    
    print(f"Target EOS Host: {eos_host}")
    print(f"Path Prefix: {path_prefix}")
    print(f"Local file: {local_file}")
    print(f"Target remote location: {path_prefix}/{bucket}/{remote_file_name}")
    
    # 2. Recreate a local ROOT file with dummy tree/branches
    print("\n1. Creating local ROOT file...")
    try:
        with uproot.recreate(local_file) as f:
            f["events"] = {
                "run": [1, 1, 2, 2, 3],
                "event": [101, 102, 201, 202, 301],
                "pt": [25.4, 48.1, 12.0, 88.3, 105.7]
            }
        print("Local ROOT file created successfully.")
    except Exception as e:
        print(f"Failed to create local ROOT file: {e}")
        return
        
    # 3. Instantiate ObjectStoreManager
    print("\n2. Initializing ObjectStoreManager...")
    try:
        osm = ObjectStoreManager()
        print("ObjectStoreManager initialized.")
    except Exception as e:
        print(f"Failed to initialize ObjectStoreManager: {e}")
        return
        
    # 4. Upload file
    print("\n3. Uploading file to EOS...")
    try:
        # Note: upload_file deletes the local file in its finally block!
        osm.upload_file(bucket, remote_file_name, local_file)
        print("Upload succeeded!")
    except Exception as e:
        print(f"Upload failed: {e}")
        return
        
    # 5. Verify upload by reading it back from EOS
    print("\n4. Verifying upload (reading remote file)...")
    remote_url = f"root://{eos_host}/{path_prefix}/{bucket}/{remote_file_name}"
    print(f"Reading from: {remote_url}")
    try:
        # Open file via fsspec
        with fsspec.open(remote_url, "rb") as open_file:
            # Load with uproot
            with uproot.open(open_file) as remote_tree:
                print("Remote file read successfully!")
                print(f"Keys inside remote ROOT file: {remote_tree.keys()}")
                events = remote_tree["events"]
                print(f"Branches: {events.keys()}")
                print(f"Values in pt branch: {events['pt'].array()}")
        print("\n=== Test PASSED end-to-end! ===")
    except Exception as e:
        print(f"\nVerification failed: {e}")

if __name__ == "__main__":
    main()
