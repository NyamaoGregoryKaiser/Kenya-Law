import os
import logging
from typing import Dict

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_community.embeddings import OllamaEmbeddings


logger = logging.getLogger("document_index")


class DocumentIndexer:
	def __init__(self):
		qdrant_host = os.getenv("QDRANT_HOST", "127.0.0.1")
		qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
		self.collection_name = os.getenv("KENYALAW_DOC_COLLECTION", "kenyalaw_documents")

		self.client = QdrantClient(host=qdrant_host, port=qdrant_port)

		# Ensure collection exists (simple single-vector config)
		try:
			if not self.client.collection_exists(self.collection_name):
				# Infer embedding dimension by embedding a dummy string
				emb = self._get_embeddings()
				vec = emb.embed_query("kenyalaw-documents-init")
				dim = len(vec)
				self.client.recreate_collection(
					collection_name=self.collection_name,
					vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
				)
				logger.info(f"Created Qdrant collection {self.collection_name} (dim={dim}) for document-level index")
		except Exception as e:
			logger.error(f"Failed to ensure document collection {self.collection_name}: {e}", exc_info=True)

	def _get_embeddings(self) -> OllamaEmbeddings:
		base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
		model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
		return OllamaEmbeddings(model=model, base_url=base_url)

	def upsert_document(self, doc_id: str, master_text: str, payload: Dict) -> None:
		"""
		Upsert a single document-level vector (master_text) into kenyalaw_documents.
		"""
		try:
			emb = self._get_embeddings()
			vector = emb.embed_query(master_text)
			self.client.upsert(
				collection_name=self.collection_name,
				points=[
					qmodels.PointStruct(
						id=doc_id,
						vector=vector,
						payload=payload,
					)
				],
			)
			logger.info(f"Upserted document {doc_id} into {self.collection_name}")
		except Exception as e:
			logger.error(f"Failed to upsert document {doc_id} into {self.collection_name}: {e}", exc_info=True)


document_indexer = DocumentIndexer()

