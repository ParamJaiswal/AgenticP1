"""Knowledge Base service using ChromaDB (free, embedded, no external service)."""

from __future__ import annotations

import asyncio
import io
import os
from typing import Any

import structlog

from config import settings

log = structlog.get_logger()


class KnowledgeBaseService:
    """RAG-based knowledge base using ChromaDB + sentence-transformers."""

    def __init__(self) -> None:
        self._client: Any | None = None
        self._embedding_fn: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def _get_embedding_fn(self) -> Any:
        if self._embedding_fn is None:
            from chromadb.utils import embedding_functions

            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )
        return self._embedding_fn

    def _collection_name(self, organization_id: str) -> str:
        """Unique ChromaDB collection per tenant."""
        return f"org_{organization_id.replace('-', '_')}"

    def _get_collection(self, organization_id: str) -> Any:
        client = self._get_client()
        return client.get_or_create_collection(
            name=self._collection_name(organization_id),
            embedding_function=self._get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )

    async def add_text(
        self,
        organization_id: str,
        text: str,
        doc_id: str,
        metadata: dict | None = None,
    ) -> int:
        """Add text to the knowledge base, chunked.

        Returns:
            Number of chunks added.
        """
        chunks = self._chunk_text(text)
        if not chunks:
            return 0

        loop = asyncio.get_event_loop()

        def _add() -> int:
            collection = self._get_collection(organization_id)
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metas = [
                {**(metadata or {}), "doc_id": doc_id, "chunk_index": i}
                for i in range(len(chunks))
            ]
            collection.upsert(documents=chunks, ids=ids, metadatas=metas)
            return len(chunks)

        return await loop.run_in_executor(None, _add)

    async def add_pdf(
        self, organization_id: str, pdf_bytes: bytes, doc_id: str, filename: str
    ) -> int:
        """Extract text from PDF and add to knowledge base."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("pypdf not installed: pip install pypdf")

        def _extract() -> str:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            return "\n\n".join(
                page.extract_text() for page in reader.pages if page.extract_text()
            )

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _extract)
        return await self.add_text(
            organization_id, text, doc_id, {"filename": filename, "type": "pdf"}
        )

    async def add_docx(
        self, organization_id: str, docx_bytes: bytes, doc_id: str, filename: str
    ) -> int:
        """Extract text from DOCX and add to knowledge base."""
        try:
            import docx2txt
        except ImportError:
            raise RuntimeError("docx2txt not installed: pip install docx2txt")

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(docx_bytes)
            tmp_path = tmp.name

        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None, lambda: docx2txt.process(tmp_path)
            )
        finally:
            os.unlink(tmp_path)

        return await self.add_text(
            organization_id, text, doc_id, {"filename": filename, "type": "docx"}
        )

    async def add_url(
        self, organization_id: str, url: str, doc_id: str
    ) -> int:
        """Scrape URL and add content to knowledge base."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to fetch URL: {resp.status}")
                html = await resp.text()

        # Basic HTML stripping
        import re

        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        return await self.add_text(
            organization_id, text, doc_id, {"url": url, "type": "url"}
        )

    async def query(
        self, organization_id: str, query_text: str, top_k: int | None = None
    ) -> list[str]:
        """Retrieve relevant chunks for a query.

        Returns:
            List of relevant text chunks.
        """
        k = top_k or settings.RAG_TOP_K
        loop = asyncio.get_event_loop()

        def _query() -> list[str]:
            collection = self._get_collection(organization_id)
            if collection.count() == 0:
                return []
            results = collection.query(query_texts=[query_text], n_results=min(k, collection.count()))
            return results.get("documents", [[]])[0]

        return await loop.run_in_executor(None, _query)

    async def delete_document(self, organization_id: str, doc_id: str) -> None:
        """Delete all chunks for a document."""
        loop = asyncio.get_event_loop()

        def _delete() -> None:
            collection = self._get_collection(organization_id)
            # Find all IDs for this doc
            results = collection.get(where={"doc_id": doc_id})
            if results and results.get("ids"):
                collection.delete(ids=results["ids"])

        await loop.run_in_executor(None, _delete)

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + size
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
            if start <= 0:
                start = end  # Avoid infinite loop on very short texts
        return chunks


_kb_service: KnowledgeBaseService | None = None


def get_knowledge_base_service() -> KnowledgeBaseService:
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService()
    return _kb_service
