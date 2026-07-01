# Copyright (c) 2019, IRIS-HEP
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from tenacity import retry, stop_after_attempt, wait_random_exponential


class ObjectStoreManager:

    def __init__(
        self,
        url,
        username,
        password,
        use_https=False,
        store_type=None,
        eos_host=None,
        eos_protocol=None,
        eos_path_prefix=None,
        eos_use_bucket_directory=None,
    ):
        import os

        # Use parameter or fallback to environment variables
        self.store_type = (store_type or os.environ.get("OBJECT_STORE_TYPE", "minio")).lower()
        if "EOS_HOST" in os.environ and not store_type:
            self.store_type = "eos"

        if self.store_type in ["eos", "fsspec", "root"]:
            self.eos_host = eos_host or os.environ.get("EOS_HOST", "eos.cms.rcac.purdue.edu")
            self.eos_protocol = eos_protocol or os.environ.get("EOS_PROTOCOL", "root")
            prefix = eos_path_prefix or os.environ.get("EOS_PATH_PREFIX", "/store/user/piperov")
            if not prefix.startswith("/"):
                prefix = "/" + prefix
            self.path_prefix = prefix.rstrip("/")

            use_bucket = eos_use_bucket_directory
            if use_bucket is None or use_bucket == "":
                use_bucket = os.environ.get("EOS_USE_BUCKET_DIRECTORY", "true")
            if isinstance(use_bucket, str):
                self.use_bucket_directory = use_bucket.lower() == "true"
            else:
                self.use_bucket_directory = bool(use_bucket)

            self.fs = None
            try:
                import fsspec
                self.fs = fsspec.filesystem(self.eos_protocol, hostid=self.eos_host)
            except ImportError:
                import logging
                logging.getLogger(__name__).warning(
                    "fsspec not installed. Directory creation/deletion on EOS will be skipped."
                )
        else:
            from minio import Minio
            self.minio_client = Minio(
                endpoint=url, access_key=username, secret_key=password, secure=use_https
            )

    @retry(
        stop=stop_after_attempt(3), wait=wait_random_exponential(max=60), reraise=True
    )
    def create_bucket(self, bucket_name):
        if self.store_type in ["eos", "fsspec", "root"]:
            if self.fs:
                remote_dir = self.path_prefix
                if self.use_bucket_directory:
                    remote_dir = f"{remote_dir}/{bucket_name}"
                try:
                    self.fs.makedirs(remote_dir, exist_ok=True)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Could not create directory {remote_dir}: {e}"
                    )
            return

        self.minio_client.make_bucket(bucket_name)

    def list_buckets(self):
        if self.store_type in ["eos", "fsspec", "root"]:
            if self.fs:
                try:
                    return self.fs.ls(self.path_prefix)
                except Exception:
                    return []
            return []
        return self.minio_client.list_buckets()

    def delete_bucket_and_contents(self, bucket_name):
        if self.store_type in ["eos", "fsspec", "root"]:
            if self.fs:
                remote_dir = self.path_prefix
                if self.use_bucket_directory:
                    remote_dir = f"{remote_dir}/{bucket_name}"
                try:
                    self.fs.rm(remote_dir, recursive=True)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Could not delete directory {remote_dir}: {e}"
                    )
            return

        if not self.minio_client.bucket_exists(bucket_name):
            print(f"Bucket '{bucket_name}' does not exist. Nothing to delete.")
            return

        # List all objects in the bucket
        objects = self.minio_client.list_objects(bucket_name, recursive=True)

        # Remove each object
        for obj in objects:
            self.minio_client.remove_object(bucket_name, obj.object_name)

        # Remove the bucket itself
        self.minio_client.remove_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' deleted successfully.")
