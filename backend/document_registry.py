import os
import hashlib
import logging
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import (
	create_engine,
	String,
	DateTime,
	Text,
	Index,
	select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

logger = logging.getLogger("document_registry")


def _sha256(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def stable_doc_uid(source_path: str) -> str:
	# Stable identity for a "document at a path" (good for re-index/diff/delete).
	# Dedupe is handled separately via content_hash.
	normalized = (source_path or "").strip().replace("\\", "/")
	return _sha256(normalized)


class Base(DeclarativeBase):
	pass


class DocumentRecord(Base):
	__tablename__ = "kl_documents"

	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	doc_uid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
	source_path: Mapped[str] = mapped_column(Text, nullable=False)

	content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
	extract_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
	chunker_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
	embedding_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

	index_status: Mapped[str] = mapped_column(String(24), nullable=False, default="discovered")  # discovered|indexed|failed|deleted
	last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
	deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
	error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


Index("ix_kl_documents_content_hash", DocumentRecord.content_hash)


class DocumentRegistry:
	def __init__(self):
		self.database_url = os.getenv("DATABASE_URL", "").strip()
		self.enabled = bool(self.database_url)
		self._Session = None

		if not self.enabled:
			logger.warning("DATABASE_URL not set; document registry disabled")
			return

		try:
			engine = create_engine(self.database_url, pool_pre_ping=True)
			self._Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
			Base.metadata.create_all(engine)
			logger.info("Document registry initialized")
		except Exception as e:
			self.enabled = False
			self._Session = None
			logger.error(f"Failed to initialize document registry: {e}", exc_info=True)

	def get_by_source_path(self, source_path: str) -> Optional[DocumentRecord]:
		if not self.enabled or not self._Session:
			return None
		doc_uid = stable_doc_uid(source_path)
		with self._Session() as session:
			return session.scalar(select(DocumentRecord).where(DocumentRecord.doc_uid == doc_uid))

	def upsert_discovered(
		self,
		source_path: str,
		*,
		content_hash: Optional[str],
		extract_version: Optional[str],
		chunker_version: Optional[str],
		embedding_model: Optional[str],
	) -> Tuple[str, DocumentRecord]:
		"""
		Create/update a registry record for a source_path.
		Returns (doc_uid, record).
		"""
		doc_uid = stable_doc_uid(source_path)
		if not self.enabled or not self._Session:
			# Stateless fallback
			return doc_uid, DocumentRecord(
				doc_uid=doc_uid,
				source_path=source_path,
				content_hash=content_hash,
				extract_version=extract_version,
				chunker_version=chunker_version,
				embedding_model=embedding_model,
				index_status="discovered",
			)

		now = datetime.utcnow()
		with self._Session() as session:
			rec = session.scalar(select(DocumentRecord).where(DocumentRecord.doc_uid == doc_uid))
			if rec is None:
				rec = DocumentRecord(
					doc_uid=doc_uid,
					source_path=source_path,
					content_hash=content_hash,
					extract_version=extract_version,
					chunker_version=chunker_version,
					embedding_model=embedding_model,
					index_status="discovered",
					created_at=now,
					updated_at=now,
				)
				session.add(rec)
			else:
				rec.source_path = source_path
				rec.content_hash = content_hash
				rec.extract_version = extract_version
				rec.chunker_version = chunker_version
				rec.embedding_model = embedding_model
				rec.updated_at = now
			session.commit()
			session.refresh(rec)
			return doc_uid, rec

	def mark_indexed(self, doc_uid: str):
		if not self.enabled or not self._Session:
			return
		now = datetime.utcnow()
		with self._Session() as session:
			rec = session.scalar(select(DocumentRecord).where(DocumentRecord.doc_uid == doc_uid))
			if rec:
				rec.index_status = "indexed"
				rec.last_indexed_at = now
				rec.updated_at = now
				rec.error_message = None
				rec.deleted_at = None
				session.commit()

	def mark_failed(self, doc_uid: str, message: str):
		if not self.enabled or not self._Session:
			return
		now = datetime.utcnow()
		with self._Session() as session:
			rec = session.scalar(select(DocumentRecord).where(DocumentRecord.doc_uid == doc_uid))
			if rec:
				rec.index_status = "failed"
				rec.updated_at = now
				rec.error_message = message[:4000]
				session.commit()

	def mark_deleted(self, doc_uid: str):
		if not self.enabled or not self._Session:
			return
		now = datetime.utcnow()
		with self._Session() as session:
			rec = session.scalar(select(DocumentRecord).where(DocumentRecord.doc_uid == doc_uid))
			if rec:
				rec.index_status = "deleted"
				rec.deleted_at = now
				rec.updated_at = now
				session.commit()


registry = DocumentRegistry()

