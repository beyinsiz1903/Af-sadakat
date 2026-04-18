"""Storage Router: Abstract file storage with S3-compatible backend.
Falls back to local /uploads/ when S3 is not configured.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
import os
import logging
import uuid
from pathlib import Path

from core.config import db
from core.tenant_guard import serialize_doc, now_utc, resolve_tenant, get_current_user
from fastapi import Depends

logger = logging.getLogger("omnihub.storage")

router = APIRouter(prefix="/api/v2/storage", tags=["storage"])

S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_REGION = os.environ.get("S3_REGION", "eu-west-1")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
STORAGE_MODE = "s3" if S3_BUCKET and S3_ACCESS_KEY else "local"

LOCAL_UPLOAD_DIR = Path("uploads")
LOCAL_UPLOAD_DIR.mkdir(exist_ok=True)

s3_client = None
if STORAGE_MODE == "s3":
    try:
        import boto3
        s3_client = boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
        )
        logger.info(f"S3 storage enabled: bucket={S3_BUCKET}")
    except ImportError:
        logger.warning("boto3 not installed, falling back to local storage")
        STORAGE_MODE = "local"


async def store_file(tenant_id: str, file: UploadFile, entity_type: str = "general") -> dict:
    ext = Path(file.filename or "file").suffix
    file_id = str(uuid.uuid4())
    key = f"{tenant_id}/{entity_type}/{file_id}{ext}"
    content = await file.read()

    if STORAGE_MODE == "s3" and s3_client:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type or "application/octet-stream",
        )
        url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
    else:
        local_dir = LOCAL_UPLOAD_DIR / tenant_id / entity_type
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / f"{file_id}{ext}"
        with open(local_path, "wb") as f:
            f.write(content)
        url = f"/uploads/{tenant_id}/{entity_type}/{file_id}{ext}"

    record = {
        "id": file_id, "tenant_id": tenant_id,
        "original_name": file.filename or "file",
        "key": key, "url": url,
        "size": len(content),
        "content_type": file.content_type or "application/octet-stream",
        "entity_type": entity_type,
        "storage": STORAGE_MODE,
        "created_at": now_utc().isoformat(),
    }
    await db.file_records.insert_one(record)
    return record


async def delete_file(tenant_id: str, file_id: str) -> bool:
    record = await db.file_records.find_one({"id": file_id, "tenant_id": tenant_id})
    if not record:
        return False

    if record.get("storage") == "s3" and s3_client:
        try:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=record["key"])
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
    else:
        local_path = LOCAL_UPLOAD_DIR / record["key"]
        if local_path.exists():
            local_path.unlink()

    await db.file_records.delete_one({"id": file_id})
    return True


@router.get("/config")
async def get_storage_config():
    return {"mode": STORAGE_MODE, "s3_bucket": S3_BUCKET if STORAGE_MODE == "s3" else None}


@router.post("/tenants/{tenant_slug}/upload")
async def upload_file(
    tenant_slug: str,
    file: UploadFile = File(...),
    entity_type: str = Form("general"),
    user=Depends(get_current_user)
):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    max_size = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    await file.seek(0)

    record = await store_file(tid, file, entity_type)
    return {"file_id": record["id"], "url": record["url"], "size": record["size"]}


@router.get("/tenants/{tenant_slug}/files")
async def list_files(tenant_slug: str, entity_type: str = None, limit: int = 50, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    query = {"tenant_id": tid}
    if entity_type:
        query["entity_type"] = entity_type

    files = await db.file_records.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    return [serialize_doc(f) for f in files]


@router.delete("/tenants/{tenant_slug}/files/{file_id}")
async def remove_file(tenant_slug: str, file_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    ok = await delete_file(tid, file_id)
    if not ok:
        raise HTTPException(status_code=404, detail="File not found")
    return {"deleted": True}


@router.get("/tenants/{tenant_slug}/files/{file_id}/signed-url")
async def get_signed_url(tenant_slug: str, file_id: str, expires_in: int = 3600,
                          user=Depends(get_current_user)):
    """Generate a presigned URL for private S3 objects (1h default)."""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    record = await db.file_records.find_one({"id": file_id, "tenant_id": tid})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    expires_in = max(60, min(expires_in, 86400))
    if record.get("storage") == "s3" and s3_client:
        try:
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": record["key"]},
                ExpiresIn=expires_in,
            )
            return {"url": url, "expires_in": expires_in, "storage": "s3"}
        except Exception as e:
            logger.error(f"presign failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to sign URL")
    return {"url": record["url"], "expires_in": 0, "storage": "local"}
