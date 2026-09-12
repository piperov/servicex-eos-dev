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
import logging
import os
import traceback

try:
    from minio.error import MinioException, S3Error
except ImportError:
    class MinioException(Exception):
        pass

    class S3Error(Exception):
        pass

from tenacity import (
    RetryError,
    before_log,
    retry,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)


class ObjectStoreError(Exception):
    pass


class ObjectStoreManager:

    def __init__(self, url=None, username=None, password=None, use_https=False):
        handler = logging.NullHandler()
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(handler)

        self.store_type = os.environ.get("OBJECT_STORE_TYPE", "minio").lower()
        if "EOS_HOST" in os.environ and "OBJECT_STORE_TYPE" not in os.environ:
            self.store_type = "eos"

        if self.store_type in ["eos", "fsspec", "root"]:
            import fsspec
            self.eos_host = os.environ.get("EOS_HOST", "eos.cms.rcac.purdue.edu")
            self.eos_protocol = os.environ.get("EOS_PROTOCOL", "root")

            prefix = os.environ.get("EOS_PATH_PREFIX", "/store/user/piperov")
            if not prefix.startswith("/"):
                prefix = "/" + prefix
            self.path_prefix = prefix.rstrip("/")

            self.use_bucket_directory = (
                os.environ.get("EOS_USE_BUCKET_DIRECTORY", "true").lower() == "true"
            )

            self.logger.info(
                f"Initializing fsspec filesystem: {self.eos_protocol}://{self.eos_host} with prefix {self.path_prefix}"
            )
            self.fs = fsspec.filesystem(self.eos_protocol, hostid=self.eos_host)
            self.fs = fsspec.filesystem(self.eos_protocol, hostid=self.eos_host)

            # --- SP let's check if we can access the remote EOS FS ---
            try:
                print("DEBUG: SP Testing remote filesystem access...")
                # List the target prefix directory to verify read access
                test_path = "/store/user/piperov"
                # --- SP contents = self.fs.ls(test_path)
                contents = self.fs.ls(self.path_prefix) 
                # --- SP print(f"DEBUG: Success! Found {len(contents)} items in {test_path}")
                print(f"DEBUG: Success! Found {len(contents)} items in {self.path_prefix}") 
                print(f"DEBUG: Sample items: {contents[:3]}")
            except Exception as e:
                print(f"DEBUG: SP Remote filesystem test failed with error: {e}")
            # ----------------------------

        else:
            from minio import Minio

            if "MINIO_ENCRYPT" in os.environ:
                secure_connection = os.environ["MINIO_ENCRYPT"].lower() == "true"
            else:
                secure_connection = use_https
            self.minio_client = Minio(
                endpoint=url if url else os.environ["MINIO_URL"],
                access_key=username if username else os.environ["MINIO_ACCESS_KEY"],
                secret_key=password if password else os.environ["MINIO_SECRET_KEY"],
                secure=secure_connection,
            )

    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_result(
            lambda e: isinstance(e, S3Error)
            and hasattr(e, "code")
            and e.code in ["SlowDown", "ServiceUnavailable", "Throttling"]
        ),
        wait=wait_exponential(multiplier=3, exp_base=4) + wait_random(min=1, max=3),
        before=before_log(logging.getLogger(__name__), logging.INFO),
    )
    def _upload_file_with_retry(self, bucket, object_name, path):
        """
        Upload a file to the object store with retry logic for certain S3 errors.
        To take advantage of tenacity's retry logic based on specific errors, this
        function needs to return the exception rather than raise it.
        """
        try:
            result = self.minio_client.fput_object(
                bucket_name=bucket, object_name=object_name, file_path=path
            )
        except Exception as e:
            # retry_if_result needs the exception to be returned and not raised
            return e
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=3, exp_base=4) + wait_random(min=1, max=3),
        before=before_log(logging.getLogger(__name__), logging.INFO),
    )
    def _upload_file_fsspec_with_retry(self, remote_path, path):
        """
        Upload a file to remote filesystem using fsspec open and shutil.copyfileobj.
        This bypasses fs.put() which is not implemented by fsspec_xrootd.
        """
        import shutil
        with open(path, "rb") as f_local:
            with self.fs.open(remote_path, "wb") as f_remote:
                shutil.copyfileobj(f_local, f_remote)

    def upload_file(self, bucket, object_name, path):
        try:
            if self.store_type in ["eos", "fsspec", "root"]:
                remote_dir = self.path_prefix
                if self.use_bucket_directory:
                    remote_dir = f"{remote_dir}/{bucket}"
                remote_path = f"{remote_dir}/{object_name}"

                try:
                    self.fs.makedirs(remote_dir, exist_ok=True)
                except Exception as e:
                    self.logger.warning(
                        f"Could not create directory {remote_dir} (will attempt upload anyway): {e}"
                    )

                self._upload_file_fsspec_with_retry(remote_path, path)

                self.logger.info(
                    "OSM > uploaded object via fsspec.",
                    extra={
                        "request_id": bucket,
                        "object_name": object_name,
                        "remote_path": remote_path,
                    },
                )
            else:
                result = self._upload_file_with_retry(bucket, object_name, path)

                # The retry logic will return the exception rather than raise it
                if isinstance(result, Exception):
                    raise result

                self.logger.info(
                    "OSM > created object.",
                    extra={"request_id": bucket, "object_name": result.object_name},
                )

        except (RetryError, S3Error) as e:
            # If a non-retryable S3Error is raised it will come here. If we
            # ran out of retries it will also come here, but the exception will
            # wrapped by tenacity
            self.logger.error("S3Error", exc_info=True)
            traceback.print_exc()
            raise ObjectStoreError(
                f"Error uploading file to object store: {path}"
            ) from e

        except MinioException as e:
            self.logger.error("Minio error", exc_info=True)
            traceback.print_exc()
            raise ObjectStoreError(
                f"Error uploading file to object store: {path}"
            ) from e

        except Exception as e:
            self.logger.error("FSSpec / general upload error", exc_info=True)
            traceback.print_exc()
            raise ObjectStoreError(
                f"Error uploading file to object store: {path}"
            ) from e

        finally:
            # Delete the file regardless of success or failure
            try:
                os.remove(path)
            except FileNotFoundError:
                pass  # Should never happen, but is not fatal if it occurs
