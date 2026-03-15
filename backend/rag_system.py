"""
RAG (Retrieval-Augmented Generation) System for Kenya Law AI.
Integrates document indexing, vector search, and AI-powered responses.
"""

import os
import logging
import time
import re
from typing import List, Dict, Any
from datetime import datetime

try:
	# Try newer langchain import (langchain>=0.1.0)
	from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
	# Fallback to old langchain import (langchain==0.0.350)
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
from qdrant_client import QdrantClient
try:
	from qdrant_client.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
except ImportError:
	from qdrant_client.http.models import VectorParams, Distance
	try:
		from qdrant_client.http.models import Filter, FieldCondition, MatchValue
	except ImportError:
		Filter = FieldCondition = MatchValue = None  # header fetch will be skipped
from langchain_community.vectorstores import Qdrant
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings

# Phase 2: document-level index for two-stage retrieval
try:
	from document_index import document_indexer
except ImportError:
	document_indexer = None  # optional

# KL_LOOKUP + MongoDB (colleague's pipeline: KL_LOOKUP in Qdrant, documents/document_processing in MongoDB)
try:
	from mongo_documents import get_documents_info, parse_document_id_from_kl_lookup_text
except ImportError:
	get_documents_info = None
	parse_document_id_from_kl_lookup_text = None

# Local Ollama configuration (LLM + embeddings)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:3b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "24000"))
USE_KL_LOOKUP = os.getenv("USE_KL_LOOKUP", "").strip().lower() in ("1", "true", "yes")
QDRANT_KL_LOOKUP_COLLECTION = os.getenv("QDRANT_KL_LOOKUP_COLLECTION", "KL_LOOKUP")
# Structure-aware chunking: header (case title, court, parties) as its own chunk so it is retrievable.
HEADER_MAX_CHARS = int(os.getenv("RAG_HEADER_MAX_CHARS", "1500"))
JUDGMENT_MARKERS = ("JUDGMENT OF THE COURT", "JUDGMENT\n", "\n\nJUDGMENT ")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_system")

# Ensure NLTK data is available for unstructured (DOC/DOCX processing)
def _ensure_nltk_data():
	"""Download required NLTK data if missing (needed by unstructured for DOC/DOCX)."""
	try:
		import nltk
		nltk_data_dir = os.path.join(os.path.dirname(__file__), "nltk_data")
		os.makedirs(nltk_data_dir, exist_ok=True)
		nltk.data.path.insert(0, nltk_data_dir)
		# Download both punkt and punkt_tab (some envs look for tokenizers/punkt/PY3_tab)
		for resource in ("punkt", "punkt_tab"):
			try:
				nltk.data.find(f"tokenizers/{resource}")
			except LookupError:
				logger.info("Downloading NLTK %s (required for DOC/DOCX processing)...", resource)
				nltk.download(resource, quiet=True, download_dir=nltk_data_dir)
				logger.info("NLTK %s downloaded successfully", resource)
		# Download averaged_perceptron_tagger_eng if missing
		try:
			nltk.data.find("taggers/averaged_perceptron_tagger_eng")
		except LookupError:
			logger.info("Downloading NLTK averaged_perceptron_tagger_eng (required for DOC/DOCX processing)...")
			nltk.download("averaged_perceptron_tagger_eng", quiet=True, download_dir=nltk_data_dir)
			logger.info("NLTK averaged_perceptron_tagger_eng downloaded successfully")
	except Exception as e:
		logger.warning("Could not ensure NLTK data (DOC/DOCX may fail): %s", e)

_ensure_nltk_data()

