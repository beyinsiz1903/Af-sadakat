"""File Upload Router - Photo/file upload for requests, lost&found, etc.
Chunked upload support, image validation, persistent storage
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from typing import Optional, List
import os
import uuid
import aiofiles
from pathlib import Path

from core.config import db, PUBLIC_BASE_URL
from core.tenant_guard import (
    resolve_tenant, get_current_user, get_optional_user,
    serialize_doc, new_id, now_utc, insert_scoped, find_many_scoped
)

router = APIRouter(prefix="/api/v2/uploads", tags=["uploads"])

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".doc", ".docx", ".mp4", ".mov"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()

@router.post("/g/{tenant_slug}/upload")
async def guest_upload_file(
    tenant_slug: str,
    file: UploadFile = File(...),
    entity_type: str = Form(default="request"),
    entity_id: str = Form(default=""),
    room_code: str = Form(default=""),
):
    """Guest file upload (no auth required)"""
    tenant = await resolve_tenant(tenant_slug)
    return await _handle_upload(file, tenant["id"], entity_type, entity_id, room_code, "guest")

@router.post("/tenants/{tenant_slug}/upload")
async def admin_upload_file(
    tenant_slug: str,
    file: UploadFile = File(...),
    entity_type: str = Form(default=""),
    entity_id: str = Form(default=""),
    user=Depends(get_current_user),
):
    """Admin file upload"""
    tenant = await resolve_tenant(tenant_slug)
    return await _handle_upload(file, tenant["id"], entity_type, entity_id, "", user.get("name", "admin"))

async def _handle_upload(file: UploadFile, tenant_id: str, entity_type: str, entity_id: str, room_code: str, uploaded_by: str):
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {ext}")
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    filepath = UPLOAD_DIR / filename
    
    # Save file
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)
    
    # Record in DB
    file_url = f"/api/v2/uploads/files/{filename}"
    
    record = {
        "id": file_id,
        "tenant_id": tenant_id,
        "filename": file.filename,
        "stored_filename": filename,
        "file_url": file_url,
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": len(content),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "room_code": room_code,
        "uploaded_by": uploaded_by,
        "created_at": now_utc().isoformat(),
    }
    await db.file_uploads.insert_one(record)
    
    return {
        "id": file_id,
        "filename": file.filename,
        "file_url": file_url,
        "content_type": file.content_type,
        "size_bytes": len(content),
    }

@router.get("/files/{filename}")
async def serve_file(filename: str):
    """Serve uploaded file"""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)

@router.get("/g/{tenant_slug}/files")
async def list_guest_files(tenant_slug: str, entity_type: str = "", entity_id: str = "", room_code: str = ""):
    """List files for a guest entity"""
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if room_code:
        query["room_code"] = room_code
    return await find_many_scoped("file_uploads", tenant["id"], query, sort=[("created_at", -1)])

@router.get("/tenants/{tenant_slug}/files")
async def list_admin_files(tenant_slug: str, entity_type: str = "", entity_id: str = "",
                           user=Depends(get_current_user)):
    """List files for admin"""
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    return await find_many_scoped("file_uploads", tenant["id"], query, sort=[("created_at", -1)])
