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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

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

# Timeout (seconds) for individual EOS operations. XRootD can hang
# indefinitely if the server is unreachable, so we cap each call.
EOS_CONNECT_TIMEOUT = 30
EOS_OP_TIMEOUT = 60


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
            self.eos_host = os.environ.get("EOS_HOST", "eos.cms.rcac.purdue.edu")
            self.eos_protocol = os.environ.get("EOS_PROTOCOL", "root")

            prefix = os.environ.get("EOS_PATH_PREFIX", "/store/user/piperov")
            if not prefix.startswith("/"):
                prefix = "/" + prefix
            self.path_prefix = prefix.rstrip("/")

            self.use_bucket_directory = (
                os.environ.get("EOS_USE_BUCKET_DIRECTORY", "true").lower() == "true"
            )
            self._fs = None
            self._fs_pid = None
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

    @property
    def fs(self):
        current_pid = os.getpid()
        if getattr(self, "_fs_pid", None) != current_pid or getattr(self, "_fs", None) is None:
            import fsspec
            self.logger.info(
                f"[EOS] Initializing fsspec filesystem for pid={current_pid}: "
                f"{self.eos_protocol}://{self.eos_host} "
                f"with prefix={self.path_prefix} "
                f"use_bucket_directory={self.use_bucket_directory}"
            )
            self._fs = fsspec.filesystem(self.eos_protocol, hostid=self.eos_host)
            self._fs_pid = current_pid

            # Test remote connectivity with a timeout so we fail fast
            # rather than hanging indefinitely if EOS is unreachable.
            self.logger.info(
                f"[EOS] Testing remote filesystem connectivity for pid={current_pid} "
                f"(timeout={EOS_CONNECT_TIMEOUT}s): listing {self.path_prefix}"
            )
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._fs.ls, self.path_prefix)
                    contents = future.result(timeout=EOS_CONNECT_TIMEOUT)
                self.logger.info(
                    f"[EOS] Connectivity test PASSED for pid={current_pid}: found {len(contents)} items "
                    f"in {self.path_prefix}. Sample: {contents[:3]}"
                )
            except FuturesTimeoutError:
                self.logger.error(
                    f"[EOS] Connectivity test TIMED OUT for pid={current_pid} after {EOS_CONNECT_TIMEOUT}s "
                    f"trying to list {self.path_prefix} on {self.eos_host}. "
                    "This usually means the pod cannot reach the EOS server "
                    "(check network/hostNetwork settings and XRootD port 1094)."
                )
            except Exception as e:
                self.logger.warning(
                    f"[EOS] Connectivity test FAILED for pid={current_pid} (will attempt uploads anyway): {e}"
                )
        return self._fs

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
        self.logger.info(f"[EOS] Opening remote file for write (timeout={EOS_OP_TIMEOUT}s): {remote_path}")
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                def _do_copy():
                    with open(path, "rb") as f_local:
                        with self.fs.open(remote_path, "wb") as f_remote:
                            shutil.copyfileobj(f_local, f_remote)
                future = executor.submit(_do_copy)
                future.result(timeout=EOS_OP_TIMEOUT)
        except FuturesTimeoutError:
            raise OSError(
                f"[EOS] Upload to {remote_path} timed out after {EOS_OP_TIMEOUT}s. "
                "Check EOS network connectivity and x509 proxy validity."
            )
        self.logger.info(f"[EOS] Upload completed: {remote_path}")

    def upload_file(self, bucket, object_name, path):
        try:
            if self.store_type in ["eos", "fsspec", "root"]:
                remote_dir = self.path_prefix
                if self.use_bucket_directory:
                    remote_dir = f"{remote_dir}/{bucket}"
                remote_path = f"{remote_dir}/{object_name}"
                remote_file_dir = os.path.dirname(remote_path)

                self.logger.info(
                    f"[EOS] Creating remote directory (if needed): {remote_file_dir}"
                )
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(self.fs.makedirs, remote_file_dir, True)
                        future.result(timeout=EOS_OP_TIMEOUT)
                    self.logger.info(f"[EOS] Remote directory ready: {remote_file_dir}")
                except FuturesTimeoutError:
                    self.logger.warning(
                        f"[EOS] makedirs timed out after {EOS_OP_TIMEOUT}s for "
                        f"{remote_file_dir} — will attempt upload anyway"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"[EOS] Could not create directory {remote_file_dir} "
                        f"(will attempt upload anyway): {e}"
                    )

                self.logger.info(
                    f"[EOS] Starting upload: local={path} -> remote={remote_path}"
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
