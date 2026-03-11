"""Knowledge base management routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth_middleware import get_current_user
from app.db.database import get_db
from app.models.knowledge import KnowledgeDocument
from app.models.user import User
from app.services.knowledge_base import get_knowledge_base_service

router = APIRouter()


class URLRequest(BaseModel):
    url: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.get("/")
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """List all knowledge base documents."""
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.organization_id == current_user.organization_id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return {
        "data": [
            {
                "id": d.id,
                "filename": d.filename,
                "source_url": d.source_url,
                "doc_type": d.doc_type,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "error_message": d.error_message,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ]
    }


@router.post("/upload", status_code=201)
async def upload_document(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> dict:
    """Upload a document (PDF, TXT, DOCX) to the knowledge base."""
    allowed_types = {
        "application/pdf": "pdf",
        "text/plain": "txt",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    }

    content_type = file.content_type or ""
    if content_type not in allowed_types and not file.filename.endswith(
        (".pdf", ".txt", ".docx")
    ):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    data = await file.read()

    # Create DB record first
    doc = KnowledgeDocument(
        organization_id=current_user.organization_id,
        filename=file.filename or "upload",
        doc_type="file",
        status="processing",
    )
    db.add(doc)
    await db.flush()

    # Process in background
    kb = get_knowledge_base_service()
    try:
        fname = file.filename or ""
        if fname.endswith(".pdf") or "pdf" in content_type:
            chunks = await kb.add_pdf(current_user.organization_id, data, doc.id, fname)
        elif fname.endswith(".docx"):
            chunks = await kb.add_docx(
                current_user.organization_id, data, doc.id, fname
            )
        else:
            text = data.decode("utf-8", errors="ignore")
            chunks = await kb.add_text(
                current_user.organization_id, text, doc.id, {"filename": fname}
            )

        doc.status = "ready"
        doc.chunk_count = chunks
    except Exception as exc:
        doc.status = "error"
        doc.error_message = str(exc)

    db.add(doc)
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
    }


@router.post("/url", status_code=201)
async def add_url(
    body: URLRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Add a URL to the knowledge base."""
    doc = KnowledgeDocument(
        organization_id=current_user.organization_id,
        filename=body.url[:255],
        source_url=body.url,
        doc_type="url",
        status="processing",
    )
    db.add(doc)
    await db.flush()

    kb = get_knowledge_base_service()
    try:
        chunks = await kb.add_url(current_user.organization_id, body.url, doc.id)
        doc.status = "ready"
        doc.chunk_count = chunks
    except Exception as exc:
        doc.status = "error"
        doc.error_message = str(exc)

    db.add(doc)
    return {
        "id": doc.id,
        "url": body.url,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
    }


@router.post("/search")
async def search_knowledge_base(
    body: SearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Search the knowledge base (test endpoint)."""
    kb = get_knowledge_base_service()
    results = await kb.query(current_user.organization_id, body.query, top_k=body.top_k)
    return {"query": body.query, "results": results}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Delete a document from the knowledge base."""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()

    if not doc or doc.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Document not found")

    kb = get_knowledge_base_service()
    await kb.delete_document(current_user.organization_id, doc_id)
    await db.delete(doc)

    return {"message": "Document deleted"}