class PatriotAIRAGSystem:
	def __init__(self):
		self.embeddings = None
		self.vectorstore = None
		self.llm = None
		self._qdrant_client = None
		self._qdrant_collection = None
		self._initialize_llm()
		self._initialize_vectorstore()
	
	def _initialize_llm(self):
		try:
			# Local Ollama LLM
			self.llm = ChatOllama(
				model=OLLAMA_LLM_MODEL,
				base_url=OLLAMA_BASE_URL,
				temperature=0.1,
			)
			self.llm_fallback = None
			logger.info(f"Answer generation: local Ollama only (model={OLLAMA_LLM_MODEL}, base_url={OLLAMA_BASE_URL}). No Gemini/Google.")
		except Exception as e:
			logger.error(f"Failed to initialize Ollama LLM: {e}")
			self.llm = None
			self.llm_fallback = None
	
	def _initialize_vectorstore(self):
		try:
			# Local Ollama embeddings
			self.embeddings = OllamaEmbeddings(
				model=OLLAMA_EMBED_MODEL,
				base_url=OLLAMA_BASE_URL,
			)
			logger.info(f"Initialized Ollama embeddings with model: {OLLAMA_EMBED_MODEL} at {OLLAMA_BASE_URL}")

			# Qdrant configuration
			qdrant_host = os.getenv("QDRANT_HOST", "127.0.0.1")
			qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
			collection_name = os.getenv("QDRANT_COLLECTION", "kenyalaw_cases")

			client = QdrantClient(host=qdrant_host, port=qdrant_port)

			# Ensure collection exists (Qdrant does not auto-create on first write)
			try:
				if not client.collection_exists(collection_name):
					# Get embedding dimension from model (e.g. nomic-embed-text -> 768)
					dim = len(self.embeddings.embed_query("x"))
					client.create_collection(
						collection_name=collection_name,
						vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
					)
					logger.info(f"Created Qdrant collection {collection_name} with dimension {dim}")
			else:
					logger.info(f"Qdrant collection {collection_name} already exists")
			except Exception as e:
				logger.warning(f"Could not ensure Qdrant collection {collection_name}: {e}")

			self.vectorstore = Qdrant(
				client=client,
				collection_name=collection_name,
				embeddings=self.embeddings,
			)
			self._qdrant_client = client
			self._qdrant_collection = collection_name
			logger.info(f"Vector store initialized (Qdrant collection={collection_name})")
		except Exception as e:
			logger.error(f"Vector store initialization failed: {e}", exc_info=True)
			self.vectorstore = None
			self._qdrant_client = None
			self._qdrant_collection = None
	
	def _load_document(self, file_path: str):
		try:
			ext = os.path.splitext(file_path)[1].lower()
			if ext == '.pdf':
				loader = PyPDFLoader(file_path)
			elif ext in ['.txt']:
				loader = TextLoader(file_path)
			elif ext in ['.doc', '.docx']:
				loader = UnstructuredWordDocumentLoader(file_path)
			else:
				logger.warning(f"Unsupported file type: {ext}")
				return []
			docs = loader.load()
			logger.info(f"Loaded {len(docs)} pages from {file_path}")
			return docs
		except Exception as e:
			logger.error(f"Failed to load document {file_path}: {e}")
			return []
	
	def _split_documents(self, documents, source_path: str = None):
		"""Structure-aware chunking: header (case title, court, parties) as its own chunk so party names are retrievable."""
		if not documents:
			return []
		source_path = source_path or documents[0].metadata.get("source", "Unknown")
		filename = os.path.basename(source_path) if source_path else "Unknown"
		full_text = "\n\n".join(d.page_content for d in documents).strip()
		if not full_text:
			return []
		# Header = text before "JUDGMENT OF THE COURT" / "JUDGMENT" or first HEADER_MAX_CHARS (case caption + parties).
		header_end = len(full_text)
		for marker in JUDGMENT_MARKERS:
			idx = full_text.find(marker)
			if idx >= 0:
				header_end = min(header_end, idx)
		header_end = min(header_end, HEADER_MAX_CHARS)
		header_text = full_text[:header_end].strip()
		body_text = full_text[header_end:].strip()
		result = []
		if header_text:
			header_doc = Document(
				page_content=header_text,
				metadata={
					"source": source_path,
					"filename": filename,
					"chunk_index": 0,
					"is_header": True,
				},
			)
			result.append(header_doc)
		if body_text:
			body_doc = Document(page_content=body_text, metadata={"source": source_path, "filename": filename})
			body_chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents([body_doc])
			for i, doc in enumerate(body_chunks):
				doc.metadata["chunk_index"] = len(result) + i
				doc.metadata["is_header"] = False
				doc.metadata["source"] = source_path
				doc.metadata["filename"] = filename
			result.extend(body_chunks)
		return result
	
	def index_document(self, file_path: str, metadata: Dict[str, Any] = None):
		"""Returns (success: bool, message: str)."""
		try:
			if self.vectorstore is None:
				logger.warning("Vector store not initialized; skipping index")
				return False, "Vector store not initialized. Check Ollama and Qdrant and server logs."
			documents = self._load_document(file_path)
			if not documents:
				return False, "Could not load document (install 'unstructured' for DOC/DOCX, or check file format)."
			split_docs = self._split_documents(documents, source_path=file_path)
			if metadata:
				for d in split_docs:
					d.metadata.update(metadata)
			self.vectorstore.add_documents(split_docs)
			logger.info(f"Successfully indexed {file_path}")
			return True, "Indexed for AI search."
		except Exception as e:
			logger.error(f"Failed to index document {file_path}: {e}")
			return False, str(e)
	
	def is_document_indexed(self, filename: str) -> bool:
		"""Check if a document is indexed in the vector store by filename."""
		try:
			if self.vectorstore is None:
				logger.debug(f"Vector store not initialized, {filename} not indexed")
				return False
			# Qdrant: exact, fast existence check using payload filter (avoid costly similarity_search).
			if getattr(self, "_qdrant_client", None) and getattr(self, "_qdrant_collection", None) and Filter is not None:
				try:
					metadata_key = getattr(self.vectorstore, "metadata_payload_key", "metadata")
					scroll_filter = Filter(
						must=[
							FieldCondition(key=f"{metadata_key}.filename", match=MatchValue(value=filename)),
						]
					)
					records, _ = self._qdrant_client.scroll(
						collection_name=self._qdrant_collection,
						scroll_filter=scroll_filter,
						limit=1,
						with_payload=False,
						with_vectors=False,
					)
					return bool(records)
				except Exception as e:
					logger.warning(f"Qdrant indexed-check failed for {filename}: {e}")
					# Fall through to semantic fallback

			# Fallback: semantic check (best-effort). This can be slow on large collections.
			try:
				results = self.vectorstore.similarity_search(filename, k=3)
				return any((doc.metadata or {}).get("filename") == filename for doc in results)
			except Exception as search_error:
				logger.warning(f"Search fallback failed for {filename}: {search_error}")
				return False
		except Exception as e:
			logger.warning(f"Failed to check if document {filename} is indexed: {e}")
			return False
	
	def delete_document(self, filename: str) -> bool:
		"""Delete a document from the vector store by filename. Returns True if successful."""
		try:
			if self.vectorstore is None:
				logger.warning("Vector store not initialized; cannot delete from vector store")
				return False
			# Qdrant: delete by metadata filter (fast, exact).
			if getattr(self, "_qdrant_client", None) and getattr(self, "_qdrant_collection", None) and Filter is not None:
				metadata_key = getattr(self.vectorstore, "metadata_payload_key", "metadata")
				delete_filter = Filter(
					must=[
						FieldCondition(key=f"{metadata_key}.filename", match=MatchValue(value=filename)),
					]
				)
				self._qdrant_client.delete(
					collection_name=self._qdrant_collection,
					points_selector=delete_filter,
				)
				logger.info(f"Deleted document {filename} from Qdrant vector store")
				return True

			# Fallback: if some other vectorstore is used, we can't safely delete by metadata here.
			logger.warning(f"Vector store does not support metadata delete for {filename}")
			return False
		except Exception as e:
			logger.warning(f"Failed to delete document {filename} from vector store: {e}")
			# Return False but don't raise - file deletion should still proceed
			return False
	
	def search_documents(self, query: str, k: int = 6):
		try:
			if not self.vectorstore:
				logger.warning("Vector store not initialized")
				return []
			return self.vectorstore.similarity_search(query, k=k)
		except Exception as e:
			logger.error(f"Failed to search documents: {e}")
			return []
	
	def _extract_case_hint(self, query: str) -> str | None:
		"""
		Best-effort extraction of a case-number style hint from the query,
		so we can bias retrieval towards files whose filenames match it.

		Examples it should pick up:
		- CIVIL APPEAL NO. 39 OF 2017
		- CRIMINAL APPEAL NO. 85 & 86 OF 2007
		- CIVIL APPLICATION NO. E073 OF 2023
		- KISUMU CIV APPEAL NO 39 OF 2017
		"""
		try:
			q = " ".join((query or "").upper().split())

			# Generic "<TYPE> APPEAL NO./NOS. ... 2017"
			m = re.search(r"(CIVIL|CRIMINAL)\s+APPEAL\s+NO[S]?\.?\s+[^\n]+?\d{4}", q)
			if m:
				return m.group(0)

			# "<TYPE> APPLICATION NO./NOS. E073 OF 2023"
			m = re.search(r"(CIVIL|CRIMINAL)\s+APPLICATION\s+NO[S]?\.?\s+[^\n]+?\d{4}", q)
			if m:
				return m.group(0)

			# Registry-prefixed patterns: "KISUMU CIV APP NO/NOS 39 OF 2017"
			m = re.search(r"(KISUMU|MOMBASA|NAIROBI|MALINDI)\s+[A-Z]+\s+APP(?:EAL|\.?)\s+NO[S]?\.?\s+[^\n]+?\d{4}", q)
			if m:
				return m.group(0)

			# Fallback: "<TYPE> APPEAL NO./NOS. 39" (no year)
			m = re.search(r"(CIVIL|CRIMINAL)\s+APPEAL\s+NO[S]?\.?\s+\d+", q)
			if m:
				return m.group(0)

			return None
		except Exception as e:
			logger.debug(f"Failed to extract case hint from query '{query}': {e}")
			return None

	def _extract_filename_from_query(self, query: str) -> str | None:
		"""Extract a filename (e.g. '85 & 86.07.doc') from the query when the user refers to a specific document."""
		try:
			if not query or not query.strip():
				return None
			# The backend rewrites queries (role/tone preamble). To avoid capturing that whole sentence,
			# extract the filename from the *last* segment after sentence-like punctuation.
			segment = re.split(r"[.?!]\s+", query.strip())[-1]
			# If split produced nothing useful, fall back to full query.
			haystack = segment if segment else query
			# Find the last filename-like substring in the segment/query.
			matches = re.findall(r"([A-Za-z0-9_\s&.\-()]+?\.(?:docx?|pdf|txt))", haystack, re.IGNORECASE)
			if not matches:
				# Fallback to searching the whole query
				matches = re.findall(r"([A-Za-z0-9_\s&.\-()]+?\.(?:docx?|pdf|txt))", query, re.IGNORECASE)
			if not matches:
				return None
			# Prefer a match that contains digits or '&' (common in your filenames), and prefer the last one.
			candidates = [m for m in matches if re.search(r"[\d&]", m)]
			chosen = (candidates[-1] if candidates else matches[-1])
			fname = chosen
			if not m:
				return None
			fname = fname.strip().strip("'\"`").strip().rstrip(".")
			if not fname:
				return None
			return fname
		except Exception as e:
			logger.debug(f"Failed to extract filename from query: {e}")
			return None

	def _ensure_header_chunks(self, relevant_docs: List[Document]) -> List[Document]:
		"""For each document in results, ensure its header chunk (case caption, parties) is included so party names are in context."""
		if not relevant_docs or not getattr(self, "_qdrant_client", None) or not getattr(self, "_qdrant_collection", None):
			return relevant_docs
		if Filter is None or FieldCondition is None or MatchValue is None:
			return relevant_docs
		sources_with_header = {doc.metadata.get("source") for doc in relevant_docs if doc.metadata.get("is_header") or doc.metadata.get("chunk_index") == 0}
		unique_sources = {doc.metadata.get("source", "Unknown") for doc in relevant_docs}
		missing = unique_sources - sources_with_header
		if not missing:
			return relevant_docs
		# LangChain Qdrant stores payload as page_content + metadata (nested under "metadata" key).
		content_key = getattr(self.vectorstore, "content_payload_key", "page_content")
		metadata_key = getattr(self.vectorstore, "metadata_payload_key", "metadata")
		header_docs = []
		for source in missing:
			try:
				scroll_filter = Filter(must=[
					FieldCondition(key=f"{metadata_key}.source", match=MatchValue(value=source)),
					FieldCondition(key=f"{metadata_key}.chunk_index", match=MatchValue(value=0)),
				])
				records, _ = self._qdrant_client.scroll(
					collection_name=self._qdrant_collection,
					scroll_filter=scroll_filter,
					limit=1,
					with_payload=True,
					with_vectors=False,
				)
				if records and len(records) > 0:
					point = records[0]
					payload = point.payload or {}
					content = payload.get(content_key) or payload.get("page_content", "")
					meta = payload.get(metadata_key) or payload
					if isinstance(meta, dict):
						meta = dict(meta)
					else:
						meta = {}
					header_docs.append(Document(page_content=content, metadata=meta))
					logger.debug(f"Included header chunk for source: {source[:80]}...")
			except Exception as e:
				logger.debug(f"Could not fetch header for source {source[:50]}...: {e}")
		# Prepend header chunks so they appear before body chunks in context.
		return header_docs + relevant_docs

	def _query_definition_terms(self, query: str) -> List[str]:
		"""Extract terms the user is asking about (e.g. for 'definition of written law') so we can prioritize chunks containing them."""
		q = (query or "").strip().lower()
		terms: List[str] = []
		# Quoted strings: "written law" or 'written law'
		for m in re.findall(r"[\"']([^\"']{2,50})[\"']", query or "", re.IGNORECASE):
			terms.append(m.strip())
		# After "definition of X" or "meaning of X" or "what is X" (allow letters, spaces, digits for Act names)
		for pattern in [r"definition\s+of\s+([a-z0-9\s]+?)(?:\s+under|\s+in|\.|$)", r"meaning\s+of\s+([a-z0-9\s]+?)(?:\s+under|\s+in|\.|$)", r"what\s+is\s+(?:the\s+)?([a-z0-9\s]+?)(?:\s+under|\s+in|\.|\?|$)"]:
			m = re.search(pattern, q, re.IGNORECASE)
			if m:
				t = m.group(1).strip()
				if len(t) > 2 and t not in ("the", "a", "an"):
					terms.append(t)
		return list(dict.fromkeys(terms))  # unique, order preserved

	def _prioritize_chunks_by_terms(self, query: str, docs: List[Document]) -> List[Document]:
		"""Put chunks that contain the query's key terms (e.g. 'written law') first so they are not truncated out of context."""
		terms = self._query_definition_terms(query)
		if not terms:
			return docs
		def score(doc: Document) -> int:
			raw = (doc.page_content or "").lower()
			# Normalize whitespace so "written law" matches "written  law" or "written\nlaw" from PDFs
			text = re.sub(r"\s+", " ", raw)
			total = 0
			for t in terms:
				t_lower = t.lower().strip()
				t_norm = re.sub(r"\s+", " ", t_lower)
				if t_norm in text:
					total += 2  # exact phrase (after normalizing)
				elif len(t_norm.split()) > 1 and all(w in text for w in t_norm.split() if len(w) > 1):
					total += 1  # all words present
			return total
		return sorted(docs, key=lambda d: -score(d))

	def _put_definition_chunk_first(self, query: str, docs: List[Document]) -> List[Document]:
		"""For 'definition of X' queries, move the chunk that contains 'X means—' or '"X" means' to the very start so the LLM always sees it."""
		terms = self._query_definition_terms(query)
		if not terms or not docs:
			return docs
		for term in terms:
			term_esc = re.escape(term)
			# Match "'written law' means—" or '"written law" means' or "written law means:" etc.
			pattern = rf"[\"']?{term_esc}[\"']?\s+means\s*[—\-:\s]"
			for i, doc in enumerate(docs):
				content = (doc.page_content or "")
				if re.search(pattern, content, re.IGNORECASE):
					if i == 0:
						return docs
					# Include next chunk if same document (often the (a)(b)(c) list)
					first = [doc]
					src = doc.metadata.get("source")
					if i + 1 < len(docs) and docs[i + 1].metadata.get("source") == src:
						first.append(docs[i + 1])
					rest = [d for j, d in enumerate(docs) if j != i and j != i + 1]
					return first + rest
		return docs

	def _guess_filename_from_case_hint(self, case_hint: str) -> str | None:
		"""Best-effort guess of a filename corresponding to a case hint string, using semantic search."""
		try:
			if not self.vectorstore or not case_hint:
				return None
			# Search using the case hint alone to surface likely matching files
			candidates = self.vectorstore.similarity_search(case_hint, k=20)
			if not candidates:
				return None
			norm_hint = re.sub(r"\s+", "", case_hint).lower()
			digits = re.findall(r"\d+", case_hint)
			best_fname = None
			best_score = None
			for doc in candidates:
				fname = (doc.metadata.get("filename") or "").lower()
				if not fname:
					continue
				fname_norm = re.sub(r"\s+", "", fname)
				score = 0
				# strong boost for near-exact text match in filename
				if norm_hint and norm_hint in fname_norm:
					score -= 3
				# boost when all number groups from the case hint appear in the filename
				if digits and all(d in fname for d in digits):
					score -= 2
				elif digits and any(d in fname for d in digits):
					score -= 1
				if best_score is None or score < best_score:
					best_score = score
					best_fname = fname
			return best_fname
		except Exception as e:
			logger.debug(f"Failed to guess filename from case_hint '{case_hint}': {e}")
			return None
	
	def _fetch_all_chunks_for_filename(self, filename: str) -> List[Document]:
		"""
		Fetch all chunks for a given filename directly from Qdrant.
		Tries metadata.filename first, then top-level filename (in case payload is flat).
		"""
		if not getattr(self, "_qdrant_client", None) or not getattr(self, "_qdrant_collection", None):
			return []
		if Filter is None or FieldCondition is None or MatchValue is None:
			return []

		metadata_key = getattr(self.vectorstore, "metadata_payload_key", "metadata")
		content_key = getattr(self.vectorstore, "content_payload_key", "page_content")

		def _scroll_and_collect(key: str) -> List[Document]:
			all_docs: List[Document] = []
			next_offset = None
			max_chunks = 40
			try:
				scroll_filter = Filter(
					must=[FieldCondition(key=key, match=MatchValue(value=filename))],
				)
				while True:
					records, next_offset = self._qdrant_client.scroll(
						collection_name=self._qdrant_collection,
						scroll_filter=scroll_filter,
						limit=10,
						with_payload=True,
						with_vectors=False,
						offset=next_offset,
					)
					if not records:
						break
					for point in records:
						payload = point.payload or {}
						content = payload.get(content_key) or payload.get("page_content", "")
						meta = payload.get(metadata_key) or payload
						if isinstance(meta, dict):
							meta = dict(meta)
						else:
							meta = {}
						# If payload is flat, ensure filename is in metadata for by_document grouping
						if "filename" not in meta and "filename" in payload:
							meta = dict(meta, filename=payload["filename"], source=payload.get("source", ""))
						all_docs.append(Document(page_content=content, metadata=meta))
						if len(all_docs) >= max_chunks:
							break
					if not next_offset or len(all_docs) >= max_chunks:
						break
			except Exception as e:
				logger.debug(f"Scroll with key={key} for filename={filename!r}: {e}")
			return all_docs

		# Try nested key first (metadata.filename), then top-level (filename)
		all_docs = _scroll_and_collect(f"{metadata_key}.filename")
		if not all_docs:
			all_docs = _scroll_and_collect("filename")
		if not all_docs:
			logger.warning(f"No chunks found in Qdrant for filename {filename!r}; check that document is indexed.")
		else:
			logger.info(f"Fetched {len(all_docs)} chunks from Qdrant for filename={filename!r}")
		return all_docs

	def web_search(self, query: str, num_results: int = 0):
		# Web search disabled; answers are based only on uploaded documents.
			return []

	def _invoke_with_fallback(self, prompt: str) -> str:
		# Try primary model, then fallback on 429 or quota errors
		try:
			response = self.llm.invoke(prompt)
			# Extract only the content, not the metadata
			return response.content if hasattr(response, 'content') else str(response)
		except Exception as e:
			msg = str(e).lower()
			if any(x in msg for x in ["429", "quota", "rate", "per minute", "per day"]) and getattr(self, 'llm_fallback', None):
				logger.warning("Primary model quota hit; switching to fallback model")
				try:
					response = self.llm_fallback.invoke(prompt)
					# Extract only the content, not the metadata
					return response.content if hasattr(response, 'content') else str(response)
				except Exception as e2:
					logger.error(f"Fallback model also failed: {e2}")
					raise
			else:
				raise
	
	def _generate_response_via_kl_lookup(self, query: str) -> Dict[str, Any] | None:
		"""Use Qdrant KL_LOOKUP collection + MongoDB for search and references. Returns None to fall back to default path."""
		if not self.embeddings or get_documents_info is None or parse_document_id_from_kl_lookup_text is None:
			return None
		kl_collection = QDRANT_KL_LOOKUP_COLLECTION
		client = self._qdrant_client
		if not client:
			qdrant_host = os.getenv("QDRANT_HOST", "127.0.0.1")
			qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
			client = QdrantClient(host=qdrant_host, port=qdrant_port)
		try:
			if not client.collection_exists(kl_collection):
				return None
		except Exception:
			return None
		# Embed query and search KL_LOOKUP
		query_vector = self.embeddings.embed_query(query)
		k = 10
		try:
			results = client.search(
				collection_name=kl_collection,
				query_vector=query_vector,
				limit=k,
				with_payload=True,
				with_vectors=False,
			)
		except Exception as e:
			logger.warning("KL_LOOKUP search failed: %s", e)
			return None
		if not results:
			return None
		# Build context from payload["text"] and collect document_ids
		rows: List[tuple] = []  # (doc_id or "", text)
		for hit in results:
			payload = hit.payload or {}
			text = payload.get("text") or ""
			if not text.strip():
				continue
			doc_id = payload.get("document_id") or payload.get("collection_id") or parse_document_id_from_kl_lookup_text(text) or ""
			rows.append((doc_id, text))
		if not rows:
			return None
		document_ids = [r[0] for r in rows if r[0]]
		context = "\n\n".join(r[1] for r in rows)
		if len(context) > MAX_CONTEXT_CHARS:
			context = context[:MAX_CONTEXT_CHARS]
		# Resolve document names from MongoDB
		doc_info = get_documents_info(list(dict.fromkeys(document_ids))) if document_ids else {}
		# Build by_document for sources_detail: use document_name from MongoDB when available
		by_document: Dict[str, List[str]] = {}
		for doc_id, text in rows:
			label = (doc_info.get(doc_id, {}).get("document_name") or doc_id) if doc_id else "Unknown"
			if label not in by_document:
				by_document[label] = []
			by_document[label].append(text[:500] + ("..." if len(text) > 500 else ""))
		# Generate answer
		if self.llm:
			prompt = (
				"You are a Kenyan legal research assistant. Use ONLY the passages in the Context below to answer the question. "
				"Do not use any external knowledge or web search. "
				"If ANY part of the Context answers or partly answers the question, you MUST give that answer. "
				"Only say 'This information was not found in your uploaded documents' if no passage is relevant. "
				"Quote or paraphrase only from the Context.\n\n"
				f"Question: {query}\n\nContext:\n{context}\n\nAnswer based strictly on the Context above:"
			)
			answer = self._invoke_with_fallback(prompt)
		else:
			answer = f"Based on your query, {len(results)} relevant document(s) were found. Start Ollama to get answers from this content."
		sources = [f"Document: {path}" for path in by_document.keys()]
		sources_detail = [{"document": path, "chunks": chunks} for path, chunks in by_document.items()]
		confidence = min(0.35 + (len(results) - 1) * 0.1, 0.85)
		logger.info("Retrieval path: KL_LOOKUP + MongoDB (%d docs)", len(by_document))
		return {
			"answer": str(answer).strip(),
			"sources": sources,
			"sources_detail": sources_detail,
			"confidence": round(confidence, 2),
			"timestamp": datetime.now().isoformat(),
			"documents_found": len(results),
			"web_sources": 0,
		}

	def generate_response(self, query: str, use_web_search: bool = False) -> Dict[str, Any]:
		"""
		Generate a response using ONLY the uploaded/indexed documents.
		No external knowledge or web search is used. If no relevant documents
		are found, return a clear message without calling the LLM.
		Answer model: local Ollama only (no Gemini).
		"""
		t0 = time.time()
		try:
			# KL_LOOKUP + MongoDB path (colleague's pipeline)
			if USE_KL_LOOKUP:
				try:
					result = self._generate_response_via_kl_lookup(query)
					if result is not None:
						result["timestamp"] = datetime.now().isoformat()
						logger.info(f"total /api/query (KL_LOOKUP): {time.time() - t0:.2f}s")
						return result
				except Exception as e:
					logger.warning("KL_LOOKUP path failed, falling back to default: %s", e)
			# If the query explicitly mentions a filename (e.g. "85 & 86.07.doc"), fetch that document's chunks first
			relevant_docs: List[Document] = []
			used_filename_direct = False
			used_phase2 = False
			filename_in_query = self._extract_filename_from_query(query)
			if filename_in_query:
				logger.info(f"Filename extracted from query: {filename_in_query!r}")
				docs_by_name = self._fetch_all_chunks_for_filename(filename_in_query)
				if docs_by_name:
					relevant_docs = docs_by_name
					used_filename_direct = True
					logger.info(f"Using {len(relevant_docs)} chunks from filename mentioned in query: {filename_in_query!r}")
				else:
					logger.warning(f"No chunks found for filename {filename_in_query!r}; falling back to semantic search.")

			if not relevant_docs:
				# Prefer Phase 2 (document-level index) for all queries; fall back to chunk search only when Phase 2 returns nothing.
				# ---- Phase 2: document-level search then fetch chunks for top docs ----
				if document_indexer is not None:
					try:
						phase2_start = time.time()
						doc_payloads = document_indexer.search(query, k=5)
						seen_keys: set = set()
						phase2_docs: List[Document] = []
						for payload in doc_payloads:
							fname = payload.get("filename") or payload.get("doc_id")
							if not fname:
								continue
							chunks = self._fetch_all_chunks_for_filename(fname)
							for doc in chunks:
								key = (doc.metadata.get("source", ""), doc.metadata.get("chunk_index"))
								if key not in seen_keys:
									seen_keys.add(key)
									phase2_docs.append(doc)
						if phase2_docs:
							relevant_docs = phase2_docs
							used_phase2 = True
							logger.info(f"Phase 2 retrieval: {len(relevant_docs)} chunks from {len(doc_payloads)} doc(s) in {time.time() - phase2_start:.2f}s")
					except Exception as e:
						logger.warning(f"Phase 2 retrieval failed, falling back to chunk search: {e}")

				if not relevant_docs:
					# ---- Fallback: retrieval from chunk index (first pass, narrow) ----
					retrieval_start = time.time()
					relevant_docs = self.search_documents(query, k=10)
					logger.info(f"retrieval pass1: {len(relevant_docs)} chunks in {time.time() - retrieval_start:.2f}s")

			# If retrieval is very weak, try a broader second pass before giving up (only when not filename-directed and not Phase 2)
			used_chunk_pass2 = False
			if not filename_in_query and not used_phase2 and len(relevant_docs) < 3:
				retrieval2_start = time.time()
				broader_docs = self.search_documents(query, k=40)
				logger.info(f"retrieval pass2: {len(broader_docs)} chunks in {time.time() - retrieval2_start:.2f}s")
				# Prefer second-pass results only if they add something
				if len(broader_docs) > len(relevant_docs):
					relevant_docs = broader_docs
					used_chunk_pass2 = True

			# Log which retrieval path was used (for debugging and tuning)
			if used_filename_direct:
				logger.info("Retrieval path: filename-directed")
			elif used_phase2:
				logger.info("Retrieval path: Phase 2 (document-level index)")
			elif used_chunk_pass2:
				logger.info("Retrieval path: chunk search (kenyalaw_cases) + pass2")
			else:
				logger.info("Retrieval path: chunk search (kenyalaw_cases)")

			# Bias results towards filenames matching a case hint (skip when we already used a filename from the query)
			case_hint = self._extract_case_hint(query)
			case_filename_for_expansion = None
			if not used_filename_direct and case_hint and relevant_docs:
				norm_hint = re.sub(r"\s+", "", case_hint).lower()

				def _fname_score(doc):
					fname = (doc.metadata.get("filename") or "").lower()
					fname_norm = re.sub(r"\s+", "", fname)
					# 0 = strong match (comes first), 1 = others
					return 0 if norm_hint and norm_hint in fname_norm else 1

				try:
					relevant_docs.sort(key=_fname_score)
					logger.info(f"case_hint applied: '{case_hint}'")
					# First doc after sorting is our best filename candidate
					top_fname = (relevant_docs[0].metadata.get("filename") or "").strip()
					if top_fname:
						case_filename_for_expansion = top_fname
				except Exception as e:
					logger.debug(f"Failed to sort by case_hint '{case_hint}': {e}")

			# If we still don't have a filename candidate, try guessing from case hint
			if not used_filename_direct and case_hint and not case_filename_for_expansion:
				guessed = self._guess_filename_from_case_hint(case_hint)
				if guessed:
					case_filename_for_expansion = guessed
					logger.info(f"case_hint '{case_hint}' guessed filename '{guessed}' for expansion")

			# If we have a good filename candidate for this query, pull more chunks for that file
			if not used_filename_direct and case_filename_for_expansion:
				additional = self._fetch_all_chunks_for_filename(case_filename_for_expansion)
				if additional:
					# Merge, preferring unique (source, chunk_index) combinations
					seen_keys = set()
					merged: List[Document] = []
					for doc in additional + relevant_docs:
						src = doc.metadata.get("source", "")
						idx = doc.metadata.get("chunk_index")
						key = (src, idx)
						if key in seen_keys:
							continue
						seen_keys.add(key)
						merged.append(doc)
					relevant_docs = merged

			# Ensure header chunks (case caption, parties) are included when any chunk from a doc is retrieved.
			header_start = time.time()
			relevant_docs = self._ensure_header_chunks(relevant_docs)
			logger.info(f"header_merge: {time.time() - header_start:.2f}s, total chunks now {len(relevant_docs)}")
			# Put chunks that contain the asked-for terms (e.g. "written law") first so they survive context truncation
			relevant_docs = self._prioritize_chunks_by_terms(query, relevant_docs)
			# For "definition of X" queries, ensure the chunk containing "X means—" is at the very start
			relevant_docs = self._put_definition_chunk_first(query, relevant_docs)
			# Documents-only: do not use web search for the answer
			context = ""
			# Group chunks by document path so we can return each document once with its chunks
			by_document: Dict[str, List[str]] = {}
			for doc in relevant_docs:
				source_path = doc.metadata.get("source", "Unknown")
				context += f"\n{doc.page_content}\n"
				if source_path not in by_document:
					by_document[source_path] = []
				by_document[source_path].append(doc.page_content.strip())

			# No relevant documents: do not call the LLM; answer only from uploaded data
			if not relevant_docs or not context.strip():
				logger.info(f"total /api/query (no docs): {time.time() - t0:.2f}s")
				return {
					"answer": (
						"This information was not found in your uploaded documents. "
						"Answers are based only on the documents you have indexed. "
						"Please upload relevant legal documents or rephrase your question to match the content of your uploads."
					),
					"sources": [],
					"sources_detail": [],
					"confidence": 0.0,
					"timestamp": datetime.now().isoformat(),
					"documents_found": 0,
					"web_sources": 0
				}

			# Trim context to avoid excessive token usage
			if len(context) > MAX_CONTEXT_CHARS:
				context = context[:MAX_CONTEXT_CHARS]

			if self.llm:
				prompt = (
					"You are a Kenyan legal research assistant. Use ONLY the passages in the Context below to answer the question. "
					"Do not use any external knowledge or web search. "
					"If the question asks for a definition and the Context contains a definition (e.g. a phrase like 'X means—' or 'X means:' followed by a list or explanation), you MUST provide that definition from the Context—do NOT say the information was not found. "
					"For any question, if ANY part of the Context answers or partly answers it (definition, section, parties, holdings), you MUST give that answer. "
					"Only say 'This information was not found in your uploaded documents' if you have read the whole Context and no passage in it is relevant. "
					"Quote or paraphrase only from the Context. Do not add facts not present in the Context.\n\n"
					f"Question: {query}\n\nContext:\n{context}\n\n"
					"Answer based strictly on the Context above:"
				)
				gen_start = time.time()
				answer = self._invoke_with_fallback(prompt)
				logger.info(f"generation (Ollama {OLLAMA_LLM_MODEL}): {time.time() - gen_start:.2f}s")
			else:
				answer = (
					f"No LLM configured. Based on your query, {len(relevant_docs)} relevant passage(s) were found in your uploaded documents. "
					"Start Ollama locally to get answers generated from this content."
				)

			# Unique document paths for backward compatibility; sources_detail for UI (document -> chunks)
			sources = [f"Document: {path}" for path in by_document.keys()]
			sources_detail = [
				{"document": path, "chunks": chunks}
				for path, chunks in by_document.items()
			]

			# Dynamic confidence from retrieval strength: few chunks -> low, more chunks -> higher
			num_chunks = len(relevant_docs)
			if num_chunks < 2:
				confidence = 0.35  # low: weak retrieval
			else:
				confidence = min(0.35 + (num_chunks - 1) * 0.125, 0.85)
			if not self.llm:
				confidence = min(confidence, 0.6)

			logger.info(f"total /api/query: {time.time() - t0:.2f}s")
			return {
				"answer": str(answer).strip(),
				"sources": sources,
				"sources_detail": sources_detail,
				"confidence": round(confidence, 2),
				"timestamp": datetime.now().isoformat(),
				"documents_found": num_chunks,
				"web_sources": 0
			}
		except Exception as e:
			logger.error(f"Failed to generate response after {time.time() - t0:.2f}s: {e}")
			return {
				"answer": f"I encountered an error processing your query: {str(e)}",
				"sources": [],
				"sources_detail": [],
				"confidence": 0.0,
				"timestamp": datetime.now().isoformat(),
				"documents_found": 0,
				"web_sources": 0
			}

rag_system = PatriotAIRAGSystem()
