# ObjectStoreManager Support for Purdue's EOS

A custom version of the `ObjectStoreManager` has been created in the `transformer_sidecar` module to upload output ROOT files directly into Purdue's EOS using `fsspec`.

## Implementation Details

### Bypassing fsspec xrootd `NotImplementedError`
In `fsspec_xrootd`, the `fs.put` (and `fs.put_file`) helper calls the asynchronous method `_put_file`, which raises a `NotImplementedError` directly.
To bypass this limitation, we upload files in a robust and cross-compatible way:
1. Open the local file in read-binary mode (`"rb"`).
2. Open the remote destination file using the `fsspec` filesystem object (`self.fs.open(remote_path, "wb")`).
3. Stream the file contents chunk-by-chunk using `shutil.copyfileobj`.

This has been tested and verified to upload successfully to Purdue's EOS.

---

## Configuration Options

The updated `ObjectStoreManager` is dynamically backward-compatible. By default, it falls back to Minio/S3. Set the following environment variables to activate and configure the EOS (`fsspec`) integration:

| Environment Variable | Description | Default Value |
| :--- | :--- | :--- |
| `OBJECT_STORE_TYPE` | Set to `"eos"`, `"fsspec"`, or `"root"` to enable EOS mode. | `"minio"` |
| `EOS_HOST` | The XRootD endpoint hostname. | `"eos.cms.rcac.purdue.edu"` |
| `EOS_PROTOCOL` | The fsspec protocol handler name. | `"root"` |
| `EOS_PATH_PREFIX` | The base remote directory where outputs should be saved. | `"/store/user/piperov"` |
| `EOS_USE_BUCKET_DIRECTORY` | Whether to nest files inside a subdirectory named after the request ID (bucket). | `"true"` |

---

## Code Diffs

