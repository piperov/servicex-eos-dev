# Copyright (c) 2026, IRIS-HEP
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
import datetime

from flask import current_app
from flask_restful import reqparse

from servicex_app.decorators import auth_required
from servicex_app.models import TransformRequest
from servicex_app.resources.servicex_resource import ServiceXResource

import boto3


class FileURLGenerator(ServiceXResource):
    def __init__(self):
        super().__init__()
        store_type = current_app.config.get("OBJECT_STORE_TYPE", "minio").lower()
        if store_type in ["eos", "fsspec", "root"]:
            self.s3client = None
        else:
            endpoint_url = (
                "https://"
                if current_app.config.get("MINIO_ENCRYPT_PUBLIC", True)
                else "http://"
            ) + (current_app.config.get("MINIO_PUBLIC_URL") or "localhost:9000")
            self.s3client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=current_app.config.get("MINIO_ACCESS_KEY", ""),
                aws_secret_access_key=current_app.config.get("MINIO_SECRET_KEY", ""),
                use_ssl=current_app.config.get("MINIO_ENCRYPT_PUBLIC", True),
            )

    @auth_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("request_id", type=str, required=True, location="json")
        parser.add_argument("file_list", type=list, required=True, location="json")
        parser.add_argument(
            "scheme",
            type=str,
            choices=["http", "xrootd"],
            required=False,
            location="json",
        )

        args = parser.parse_args()
        request_id = args["request_id"]
        # Validate that the user is an admin or submitted the request (not yet implemented)
        transform = TransformRequest.lookup(request_id)
        if not transform:
            msg = f"Transformation request not found with id: {request_id}"
            current_app.logger.error(msg, extra={"request_id": request_id})
            return {"message": msg}, 404

        expirydelta = 365 * 24 * 60 * 60
        expiry = int(datetime.datetime.now().timestamp() + expirydelta)

        store_type = current_app.config.get("OBJECT_STORE_TYPE", "minio").lower()
        if store_type in ["eos", "fsspec", "root"]:
            eos_host = current_app.config.get("EOS_HOST", "eos.cms.rcac.purdue.edu")
            eos_protocol = current_app.config.get("EOS_PROTOCOL", "root")
            prefix = current_app.config.get("EOS_PATH_PREFIX", "/store/user/piperov")
            if not prefix.startswith("/"):
                prefix = "/" + prefix
            prefix = prefix.rstrip("/")
            use_bucket = current_app.config.get("EOS_USE_BUCKET_DIRECTORY", True)
            if isinstance(use_bucket, str):
                use_bucket = use_bucket.lower() == "true"

            rv = {}
            for f in args["file_list"]:
                if f.startswith("root://") or f.startswith("http"):
                    url = f
                else:
                    if use_bucket:
                        full_path = f"{prefix}/{request_id}/{f}"
                    else:
                        full_path = f"{prefix}/{f}"
                    url = f"{eos_protocol}://{eos_host}:1094/{full_path}"
                rv[f] = (url, {}, expiry)
            return {"uris": rv}

        rv = {
            f: (
                self.s3client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": request_id, "Key": f},
                    ExpiresIn=expirydelta,
                ),
                {},
                expiry,
            )
            for f in args["file_list"]
        }

        return {"uris": rv}
