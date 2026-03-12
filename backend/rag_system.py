"""
RAG (Retrieval-Augmented Generation) System for PatriotAI Defense Hub
Integrates document indexing, vector search, and AI-powered responses
"""

import os
import logging
import time
from typing import List, Dict, Any
from datetime import datetime

try:
	# Try newer langchain import (langchain>=0.1.0)
	from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
	# Fallback to old langchain import (langchain==0.0.350)
	from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
from qdrant_client import QdrantClient
try:
	from langchain_ollama import ChatOllama, OllamaEmbeddings
	from langchain_qdrant import Qdrant as QdrantVectorStore
except ImportError:
	from langchain_community.chat_models import ChatOllama
	from langchain_community.embeddings import OllamaEmbeddings
	from langchain_community.vectorstores import Qdrant as QdrantVectorStore

# Local Ollama configuration (LLM + embeddings)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:3b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))

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
			logger.info(f"Using local Ollama LLM ({OLLAMA_LLM_MODEL}) at {OLLAMA_BASE_URL}")
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

			self.vectorstore = QdrantVectorStore(
				client=client,
				collection_name=collection_name,
				embeddings=self.embeddings,
			)
			logger.info(f"Vector store initialized (Qdrant collection={collection_name})")
		except Exception as e:
			logger.error(f"Vector store initialization failed: {e}", exc_info=True)
			self.vectorstore = None
	
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
	
	def _split_documents(self, documents):
		return RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(documents)
	
	def index_document(self, file_path: str, metadata: Dict[str, Any] = None):
		"""Returns (success: bool, message: str)."""
		try:
			if self.vectorstore is None:
				logger.warning("Vector store not initialized; skipping index")
				return False, "Vector store not initialized. Check GOOGLE_API_KEY and server logs."
			documents = self._load_document(file_path)
			if not documents:
				return False, "Could not load document (install 'unstructured' for DOC/DOCX, or check file format)."
			split_docs = self._split_documents(documents)
			if metadata:
				for d in split_docs:
					d.metadata.update(metadata)
			self.vectorstore.add_documents(split_docs)
			self.vectorstore.persist()
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
			# Search for documents with this filename in metadata
			# Use a simple search to check if any chunks exist for this filename
			if hasattr(self.vectorstore, '_collection'):
				try:
					# Query Chroma collection directly using where clause
					results = self.vectorstore._collection.get(where={"filename": filename}, limit=1)
					if results and isinstance(results, dict):
						ids = results.get("ids", [])
						is_indexed = len(ids) > 0
						if is_indexed:
							logger.debug(f"Document {filename} is indexed ({len(ids)} chunks found)")
						return is_indexed
					return False
				except Exception as coll_error:
					logger.warning(f"Chroma collection query failed for {filename}: {coll_error}")
					# Fallback to search method
					try:
						results = self.vectorstore.similarity_search("", k=1000)
						for doc in results:
							if doc.metadata.get("filename") == filename:
								logger.debug(f"Document {filename} found via search fallback")
								return True
					except Exception as search_error:
						logger.warning(f"Search fallback also failed for {filename}: {search_error}")
					return False
			else:
				# Fallback: try searching with empty query and check metadata
				try:
					results = self.vectorstore.similarity_search("", k=1000)
					for doc in results:
						if doc.metadata.get("filename") == filename:
							logger.debug(f"Document {filename} found via search")
							return True
				except Exception as search_error:
					logger.warning(f"Search failed for {filename}: {search_error}")
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
			# Try to delete documents matching the filename in metadata
			# Access Chroma collection directly for metadata-based deletion
			if hasattr(self.vectorstore, '_collection'):
				self.vectorstore._collection.delete(where={"filename": filename})
				logger.info(f"Deleted document {filename} from vector store")
				return True
			else:
				logger.warning(f"Could not access Chroma collection to delete {filename}")
				return False
		except Exception as e:
			logger.warning(f"Failed to delete document {filename} from vector store: {e}")
			# Return False but don't raise - file deletion should still proceed
			return False
	
	def search_documents(self, query: str, k: int = 3):
		try:
			if not self.vectorstore:
				logger.warning("Vector store not initialized")
				return []
			return self.vectorstore.similarity_search(query, k=k)
		except Exception as e:
			logger.error(f"Failed to search documents: {e}")
			return []
	
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
		"""
		try:
			relevant_docs = self.search_documents(query)
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
					"You are Kenya Law AI. You must answer ONLY using the text in the Context below. "
					"Do not use any other knowledge, general legal knowledge, or information from outside the Context. "
					"If the Context does not contain enough information to answer the question, say: "
					"'This information was not found in your uploaded documents.' "
					"However, if the Context clearly identifies a person by name or as an appellant (for example, '1st appellant', "
					"'2nd appellant', etc.), you may state who they are in the case and briefly summarize what happened to them in the "
					"judgment, but only if that information appears in the Context. "
					"Quote or paraphrase only from the Context. Do not add facts, cases, or principles not present in the Context.\n\n"
					f"Question: {query}\n\nContext:\n{context}\n\n"
					"Answer based strictly on the Context above:"
				)
				answer = self._invoke_with_fallback(prompt)
			else:
				answer = (
					f"No LLM configured. Based on your query, {len(relevant_docs)} relevant passage(s) were found in your uploaded documents. "
					"Configure GOOGLE_API_KEY to get answers generated from this content only."
				)

			# Unique document paths for backward compatibility; sources_detail for UI (document -> chunks)
			sources = [f"Document: {path}" for path in by_document.keys()]
			sources_detail = [
				{"document": path, "chunks": chunks}
				for path, chunks in by_document.items()
			]

			return {
				"answer": str(answer).strip(),
				"sources": sources,
				"sources_detail": sources_detail,
				"confidence": 0.85 if self.llm and relevant_docs else 0.6,
				"timestamp": datetime.now().isoformat(),
				"documents_found": len(relevant_docs),
				"web_sources": 0
			}
		except Exception as e:
			logger.error(f"Failed to generate response: {e}")
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