Here is the diff of the changes made to [object_store_manager.py](file:///home/piperov/work/ServiceX/transformer_sidecar/src/transformer_sidecar/object_store_manager.py):

```diff
@@ -29,7 +29,15 @@
 import os
 import traceback
 
-from minio.error import MinioException, S3Error
+try:
+    from minio.error import MinioException, S3Error
+except ImportError:
+    class MinioException(Exception):
+        pass
+
+    class S3Error(Exception):
+        pass
+
 from tenacity import (
     RetryError,
     before_log,
@@ -47,9 +47,6 @@
 class ObjectStoreManager:
 
     def __init__(self, url=None, username=None, password=None, use_https=False):
-
-        from minio import Minio
-
         handler = logging.NullHandler()
         self.logger = logging.getLogger(__name__)
         self.logger.addHandler(handler)
@@ -56,13 +56,38 @@
-        if "MINIO_ENCRYPT" in os.environ:
-            secure_connection = os.environ["MINIO_ENCRYPT"].lower() == "true"
+        self.store_type = os.environ.get("OBJECT_STORE_TYPE", "minio").lower()
+        if "EOS_HOST" in os.environ and "OBJECT_STORE_TYPE" not in os.environ:
+            self.store_type = "eos"
+
+        if self.store_type in ["eos", "fsspec", "root"]:
+            import fsspec
+            self.eos_host = os.environ.get("EOS_HOST", "eos.cms.rcac.purdue.edu")
+            self.eos_protocol = os.environ.get("EOS_PROTOCOL", "root")
+
+            prefix = os.environ.get("EOS_PATH_PREFIX", "/store/user/piperov")
+            if not prefix.startswith("/"):
+                prefix = "/" + prefix
+            self.path_prefix = prefix.rstrip("/")
+
+            self.use_bucket_directory = (
+                os.environ.get("EOS_USE_BUCKET_DIRECTORY", "true").lower() == "true"
+            )
+
+            self.logger.info(
+                f"Initializing fsspec filesystem: {self.eos_protocol}://{self.eos_host} with prefix {self.path_prefix}"
+            )
+            self.fs = fsspec.filesystem(self.eos_protocol, hostid=self.eos_host)
         else:
-            secure_connection = use_https
-        self.minio_client = Minio(
-            endpoint=url if url else os.environ["MINIO_URL"],
-            access_key=username if username else os.environ["MINIO_ACCESS_KEY"],
-            secret_key=password if password else os.environ["MINIO_SECRET_KEY"],
-            secure=secure_connection,
-        )
+            from minio import Minio
+
+            if "MINIO_ENCRYPT" in os.environ:
+                secure_connection = os.environ["MINIO_ENCRYPT"].lower() == "true"
+            else:
+                secure_connection = use_https
+            self.minio_client = Minio(
+                endpoint=url if url else os.environ["MINIO_URL"],
+                access_key=username if username else os.environ["MINIO_ACCESS_KEY"],
+                secret_key=password if password else os.environ["MINIO_SECRET_KEY"],
+                secure=secure_connection,
+            )
 
     @retry(
         stop=stop_after_attempt(3),
@@ -88,18 +88,22 @@
             return e
         return result
 
+    @retry(
+        stop=stop_after_attempt(3),
+        wait=wait_exponential(multiplier=3, exp_base=4) + wait_random(min=1, max=3),
+        before=before_log(logging.getLogger(__name__), logging.INFO),
+    )
+    def _upload_file_fsspec_with_retry(self, remote_path, path):
+        """
+        Upload a file to remote filesystem using fsspec open and shutil.copyfileobj.
+        This bypasses fs.put() which is not implemented by fsspec_xrootd.
+        """
+        import shutil
+        with open(path, "rb") as f_local:
+            with self.fs.open(remote_path, "wb") as f_remote:
+                shutil.copyfileobj(f_local, f_remote)
 
     def upload_file(self, bucket, object_name, path):
         try:
-            result = self._upload_file_with_retry(bucket, object_name, path)
-
-            # The retry logic will return the exception rather than raise it
-            if isinstance(result, Exception):
-                raise result
-
-            self.logger.info(
-                "OSM > created object.",
-                extra={"request_id": bucket, "object_name": result.object_name},
-            )
+            if self.store_type in ["eos", "fsspec", "root"]:
+                remote_dir = self.path_prefix
+                if self.use_bucket_directory:
+                    remote_dir = f"{remote_dir}/{bucket}"
+                remote_path = f"{remote_dir}/{object_name}"
+
+                try:
+                    self.fs.makedirs(remote_dir, exist_ok=True)
+                except Exception as e:
+                    self.logger.warning(
+                        f"Could not create directory {remote_dir} (will attempt upload anyway): {e}"
+                    )
+
+                self._upload_file_fsspec_with_retry(remote_path, path)
+
+                self.logger.info(
+                    "OSM > uploaded object via fsspec.",
+                    extra={
+                        "request_id": bucket,
+                        "object_name": object_name,
+                        "remote_path": remote_path,
+                    },
+                )
+            else:
+                result = self._upload_file_with_retry(bucket, object_name, path)
+
+                # The retry logic will return the exception rather than raise it
+                if isinstance(result, Exception):
+                    raise result
+
+                self.logger.info(
+                    "OSM > created object.",
+                    extra={"request_id": bucket, "object_name": result.object_name},
+                )
```

---

## Verification and Testing

### 1. Integration Check
We successfully ran an integration test script showing a successful upload to Purdue's EOS:
```bash
Created local dummy file.
Uploading file to Purdue's EOS via ObjectStoreManager...
Upload succeeded!
```

### 2. Pytest Results
All `fsspec` unit tests in [test_object_store_manager.py](file:///home/piperov/work/ServiceX/transformer_sidecar/tests/test_object_store_manager.py) pass cleanly in the CVMFS environment:
```bash
transformer_sidecar/tests/test_object_store_manager.py ...               [100%]
======================= 3 passed, 4 deselected in 19.77s =======================
```
