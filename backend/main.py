"""
PatriotAI Defense Hub - Open WebUI Extension
A specialized defense intelligence platform for Kenya's defense sector
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging
import time
from datetime import datetime
import shutil
import json

# Load environment from .env files
try:
	from dotenv import load_dotenv
	# Try project root .env then backend/.env
	load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
	load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
except Exception as _e:
	logging.warning("dotenv not loaded: %s", _e)

# Import RAG system
from rag_system import rag_system
from prompts_store import filter_prompts_for_role, find_prompt_by_id, upsert_prompt, soft_delete_prompt
from legal_metadata import extract_legal_metadata, build_master_text
from document_index import document_indexer
from db_conversations import (
	create_conversation,
	list_conversations,
	get_conversation,
	get_messages,
	add_message,
	update_conversation_title,
	delete_conversation,
	title_from_first_query,
)

# Import Open WebUI components
try:
	from open_webui import create_app
	from open_webui.auth import get_current_user
	from open_webui.models import User
except ImportError:
	# Fallback for development
	logging.warning("Open WebUI not found, using mock components")
	def create_app():
		return FastAPI(title="PatriotAI Defense Hub")
	
	def get_current_user():
		return {"id": "1", "role": "admin", "name": "Demo User"}

# Initialize FastAPI app
app = create_app()

# Add request logging middleware to debug DELETE requests
@app.middleware("http")
async def log_requests(request, call_next):
	logging.info(f"Incoming request: {request.method} {request.url.path}")
	response = await call_next(request)
	logging.info(f"Response: {request.method} {request.url.path} -> {response.status_code}")
	return response

# Log environment status at startup
logging.info("Answer model for /api/query: local Ollama only (no Gemini/Google). See rag_system logs for model name.")
logging.info(f"GOOGLE_API_KEY present: {bool(os.getenv('GOOGLE_API_KEY'))} (unused for answers)")
logging.info(f"SERPAPI_API_KEY present: {bool(os.getenv('SERPAPI_API_KEY'))}")


def _index_status_path(upload_dir: str) -> str:
	return os.path.join(upload_dir, ".index_status.json")


def _metrics_path() -> str:
	data_dir = os.path.join(os.path.dirname(__file__), "data")
	os.makedirs(data_dir, exist_ok=True)
	return os.path.join(data_dir, "metrics.json")


def _load_index_status(upload_dir: str) -> dict:
	"""Load last-known indexing status for filenames (fast, avoids Qdrant calls on /api/documents)."""
	path = _index_status_path(upload_dir)
	try:
		if not os.path.exists(path):
			return {}
		with open(path, "r", encoding="utf-8") as f:
			data = json.load(f)
		return data if isinstance(data, dict) else {}
	except Exception as e:
		logging.warning(f"Failed to read index status file {path}: {e}")
		return {}


def _save_index_status(upload_dir: str, data: dict) -> None:
	path = _index_status_path(upload_dir)
	tmp = f"{path}.tmp"
	try:
		with open(tmp, "w", encoding="utf-8") as f:
			json.dump(data, f)
		os.replace(tmp, path)
	except Exception as e:
		logging.warning(f"Failed to write index status file {path}: {e}")
		try:
			if os.path.exists(tmp):
				os.remove(tmp)
		except Exception:
			pass

# Add CORS middleware
app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:3000",
		"http://localhost:8080",
		"https://172.20.16.155",
		"http://172.20.16.155",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Pydantic models
class HistoryTurn(BaseModel):
	role: str  # 'user' or 'assistant'
	content: str

class QueryRequest(BaseModel):
	query: str
	use_web_search: bool = False
	conversation_id: Optional[str] = None  # when set, messages are persisted and history loaded from DB
	context_documents: Optional[List[str]] = None
	system_prompt: Optional[str] = None
	user_rank: Optional[str] = None
	history: Optional[List[HistoryTurn]] = None
	
class SourceDetail(BaseModel):
	document: str
	chunks: List[str]

class QueryResponse(BaseModel):
	answer: str
	sources: List[str]
	confidence: float
	timestamp: datetime
	rank_applied: Optional[str] = None
	prompt_used: Optional[str] = None
	sources_detail: Optional[List[SourceDetail]] = None
	conversation_id: Optional[str] = None  # set when conversation_id was in request or new conv created

class DocumentUploadResponse(BaseModel):
	document_id: str
	filename: str
	status: str
	indexed: bool
	index_message: Optional[str] = None

class DocumentItem(BaseModel):
	filename: str
	size: int
	uploaded_at: str
	indexed: bool = False
	indexed_at: Optional[str] = None

class DocumentListResponse(BaseModel):
	documents: List[DocumentItem]
	total_uploaded: int = 0
	total_indexed: int = 0

class MapEvent(BaseModel):
	id: str
	title: str
	description: str
	latitude: float
	longitude: float
	event_type: str
	severity: str
	timestamp: datetime

class Prompt(BaseModel):
	id: str
	title: str
	description: str
	prompt_text: str
	visibility_scope: str = Field(description="global|unit|user")
	roles_allowed: List[str] = Field(default_factory=list)
	created_by: str
	version: int = 1
	is_active: bool = True
	created_at: Optional[str] = None
	updated_at: Optional[str] = None

class PromptListResponse(BaseModel):
	prompts: List[Prompt]

# Security
security = HTTPBearer()

# Routes
@app.get("/")
async def root():
	return {
		"message": "Kenya Law AI API",
		"version": "1.0.0",
		"description": "AI-powered legal research and analysis for Kenya's justice sector"
	}

@app.get("/api/prompts", response_model=PromptListResponse)
async def list_prompts(current_user: dict = Depends(get_current_user)):
	role = current_user.get('role', 'analyst')
	items = filter_prompts_for_role(role)
	return {"prompts": items}

@app.post("/api/prompts", response_model=Prompt)
async def create_or_update_prompt(prompt: Prompt, current_user: dict = Depends(get_current_user)):
	role = current_user.get('role', 'analyst')
	if role != 'admin':
		raise HTTPException(status_code=403, detail="Only admin can create or update prompts")
	data = upsert_prompt(prompt.dict())
	return data

@app.delete("/api/prompts/{pid}")
async def delete_prompt(pid: str, current_user: dict = Depends(get_current_user)):
	role = current_user.get('role', 'analyst')
	if role != 'admin':
		raise HTTPException(status_code=403, detail="Only admin can delete prompts")
	ok = soft_delete_prompt(pid)
	if not ok:
		raise HTTPException(status_code=404, detail="Prompt not found or already inactive")
	return {"status": "deleted", "id": pid}

# ---------- Conversation history (persistent per-user) ----------
@app.post("/api/conversations")
async def api_create_conversation(current_user: dict = Depends(get_current_user)):
	"""Create a new conversation for the current user."""
	user_id = str(current_user.get("id", "1"))
	conv = create_conversation(user_id=user_id, title="New Chat")
	return conv

@app.get("/api/conversations")
async def api_list_conversations(current_user: dict = Depends(get_current_user)):
	"""List conversations for the current user, newest first."""
	user_id = str(current_user.get("id", "1"))
	return {"conversations": list_conversations(user_id=user_id)}

@app.get("/api/conversations/{conversation_id}")
async def api_get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
	"""Get one conversation with its messages."""
	user_id = str(current_user.get("id", "1"))
	conv = get_conversation(conversation_id, user_id)
	if not conv:
		raise HTTPException(status_code=404, detail="Conversation not found")
	messages = get_messages(conversation_id, user_id)
	return {"conversation": conv, "messages": messages}

@app.delete("/api/conversations/{conversation_id}")
async def api_delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
	"""Delete a conversation and all its messages."""
	user_id = str(current_user.get("id", "1"))
	if not delete_conversation(conversation_id, user_id):
		raise HTTPException(status_code=404, detail="Conversation not found")
	return {"status": "deleted", "id": conversation_id}


def _rewrite_query_if_followup(query: str, history: Optional[List[dict]] = None) -> str:
	"""
	Simple conversational memory: if the current query is short/vague and there is prior
	history, append the last user topic so retrieval has context. history is a list of
	{"role": "user"|"assistant", "content": "..."}.
	"""
	q = (query or "").strip()
	if not history:
		return q
	lower_q = q.lower()
	if len(q.split()) <= 6 and any(phrase in lower_q for phrase in ["details", "explain", "more", "what about", "reasoning", "judge", "what happened next"]):
		for turn in reversed(history):
			if turn.get("role") != "user":
				continue
			previous = (turn.get("content") or "").strip()
			if len(previous.split()) >= 4:
				return f"{q} about {previous}"
	return q


@app.post("/api/query", response_model=QueryResponse)
async def query_ai(
	request: QueryRequest,
	current_user: dict = Depends(get_current_user)
):
	"""
	Process AI queries with RAG. When conversation_id is provided (or created),
	user and assistant messages are persisted; history is loaded from DB for context.
	"""
	try:
		user_id = str(current_user.get("id", "1"))

		# Resolve or create conversation
		if request.conversation_id:
			conv = get_conversation(request.conversation_id, user_id)
			if not conv:
				raise HTTPException(status_code=404, detail="Conversation not found")
			conversation_id = request.conversation_id
		else:
			conv = create_conversation(user_id=user_id, title="New Chat")
			conversation_id = conv["id"]

		existing_messages = get_messages(conversation_id, user_id)
		history_for_rewrite = [{"role": m["role"], "content": m["content"]} for m in existing_messages[-12:]]

		# First user message in this conversation -> set title from query
		if len(existing_messages) == 0:
			update_conversation_title(conversation_id, user_id, title_from_first_query(request.query))

		# Persist user message
		add_message(conversation_id, user_id, "user", request.query)

		# Rewrite short follow-ups using conversation history from DB
		query_rewrite_start = time.time()
		rewritten_query = _rewrite_query_if_followup(request.query, history_for_rewrite)
		logging.info(f"query_rewrite took {time.time() - query_rewrite_start:.2f}s")

		system_prompt = (
			"You are Kenya Law AI, an assistant for Kenyan law and jurisprudence. "
			"Be accurate, concise, and practical. Explain relevant legal principles, case law, and statutes, "
			"highlight important precedents, and clearly state assumptions. Use clear, professional English."
		)

		# RAG: retrieval + answer generation (query only, no role preamble)
		response = rag_system.generate_response(
			query=rewritten_query,
			use_web_search=request.use_web_search
		)

		sources_detail = response.get("sources_detail")
		if sources_detail is not None:
			sources_detail = [SourceDetail(document=sd["document"], chunks=sd["chunks"]) for sd in sources_detail]
		sources_json = json.dumps([{"document": sd.document, "chunks": sd.chunks} for sd in (sources_detail or [])]) if sources_detail else None

		# Persist assistant message
		add_message(conversation_id, user_id, "assistant", response["answer"], sources_json=sources_json)

		# Update metrics
		try:
			m_path = _metrics_path()
			if os.path.exists(m_path):
				with open(m_path, "r", encoding="utf-8") as f:
					metrics_data = json.load(f) or {}
			else:
				metrics_data = {}
		except Exception as e:
			logging.warning(f"Failed to read metrics file before update: {e}")
			metrics_data = {}
		try:
			today = datetime.now().date().isoformat()
			if not isinstance(metrics_data, dict):
				metrics_data = {}
			if "daily" not in metrics_data or not isinstance(metrics_data.get("daily"), dict):
				metrics_data["daily"] = {}
			metrics_data["daily"][today] = int(metrics_data["daily"].get(today, 0)) + 1
			metrics_data["total_ai_queries"] = int(metrics_data.get("total_ai_queries", 0)) + 1
			with open(m_path, "w", encoding="utf-8") as f:
				json.dump(metrics_data, f)
		except Exception as e:
			logging.warning(f"Failed to update metrics file: {e}")

		return QueryResponse(
			answer=response["answer"],
			sources=response["sources"],
			confidence=response["confidence"],
			timestamp=datetime.fromisoformat(response["timestamp"]),
			rank_applied=None,
			prompt_used=system_prompt[:4000] if system_prompt else None,
			sources_detail=sources_detail,
			conversation_id=conversation_id,
		)
	except HTTPException:
		raise
	except Exception as e:
		logging.error(f"Query processing failed: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(
	limit: int = 50,
	current_user: dict = Depends(get_current_user)
):
	"""List uploaded documents (for Uploads page).

	Default returns only the most recently modified files to keep the UI fast.
	Set limit<=0 to return all documents.
	"""
	upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
	documents = []
	try:
		if not os.path.isdir(upload_dir):
			logging.warning(f"Uploads directory does not exist: {upload_dir}")
			return DocumentListResponse(documents=[], total_uploaded=0, total_indexed=0)
		
		all_files = os.listdir(upload_dir)
		# Avoid per-file Qdrant checks here (can be slow with many docs). Use last-known status file.
		status_map = _load_index_status(upload_dir)
		logging.info(f"Found {len(all_files)} items in upload directory")
		status_filename = os.path.basename(_index_status_path(upload_dir))

		file_names: List[str] = []
		for name in all_files:
			if name == status_filename:
				continue
			path = os.path.join(upload_dir, name)
			if os.path.isfile(path):
				file_names.append(name)

		total_uploaded = len(file_names)
		total_indexed = 0
		for name in file_names:
			val = status_map.get(name)
			is_indexed = bool(val.get("indexed", False)) if isinstance(val, dict) else bool(val)
			if is_indexed:
				total_indexed += 1
		
		for name in file_names:
			path = os.path.join(upload_dir, name)
			if os.path.isfile(path):
				try:
					stat = os.stat(path)
					# Last-known index status (updated on upload/delete). If missing, default False.
					val = status_map.get(name)
					is_indexed = bool(val.get("indexed", False)) if isinstance(val, dict) else bool(val)
					indexed_at = (val.get("updated_at") if isinstance(val, dict) and is_indexed else None)
					
					documents.append(DocumentItem(
						filename=name,
						size=stat.st_size,
						uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
						indexed=is_indexed,
						indexed_at=indexed_at
					))
				except Exception as e:
					logging.error(f"Error processing file {name}: {e}", exc_info=True)
					continue
		# newest first
		documents.sort(key=lambda d: d.uploaded_at, reverse=True)
		# return only the most recent N (unless caller requests all)
		if limit and limit > 0:
			documents = documents[:limit]
		logging.info(f"Listed {len(documents)} documents from {upload_dir}")
	except Exception as e:
		logging.error(f"Error listing documents: {e}", exc_info=True)
	return DocumentListResponse(documents=documents, total_uploaded=total_uploaded, total_indexed=total_indexed)

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str, current_user: dict = Depends(get_current_user)):
	"""Delete a document from the server and vector store."""
	try:
		# Decode URL-encoded filename
		from urllib.parse import unquote
		decoded_filename = unquote(filename)
		logging.info(f"Delete request received for: {filename} (decoded: {decoded_filename})")
		
		upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
		file_path = os.path.join(upload_dir, decoded_filename)
		
		# Security: prevent directory traversal
		abs_file_path = os.path.abspath(file_path)
		abs_upload_dir = os.path.abspath(upload_dir)
		if not abs_file_path.startswith(abs_upload_dir):
			logging.error(f"Security check failed: {abs_file_path} not in {abs_upload_dir}")
			raise HTTPException(status_code=400, detail="Invalid filename")
		
		logging.info(f"Attempting to delete document {decoded_filename} from {file_path}")
		
		# Check if file exists before attempting deletion
		if not os.path.exists(file_path):
			logging.warning(f"File {decoded_filename} not found at {file_path}")
			# List files in directory to help debug
			if os.path.isdir(upload_dir):
				existing_files = os.listdir(upload_dir)
				logging.info(f"Files in upload directory: {existing_files}")
			raise HTTPException(status_code=404, detail=f"Document not found: {decoded_filename}")
		
		# Delete from vector stores: chunk index (kenyalaw_cases) and document index (kenyalaw_documents)
		try:
			rag_system.delete_document(decoded_filename)
			logging.info(f"Deleted {decoded_filename} from vector store (kenyalaw_cases)")
		except Exception as vec_error:
			logging.warning(f"Failed to delete {decoded_filename} from vector store: {vec_error}")
		try:
			document_indexer.delete_by_filename(decoded_filename)
			logging.info(f"Deleted {decoded_filename} from document-level index (kenyalaw_documents)")
		except Exception as doc_idx_error:
			logging.warning(f"Failed to delete {decoded_filename} from document index: {doc_idx_error}")
			# Continue with file deletion even if document index deletion fails
		
		# Delete the file from disk
		try:
			os.remove(file_path)
			logging.info(f"Successfully deleted document {decoded_filename} from disk at {file_path}")
			
			# Verify deletion
			if os.path.exists(file_path):
				logging.error(f"File {decoded_filename} still exists after deletion attempt!")
				raise HTTPException(status_code=500, detail="File deletion failed")
			
			logging.info(f"Deletion verified: {decoded_filename} no longer exists")

			# Update local index status map (fast)
			try:
				status_map = _load_index_status(upload_dir)
				if decoded_filename in status_map:
					status_map.pop(decoded_filename, None)
					_save_index_status(upload_dir, status_map)
			except Exception as e:
				logging.warning(f"Failed to update index status for deleted doc {decoded_filename}: {e}")

			return {"status": "deleted", "filename": decoded_filename}
		except PermissionError as perm_error:
			logging.error(f"Permission denied deleting {decoded_filename}: {perm_error}")
			raise HTTPException(status_code=403, detail="Permission denied")
		except OSError as os_error:
			logging.error(f"OS error deleting {decoded_filename}: {os_error}")
			raise HTTPException(status_code=500, detail=f"Failed to delete file: {os_error}")
	except HTTPException:
		raise
	except Exception as e:
		logging.error(f"Failed to delete document {filename}: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{filename}/download")
async def download_document(filename: str, current_user: dict = Depends(get_current_user)):
	"""Download a document file by filename."""
	try:
		from urllib.parse import unquote
		decoded_filename = unquote(filename)
		upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
		file_path = os.path.join(upload_dir, decoded_filename)

		abs_file_path = os.path.abspath(file_path)
		abs_upload_dir = os.path.abspath(upload_dir)
		if not abs_file_path.startswith(abs_upload_dir):
			logging.error(f"Security check failed for download: {abs_file_path} not in {abs_upload_dir}")
			raise HTTPException(status_code=400, detail="Invalid filename")

		if not os.path.exists(abs_file_path) or not os.path.isfile(abs_file_path):
			raise HTTPException(status_code=404, detail="Document not found")

		return FileResponse(
			abs_file_path,
			filename=decoded_filename,
			media_type="application/octet-stream"
		)
	except HTTPException:
		raise
	except Exception as e:
		logging.error(f"Failed to download document {filename}: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail="Failed to download document")

@app.post("/api/upload", response_model=DocumentUploadResponse)
async def upload_document(
	file: UploadFile = File(...),
	current_user: dict = Depends(get_current_user)
):
	"""
	Upload and index documents for RAG
	"""
	try:
		upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
		os.makedirs(upload_dir, exist_ok=True)
		file_path = os.path.join(upload_dir, file.filename)
		
		# Security: prevent directory traversal
		if not os.path.abspath(file_path).startswith(os.path.abspath(upload_dir)):
			raise HTTPException(status_code=400, detail="Invalid filename")
		
		with open(file_path, "wb") as buffer:
			content = await file.read()
			buffer.write(content)
		
		# Verify file was saved
		if not os.path.exists(file_path):
			raise HTTPException(status_code=500, detail="File was not saved successfully")
		
		# Verify file size matches
		saved_size = os.path.getsize(file_path)
		if saved_size != len(content):
			logging.warning(f"File size mismatch for {file.filename}: expected {len(content)}, got {saved_size}")
		
		logging.info(f"Saved file {file.filename} to {file_path} ({len(content)} bytes, verified: {saved_size} bytes)")
		
		# Verify file appears in directory listing
		dir_files = os.listdir(upload_dir)
		logging.info(f"Directory listing after save: {len(dir_files)} files: {dir_files}")
		if file.filename not in dir_files:
			logging.error(f"File {file.filename} not found in directory listing after save! Files in dir: {dir_files}")
		else:
			logging.info(f"File {file.filename} confirmed in directory listing")
		
		# Index document using RAG system
		metadata = {
			"filename": file.filename,
			"uploaded_by": current_user.get("name", "Unknown"),
			"uploaded_at": datetime.now().isoformat(),
			"file_size": len(content)
		}
		
		indexed, index_message = rag_system.index_document(file_path, metadata)
		document_id = f"doc_{datetime.now().timestamp()}"

		# --- Phase 1: upsert document-level synopsis into kenyalaw_documents ---
		try:
			# Reuse rag_system's loader to get clean text for metadata/synopsis
			docs = rag_system._load_document(file_path)
			full_text = "\n\n".join(d.page_content for d in docs) if docs else ""
			legal_meta = extract_legal_metadata(full_text, file.filename)
			master_text = build_master_text(legal_meta, full_text)
			# Merge upload metadata into legal_meta for richer payload
			payload = {**legal_meta, **metadata, "master_text": master_text}
			doc_id = legal_meta.get("doc_id", document_id)
			document_indexer.upsert_document(doc_id=doc_id, master_text=master_text, payload=payload)
		except Exception as e:
			logging.warning(f"Document-level indexing (kenyalaw_documents) failed for {file.filename}: {e}")

		# Persist last-known indexing status locally so /api/documents is fast even with many files
		try:
			status_map = _load_index_status(upload_dir)
			status_map[file.filename] = {
				"indexed": bool(indexed),
				"index_message": index_message,
				"updated_at": datetime.now().isoformat(),
			}
			_save_index_status(upload_dir, status_map)
		except Exception as e:
			logging.warning(f"Failed to persist index status for {file.filename}: {e}")
		
		return DocumentUploadResponse(
			document_id=document_id,
			filename=file.filename,
			status="uploaded",
			indexed=indexed,
			index_message=index_message
		)
	except HTTPException:
		raise
	except Exception as e:
		logging.error(f"Document upload failed: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/map/events", response_model=List[MapEvent])
async def get_map_events(
	current_user: dict = Depends(get_current_user)
):
	"""
	Get map events for the Kenya operations dashboard
	"""
	# Mock data for demonstration
	events = [
		MapEvent(
			id="1",
			title="Security Alert - Nairobi",
			description="Unusual activity detected in Central Business District",
			latitude=-1.2921,
			longitude=36.8219,
			event_type="security",
			severity="high",
			timestamp=datetime.now()
		),
		MapEvent(
			id="2",
			title="Training Exercise - Mombasa",
			description="Coastal defense training in progress",
			latitude=-4.0437,
			longitude=39.6682,
			event_type="training",
			severity="low",
			timestamp=datetime.now()
		),
		MapEvent(
			id="3",
			title="Intelligence Report - Kisumu",
			description="New intelligence gathering operation",
			latitude=-0.0917,
			longitude=34.7680,
			event_type="intelligence",
			severity="medium",
			timestamp=datetime.now()
		)
	]
	
	return events

@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics(
	current_user: dict = Depends(get_current_user)
):
	"""
	Get dashboard metrics and statistics (real data from uploads, index status, and metrics.json).
	"""
	upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
	total_uploaded = 0
	total_indexed = 0
	recent_documents: List[dict] = []
	if os.path.isdir(upload_dir):
		all_files = os.listdir(upload_dir)
		status_map = _load_index_status(upload_dir)
		status_filename = os.path.basename(_index_status_path(upload_dir))
		indexed_entries: List[tuple] = []
		for name in all_files:
			if name == status_filename:
				continue
			path = os.path.join(upload_dir, name)
			if not os.path.isfile(path):
				continue
			total_uploaded += 1
			val = status_map.get(name)
			is_indexed = bool(val.get("indexed", False)) if isinstance(val, dict) else bool(val)
			if is_indexed:
				total_indexed += 1
				try:
					stat = os.stat(path)
					updated_at = (val.get("updated_at") if isinstance(val, dict) else None) or datetime.fromtimestamp(stat.st_mtime).isoformat()
					indexed_entries.append((name, updated_at, stat.st_mtime))
				except Exception:
					indexed_entries.append((name, None, 0))
		indexed_entries.sort(key=lambda x: x[2], reverse=True)
		for name, updated_at, _ in indexed_entries[:15]:
			recent_documents.append({
				"filename": name,
				"uploaded_at": updated_at or datetime.now().isoformat(),
				"indexed_at": updated_at,
			})

	# AI queries from metrics.json
	ai_queries_today = 0
	total_ai_queries = 0
	try:
		m_path = _metrics_path()
		if os.path.exists(m_path):
			with open(m_path, "r", encoding="utf-8") as f:
				metrics_data = json.load(f) or {}
		else:
			metrics_data = {}
	except Exception as e:
		logging.warning(f"Failed to read metrics file: {e}")
		metrics_data = {}
	today = datetime.now().date().isoformat()
	if isinstance(metrics_data, dict):
		ai_queries_today = int(metrics_data.get("daily", {}).get(today, 0))
		total_ai_queries = int(metrics_data.get("total_ai_queries", 0))

	return {
		"judgments_indexed": total_indexed,
		"documents_uploaded": total_uploaded,
		"ai_queries_today": ai_queries_today,
		"total_ai_queries": total_ai_queries,
		"last_updated": datetime.now().isoformat(),
		"recent_documents": recent_documents,
	}

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)
