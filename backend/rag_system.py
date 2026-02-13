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
from langchain_community.vectorstores import Chroma

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")
DEFAULT_GEMINI = "models/gemini-2.5-flash"
DEFAULT_GEMINI_FALLBACK = "models/gemini-1.5-pro"

def _ensure_models_prefix(value: str, default: str) -> str:
	"""
	Gemini via google-generativeai expects model ids prefixed with `models/`.
	Normalize legacy values (e.g., `gemini-1.5-pro`) to the required format.
	"""
	if not value:
		return default
	return value if value.startswith("models/") else f"models/{value}"

GOOGLE_MODEL = _ensure_models_prefix(os.getenv("GOOGLE_MODEL", DEFAULT_GEMINI), DEFAULT_GEMINI)
GOOGLE_MODEL_FALLBACK = _ensure_models_prefix(os.getenv("GOOGLE_MODEL_FALLBACK", DEFAULT_GEMINI_FALLBACK), DEFAULT_GEMINI_FALLBACK)
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))
MAX_WEB_RESULTS = int(os.getenv("MAX_WEB_RESULTS", "3"))

# Gemini LLM
LLM_OK = False
try:
	from langchain_google_genai import ChatGoogleGenerativeAI
	LLM_OK = bool(GOOGLE_API_KEY)
except Exception:
	LLM_OK = False

# Google embeddings (if available), fallback none
EMBED_OK = False
EmbeddingsClass = None
try:
	from langchain_google_genai import GoogleGenerativeAIEmbeddings
	if GOOGLE_API_KEY:
		EmbeddingsClass = GoogleGenerativeAIEmbeddings
		EMBED_OK = True
except Exception:
	EMBED_OK = False
	EmbeddingsClass = None

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
			if LLM_OK:
				self.llm = ChatGoogleGenerativeAI(model=GOOGLE_MODEL, temperature=0.1, google_api_key=GOOGLE_API_KEY)
				self.llm_fallback = ChatGoogleGenerativeAI(model=GOOGLE_MODEL_FALLBACK, temperature=0.1, google_api_key=GOOGLE_API_KEY)
				logger.info(f"Using Gemini LLM ({GOOGLE_MODEL}) with fallback ({GOOGLE_MODEL_FALLBACK})")
			else:
				logger.warning("No GOOGLE_API_KEY found, using mock responses")
				self.llm = None
				self.llm_fallback = None
		except Exception as e:
			logger.error(f"Failed to initialize Gemini LLM: {e}")
			self.llm = None
			self.llm_fallback = None
	
	def _initialize_vectorstore(self):
		try:
			if not GOOGLE_API_KEY:
				logger.warning("GOOGLE_API_KEY not set; embeddings disabled")
				self.vectorstore = None
				return
			
			if not EMBED_OK or EmbeddingsClass is None:
				logger.warning("GoogleGenerativeAIEmbeddings not available; embeddings disabled")
				self.vectorstore = None
				return
			
			# langchain-google-genai 4.2.0 requires model parameter
			# Use gemini-embedding-001 (default embedding model)
			embedding_model = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
			try:
				self.embeddings = EmbeddingsClass(google_api_key=GOOGLE_API_KEY, model=embedding_model)
				logger.info(f"Initialized embeddings with model: {embedding_model}")
				
				persist_directory = "./chroma_db"
				self.vectorstore = Chroma(persist_directory=persist_directory, embedding_function=self.embeddings)
				logger.info("Vector store initialized (Google embeddings)")
			except Exception as embed_error:
				logger.error(f"Failed to initialize embeddings: {embed_error}", exc_info=True)
				self.vectorstore = None
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
	
	def search_documents(self, query: str, k: int = 5):
		try:
			if not self.vectorstore:
				logger.warning("Vector store not initialized")
				return []
			return self.vectorstore.similarity_search(query, k=k)
		except Exception as e:
			logger.error(f"Failed to search documents: {e}")
			return []
	
	def web_search(self, query: str, num_results: int = MAX_WEB_RESULTS):
		try:
			if not SERPAPI_KEY:
				return []
			import requests
			params = {"q": query, "api_key": SERPAPI_KEY, "num": num_results, "engine": "google"}
			resp = requests.get("https://serpapi.com/search", params=params, timeout=20)
			resp.raise_for_status()
			data = resp.json()
			results = []
			for r in data.get("organic_results", [])[:num_results]:
				results.append({"title": r.get("title", ""), "snippet": r.get("snippet", ""), "url": r.get("link", "")})
			return results
		except Exception as e:
			logger.error(f"Web search failed: {e}")
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
		try:
			relevant_docs = self.search_documents(query)
			web_results = self.web_search(query) if use_web_search else []
			context = ""
			sources = []
			for doc in relevant_docs:
				context += f"\n{doc.page_content}\n"
				sources.append(f"Document: {doc.metadata.get('source', 'Unknown')}")
			for r in web_results:
				context += f"\n{r['title']}: {r['snippet']}\n"
				sources.append(f"Web: {r['url']}")

			# Trim context to avoid excessive token usage
			if len(context) > MAX_CONTEXT_CHARS:
				context = context[-MAX_CONTEXT_CHARS:]

			if self.llm:
				prompt = (
					"You are Kenya Law AI, an assistant for Kenyan legal research and jurisprudence.\n"
					"Answer the question based on the provided context, relevant case law, statutes, and your knowledge.\n\n"
					f"Question: {query}\n\nContext:\n{context}\n\n"
					"Provide an accurate, concise legal analysis with clear reasoning and, where appropriate, references to Kenyan legal principles."
				)
				answer = self._invoke_with_fallback(prompt)
			else:
				answer = (
					f"Based on the query '{query}', here's a legal research summary:\n\n"
					f"This is a mock response from Kenya Law AI. In a production system, "
					f"this would provide detailed analysis based on:\n- Indexed legal documents and judgments ({len(relevant_docs)} documents found)\n"
					f"- Any enabled web/legal research sources ({len(web_results)} sources)\n- Historical jurisprudence data\n\n"
					"The system would explain the relevant legal principles, outline key authorities, and highlight how they may apply in the Kenyan context."
				)

			return {
				"answer": str(answer).strip(),
				"sources": sources,
				"confidence": 0.85 if self.llm else 0.6,
				"timestamp": datetime.now().isoformat(),
				"documents_found": len(relevant_docs),
				"web_sources": len(web_results)
			}
		except Exception as e:
			logger.error(f"Failed to generate response: {e}")
			return {
				"answer": f"I encountered an error processing your query: {str(e)}",
				"sources": [],
				"confidence": 0.0,
				"timestamp": datetime.now().isoformat(),
				"documents_found": 0,
				"web_sources": 0
			}

rag_system = PatriotAIRAGSystem()
