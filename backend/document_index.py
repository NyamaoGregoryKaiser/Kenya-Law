import os
import logging
from typing import Dict, List, Any, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_community.embeddings import OllamaEmbeddings


logger = logging.getLogger("document_index")


def _filter_for_filename(filename: str):
	"""Build Qdrant filter for payload filename (flat key)."""
	return qmodels.Filter(
		must=[qmodels.FieldCondition(key="filename", match=qmodels.MatchValue(value=filename))]
	)


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
			point_id = str(uuid4())
			self.client.upsert(
				collection_name=self.collection_name,
				points=[
					qmodels.PointStruct(
						id=point_id,
						vector=vector,
						payload=payload,
					)
				],
			)
			logger.info(f"Upserted document {doc_id} into {self.collection_name} as point_id={point_id}")
		except Exception as e:
			logger.error(f"Failed to upsert document {doc_id} into {self.collection_name}: {e}", exc_info=True)

	def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
		"""
		Phase 2: search document-level index by query; return list of payloads (each with "filename").
		"""
		try:
			emb = self._get_embeddings()
			vector = emb.embed_query(query)
			results = self.client.search(
				collection_name=self.collection_name,
				query_vector=vector,
				limit=k,
				with_payload=True,
				with_vectors=False,
			)
			payloads = []
			for hit in results:
				payload = (hit.payload or {}).copy()
				if payload.get("filename"):
					payloads.append(payload)
			logger.info(f"Document-level search returned {len(payloads)} docs for query (k={k})")
			return payloads
		except Exception as e:
			logger.warning(f"Document-level search failed: {e}", exc_info=True)
			return []

	def delete_by_filename(self, filename: str) -> bool:
		"""Delete all points in kenyalaw_documents whose payload.filename equals filename."""
		try:
			f = _filter_for_filename(filename)
			self.client.delete(
				collection_name=self.collection_name,
				points_selector=f,
			)
			logger.info(f"Deleted document-level points for filename={filename!r} from {self.collection_name}")
			return True
		except Exception as e:
			logger.warning(f"Failed to delete from {self.collection_name} for filename={filename!r}: {e}")
			return False

	def get_sample_metadata(self, limit: int = 10) -> List[Dict[str, Any]]:
		"""
		Scroll kenyalaw_documents and return sample payloads (metadata) for inspection.
		Drops vectors and truncates master_text so you can see what fields are available for the dashboard.
		"""
		out: List[Dict[str, Any]] = []
		try:
			if not self.client.collection_exists(self.collection_name):
				return []
			records, _ = self.client.scroll(
				collection_name=self.collection_name,
				limit=limit,
				with_payload=True,
				with_vectors=False,
			)
			for rec in records:
				payload = (rec.payload or {}).copy()
				# Truncate long text for readability
				if payload.get("master_text") and len(payload["master_text"]) > 500:
					payload["master_text"] = payload["master_text"][:500] + "..."
				out.append(payload)
		except Exception as e:
			logger.warning(f"Failed to get sample metadata: {e}", exc_info=True)
		return out

	def get_year_range(self) -> tuple[Optional[int], Optional[int]]:
		"""
		Scroll kenyalaw_documents and return (min_year, max_year) from payload.year.
		Returns (None, None) if no documents or no years found.
		"""
		years: List[int] = []
		try:
			if not self.client.collection_exists(self.collection_name):
				return (None, None)
			offset = None
			while True:
				records, offset = self.client.scroll(
					collection_name=self.collection_name,
					limit=100,
					offset=offset,
					with_payload=True,
					with_vectors=False,
				)
				for rec in records:
					payload = rec.payload or {}
					y = payload.get("year")
					if y is not None:
						try:
							years.append(int(y))
						except (TypeError, ValueError):
							pass
				if offset is None:
					break
			if not years:
				return (None, None)
			return (min(years), max(years))
		except Exception as e:
			logger.warning(f"Failed to get year range: {e}", exc_info=True)
			return (None, None)

	def get_source_counts(self) -> Dict[str, Any]:
		"""
		Aggregate counts for data sources:
		- case_law.total and by_court
		- legislation.acts_in_force / repealed_statutes / total
		- kenya_gazette.total and years[]
		"""
		result: Dict[str, Any] = {
			"case_law": {"total": 0, "by_court": {}},
			"legislation": {"total": 0, "acts_in_force": 0, "repealed_statutes": 0},
			"kenya_gazette": {"total": 0, "years": []},
		}
		try:
			if not self.client.collection_exists(self.collection_name):
				return result
			offset = None
			years_set = set()
			while True:
				records, offset = self.client.scroll(
					collection_name=self.collection_name,
					limit=100,
					offset=offset,
					with_payload=True,
					with_vectors=False,
				)
				for rec in records:
					payload = rec.payload or {}
					st = payload.get("source_type")
					if st == "case_law":
						result["case_law"]["total"] += 1
						ct = payload.get("court_type") or payload.get("court")
						if ct:
							result["case_law"]["by_court"][ct] = result["case_law"]["by_court"].get(ct, 0) + 1
					elif st == "legislation":
						result["legislation"]["total"] += 1
						lt = payload.get("legislation_type") or "acts_in_force"
						if lt == "repealed_statute":
							result["legislation"]["repealed_statutes"] += 1
						else:
							result["legislation"]["acts_in_force"] += 1
					elif st == "kenya_gazette":
						result["kenya_gazette"]["total"] += 1
						gy = payload.get("gazette_year") or payload.get("year")
						if gy is not None:
							try:
								years_set.add(int(gy))
							except (TypeError, ValueError):
								pass
				if offset is None:
					break
			if years_set:
				result["kenya_gazette"]["years"] = sorted(years_set)
			return result
		except Exception as e:
			logger.warning(f"Failed to get source counts: {e}", exc_info=True)
			return result


document_indexer = DocumentIndexer()

