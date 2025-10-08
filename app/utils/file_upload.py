import os
import logging
import shutil
import uuid
import mimetypes
from urllib.parse import urlparse
from fastapi import UploadFile, HTTPException
from pathlib import Path

try:
    import boto3  # type: ignore
    from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
except Exception:  # boto3 optional; fallback to local
    boto3 = None
    BotoCoreError = ClientError = Exception

# Logger
logger = logging.getLogger("app.file_upload")

# Local uploads directory (fallback)
UPLOADS_DIR = Path("./uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

def _s3_enabled() -> bool:
    return bool(
        boto3 is not None
        and os.getenv("AWS_S3_BUCKET")
        and os.getenv("AWS_S3_REGION")
        and os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
    )

def _s3_client():
    region = os.getenv("AWS_S3_REGION")
    # Credentials can be provided via env/instance role; boto3 will resolve
    return boto3.client("s3", region_name=region)

def _s3_public_url(bucket: str, region: str, key: str) -> str:
    base = os.getenv("AWS_S3_PUBLIC_BASE_URL")
    if base:
        return f"{base.rstrip('/')}/{key}"
    # Default virtual-hosted–style URL
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

async def upload_file(file: UploadFile, folder: str = "general") -> str:
    """
    Upload a file to AWS S3 and return its public URL.
    Local storage is disabled by configuration.
    """
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    safe_folder = folder.strip("/") if folder else "general"
    
    if not _s3_enabled():
        logger.error(
            "S3 not configured",
            extra={
                "has_boto3": boto3 is not None,
                "has_bucket": bool(os.getenv("AWS_S3_BUCKET")),
                "has_region": bool(os.getenv("AWS_S3_REGION")),
                "has_access_key": bool(os.getenv("AWS_ACCESS_KEY_ID")),
                "has_secret_key": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
            },
        )
        raise HTTPException(status_code=500, detail="S3 is not configured on the server")

    bucket = os.getenv("AWS_S3_BUCKET") or ""
    region = os.getenv("AWS_S3_REGION") or ""
    key = f"{safe_folder}/{unique_filename}"
    content_type = file.content_type or mimetypes.guess_type(unique_filename)[0] or "application/octet-stream"
    try:
        client = _s3_client()
        file.file.seek(0)
        extra_args = {"ContentType": content_type}
        acl = os.getenv("AWS_S3_ACL")
        if acl:
            # Only include ACL when explicitly provided to avoid errors on buckets with ACLs disabled
            extra_args["ACL"] = acl
        logger.info(
            "Uploading to S3",
            extra={
                "bucket": bucket,
                "region": region,
                "key": key,
                "content_type": content_type,
                "uses_acl": bool(acl),
            },
        )
        client.upload_fileobj(
            Fileobj=file.file,
            Bucket=bucket,
            Key=key,
            ExtraArgs=extra_args,
        )
        url = _s3_public_url(bucket, region, key)
        logger.info("S3 upload success", extra={"url": url})
        return url
    except ClientError as e:
        err = e.response.get("Error", {}) if hasattr(e, "response") else {}
        code = err.get("Code")
        msg = err.get("Message")
        req_id = (e.response or {}).get("ResponseMetadata", {}).get("RequestId") if hasattr(e, "response") else None
        http_status = (e.response or {}).get("ResponseMetadata", {}).get("HTTPStatusCode") if hasattr(e, "response") else None

        # Auto-retry without ACL when bucket enforces ACLs disabled (ObjectOwnership = BucketOwnerEnforced)
        if code == "AccessControlListNotSupported" and "ACL" in extra_args:
            try:
                logger.warning(
                    "Bucket does not allow ACLs; retrying upload without ACL",
                    extra={
                        "bucket": bucket,
                        "region": region,
                        "key": key,
                        "request_id": req_id,
                        "http_status": http_status,
                    },
                )
                # retry with no ACL
                extra_args_no_acl = {"ContentType": content_type}
                file.file.seek(0)
                client.upload_fileobj(
                    Fileobj=file.file,
                    Bucket=bucket,
                    Key=key,
                    ExtraArgs=extra_args_no_acl,
                )
                url = _s3_public_url(bucket, region, key)
                logger.info("S3 upload success after ACL retry", extra={"url": url})
                return url
            except Exception as e2:
                logger.exception(
                    "S3 upload retry without ACL failed",
                    extra={
                        "bucket": bucket,
                        "region": region,
                        "key": key,
                        "original_error_code": code,
                        "original_error_message": msg,
                    },
                )
                # fall through to standard error handling

        logger.exception(
            "S3 upload failed",
            extra={
                "error_code": code,
                "error_message": msg,
                "request_id": req_id,
                "http_status": http_status,
                "bucket": bucket,
                "region": region,
                "key": key,
            },
        )
        raise HTTPException(status_code=500, detail=f"S3 upload failed [{code}]: {msg}")
    except BotoCoreError as e:
        logger.exception("S3 client/core error", extra={"error": str(e), "bucket": bucket, "region": region, "key": key})
        raise HTTPException(status_code=500, detail=f"S3 client error: {e}")

async def delete_file(file_path: str) -> bool:
    """
    Delete a file from S3.
    Accepts either a full S3 URL or a relative S3 key-like path.
    """
    if not _s3_enabled():
        raise HTTPException(status_code=500, detail="S3 is not configured on the server")

    try:
        bucket = os.getenv("AWS_S3_BUCKET") or ""
        parsed = urlparse(file_path)
        if parsed.scheme in ("http", "https"):
            key = parsed.path.lstrip("/")
        else:
            key = file_path.lstrip("/")
        client = _s3_client()
        logger.info("Deleting from S3", extra={"bucket": bucket, "key": key})
        client.delete_object(Bucket=bucket, Key=key)
        logger.info("S3 delete success", extra={"bucket": bucket, "key": key})
        return True
    except ClientError as e:
        err = e.response.get("Error", {}) if hasattr(e, "response") else {}
        code = err.get("Code")
        msg = err.get("Message")
        req_id = (e.response or {}).get("ResponseMetadata", {}).get("RequestId") if hasattr(e, "response") else None
        http_status = (e.response or {}).get("ResponseMetadata", {}).get("HTTPStatusCode") if hasattr(e, "response") else None
        logger.exception("S3 delete failed", extra={"error_code": code, "error_message": msg, "request_id": req_id, "http_status": http_status, "bucket": bucket, "key": key})
        raise HTTPException(status_code=500, detail=f"S3 delete failed [{code}]: {msg}")
    except BotoCoreError as e:
        logger.exception("S3 client/core error on delete", extra={"error": str(e), "bucket": bucket, "key": key})
        raise HTTPException(status_code=500, detail=f"S3 client error: {e}")
