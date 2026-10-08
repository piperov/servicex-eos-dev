import datetime

from flask import current_app
from flask_restful import reqparse

from servicex_app.decorators import auth_required
from servicex_app.models import TransformationResult
from servicex_app.resources.servicex_resource import ServiceXResource


class TransformationResults(ServiceXResource):
    @auth_required
    def get(self, request_id):
        if not request_id:
            return {"message": "Missing required transformation request_id"}, 400

        parser = reqparse.RequestParser()
        parser.add_argument("later_than", type=str, required=False, location="args")

        args = parser.parse_args()

        transform_result_query = TransformationResult.query.filter_by(
            request_id=request_id
        )

        later_than_str = args.get("later_than")
        if later_than_str:
            try:
                later_than = datetime.datetime.fromisoformat(later_than_str)
            except (AttributeError, ValueError):
                return {
                    "message": (
                        f"later_than value {later_than_str} "
                        "is not an ISO 8601 compliant datetime"
                    )
                }, 400
            transform_result_query = transform_result_query.filter(
                TransformationResult.created_at > later_than
            )

        store_type = current_app.config.get("OBJECT_STORE_TYPE", "minio").lower()
        is_eos = store_type in ["eos", "fsspec", "root"]

        if is_eos:
            eos_host = current_app.config.get("EOS_HOST", "eos.cms.rcac.purdue.edu")
            eos_protocol = current_app.config.get("EOS_PROTOCOL", "root")
            prefix = current_app.config.get("EOS_PATH_PREFIX", "/store/user/piperov")
            if not prefix.startswith("/"):
                prefix = "/" + prefix
            prefix = prefix.rstrip("/")
            use_bucket = current_app.config.get("EOS_USE_BUCKET_DIRECTORY", True)
            if isinstance(use_bucket, str):
                use_bucket = use_bucket.lower() == "true"

        results = []
        for transformation_result in transform_result_query:
            res_json = transformation_result.to_json(transformation_result)
            if is_eos and res_json.get("s3-object-name"):
                s3_name = res_json["s3-object-name"]
                if not s3_name.startswith("root://") and not s3_name.startswith("http"):
                    if use_bucket:
                        full_path = f"{prefix}/{request_id}/{s3_name}"
                    else:
                        full_path = f"{prefix}/{s3_name}"
                    res_json["s3-object-name"] = f"{eos_protocol}://{eos_host}:1094/{full_path}"
            results.append(res_json)

        return {"results": results}
