"""
RAG (Retrieval-Augmented Generation) System for PatriotAI Defense Hub
Integrates document indexing, vector search, and AI-powered responses
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

# Local Ollama configuration (LLM + embeddings)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:3b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))
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
		
		# Download punkt_tab if missing
		try:
			nltk.data.find('tokenizers/punkt_tab')
		except LookupError:
			logger.info("Downloading NLTK punkt_tab data (required for DOC/DOCX processing)...")
			nltk.download('punkt_tab', quiet=True, download_dir=nltk_data_dir)
			logger.info("NLTK punkt_tab downloaded successfully")
		
		# Download averaged_perceptron_tagger_eng if missing
		try:
			nltk.data.find('taggers/averaged_perceptron_tagger_eng')
		except LookupError:
			logger.info("Downloading NLTK averaged_perceptron_tagger_eng data (required for DOC/DOCX processing)...")
			nltk.download('averaged_perceptron_tagger_eng', quiet=True, download_dir=nltk_data_dir)
			logger.info("NLTK averaged_perceptron_tagger_eng downloaded successfully")
	except Exception as e:
		logger.warning(f"Could not ensure NLTK data (DOC/DOCX may fail): {e}")

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

			# Generic "<TYPE> APPEAL NO. ... 2017"
			m = re.search(r"(CIVIL|CRIMINAL)\s+APPEAL\s+NO\.?\s+[^\n]+?\d{4}", q)
			if m:
				return m.group(0)

			# "<TYPE> APPLICATION NO. E073 OF 2023"
			m = re.search(r"(CIVIL|CRIMINAL)\s+APPLICATION\s+NO\.?\s+[^\n]+?\d{4}", q)
			if m:
				return m.group(0)

			# Registry-prefixed patterns: "KISUMU CIV APP NO 39 OF 2017"
			m = re.search(r"(KISUMU|MOMBASA|NAIROBI|MALINDI)\s+[A-Z]+\s+APP(?:EAL|\.?)\s+NO\.?\s+[^\n]+?\d{4}", q)
			if m:
				return m.group(0)

			# Fallback: "<TYPE> APPEAL NO. 39" (no year)
			m = re.search(r"(CIVIL|CRIMINAL)\s+APPEAL\s+NO\.?\s+\d+", q)
			if m:
				return m.group(0)

			return None
		except Exception as e:
			logger.debug(f"Failed to extract case hint from query '{query}': {e}")
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
	
	def generate_response(self, query: str, use_web_search: bool = False) -> Dict[str, Any]:
		"""
		Generate a response using ONLY the uploaded/indexed documents.
		No external knowledge or web search is used. If no relevant documents
		are found, return a clear message without calling the LLM.
		Answer model: local Ollama only (no Gemini).
		"""
		t0 = time.time()
		try:
			# ---- Retrieval (first pass, narrow) ----
			retrieval_start = time.time()
			relevant_docs = self.search_documents(query, k=10)
			logger.info(f"retrieval pass1: {len(relevant_docs)} chunks in {time.time() - retrieval_start:.2f}s")

			# If retrieval is very weak, try a broader second pass before giving up
			if len(relevant_docs) < 3:
				retrieval2_start = time.time()
				broader_docs = self.search_documents(query, k=40)
				logger.info(f"retrieval pass2: {len(broader_docs)} chunks in {time.time() - retrieval2_start:.2f}s")
				# Prefer second-pass results only if they add something
				if len(broader_docs) > len(relevant_docs):
					relevant_docs = broader_docs

			# Bias results towards filenames matching a case hint from the query
			case_hint = self._extract_case_hint(query)
			if case_hint and relevant_docs:
				norm_hint = re.sub(r"\s+", "", case_hint).lower()

				def _fname_score(doc):
					fname = (doc.metadata.get("filename") or "").lower()
					fname_norm = re.sub(r"\s+", "", fname)
					# 0 = strong match (comes first), 1 = others
					return 0 if norm_hint and norm_hint in fname_norm else 1

				try:
					relevant_docs.sort(key=_fname_score)
					logger.info(f"case_hint applied: '{case_hint}'")
				except Exception as e:
					logger.debug(f"Failed to sort by case_hint '{case_hint}': {e}")

			# Ensure header chunks (case caption, parties) are included when any chunk from a doc is retrieved.
			header_start = time.time()
			relevant_docs = self._ensure_header_chunks(relevant_docs)
			logger.info(f"header_merge: {time.time() - header_start:.2f}s, total chunks now {len(relevant_docs)}")
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
					"If the Context clearly contains relevant information (e.g. parties, case number, issues, holdings), you MUST use it to answer, "
					"and you may logically connect and explain events as long as you do not invent facts that are not supported by the text. "
					"If the Context truly contains no discussion relevant to the question, say: "
					"'This information was not found in your uploaded documents.' "
					"Do NOT say that information is 'not explicitly named' if it actually appears in the Context (for example, party names before 'APPELLANT' or 'RESPONDENT'). "
					"Quote or paraphrase only from the Context. Do not add legal principles, cases, or facts that are not present in the Context.\n\n"
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
