"""
PatriotAI Defense Hub - Open WebUI Extension
A specialized defense intelligence platform for Kenya's defense sector
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging
from datetime import datetime
import shutil

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

# Log environment status at startup
import os
logging.info(f"GOOGLE_API_KEY present: {bool(os.getenv('GOOGLE_API_KEY'))}")
logging.info(f"SERPAPI_API_KEY present: {bool(os.getenv('SERPAPI_API_KEY'))}")

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
class QueryRequest(BaseModel):
	query: str
	use_web_search: bool = False
	context_documents: Optional[List[str]] = None
	system_prompt: Optional[str] = None
	user_rank: Optional[str] = None  # e.g., "Advocate", "Judge", "Legal Researcher"

class QueryResponse(BaseModel):
	answer: str
	sources: List[str]
	confidence: float
	timestamp: datetime
	rank_applied: Optional[str] = None
	prompt_used: Optional[str] = None

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

class DocumentListResponse(BaseModel):
	documents: List[DocumentItem]

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

# adjust /api/query to resolve prompt id if provided via system_prompt field containing the id
# (keep previous behavior for raw text)
@app.post("/api/query", response_model=QueryResponse)
async def query_ai(
	request: QueryRequest,
	current_user: dict = Depends(get_current_user)
):
	"""
	Process AI queries with RAG capabilities and optional legal role / system prompt
	"""
	try:
		role_preamble = ""
		if request.user_rank:
			role_preamble = (
				f"You are responding to a legal professional (role: {request.user_rank}). "
				"Tailor depth, tone, and recommendations appropriately for this audience. "
			)
		
		custom_system = request.system_prompt
		# If the client sent an id-like value that matches a prompt, resolve it server-side
		if custom_system and len(custom_system) <= 64:
			resolved = find_prompt_by_id(custom_system)
			if resolved:
				custom_system = resolved.get('prompt_text')
		
		if not custom_system:
			custom_system = (
			"You are Kenya Law AI, an assistant for Kenyan law and jurisprudence. "
			"Be accurate, concise, and practical. Explain relevant legal principles, case law, and statutes, "
			"highlight important precedents, and clearly state assumptions. Use clear, professional English."
			)

		# Use the RAG system to generate response
		response = rag_system.generate_response(
			query=f"{role_preamble}{request.query}",
			use_web_search=request.use_web_search
		)
		# Do not append raw system prompt to the answer; keep response clean for the UI

		return QueryResponse(
			answer=response["answer"],
			sources=response["sources"],
			confidence=response["confidence"],
			timestamp=datetime.fromisoformat(response["timestamp"]),
			rank_applied=request.user_rank,
			prompt_used=(custom_system[:4000] if custom_system else None)
		)
	except Exception as e:
		logging.error(f"Query processing failed: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(current_user: dict = Depends(get_current_user)):
	"""List uploaded documents (for Uploads page)."""
	upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
	documents = []
	if os.path.isdir(upload_dir):
		for name in os.listdir(upload_dir):
			path = os.path.join(upload_dir, name)
			if os.path.isfile(path):
				stat = os.stat(path)
				documents.append(DocumentItem(
					filename=name,
					size=stat.st_size,
					uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
				))
	# newest first
	documents.sort(key=lambda d: d.uploaded_at, reverse=True)
	return DocumentListResponse(documents=documents)

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str, current_user: dict = Depends(get_current_user)):
	"""Delete a document from the server and vector store."""
	try:
		upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
		file_path = os.path.join(upload_dir, filename)
		
		# Security: prevent directory traversal
		if not os.path.abspath(file_path).startswith(os.path.abspath(upload_dir)):
			raise HTTPException(status_code=400, detail="Invalid filename")
		
		# Delete from vector store first
		rag_system.delete_document(filename)
		
		# Delete the file from disk
		if os.path.exists(file_path):
			os.remove(file_path)
			logging.info(f"Deleted document {filename}")
			return {"status": "deleted", "filename": filename}
		else:
			raise HTTPException(status_code=404, detail="Document not found")
	except HTTPException:
		raise
	except Exception as e:
		logging.error(f"Failed to delete document {filename}: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload", response_model=DocumentUploadResponse)
async def upload_document(
	file: UploadFile = File(...),
	current_user: dict = Depends(get_current_user)
):
	"""
	Upload and index documents for RAG
	"""
	try:
		upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
		os.makedirs(upload_dir, exist_ok=True)
		file_path = os.path.join(upload_dir, file.filename)
		with open(file_path, "wb") as buffer:
			content = await file.read()
			buffer.write(content)
		
		# Index document using RAG system
		metadata = {
			"filename": file.filename,
			"uploaded_by": current_user.get("name", "Unknown"),
			"uploaded_at": datetime.now().isoformat(),
			"file_size": len(content)
		}
		
		indexed, index_message = rag_system.index_document(file_path, metadata)
		document_id = f"doc_{datetime.now().timestamp()}"
		
		return DocumentUploadResponse(
			document_id=document_id,
			filename=file.filename,
			status="uploaded",
			indexed=indexed,
			index_message=index_message
		)
	except Exception as e:
		logging.error(f"Document upload failed: {e}")
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
	Get dashboard metrics and statistics
	"""
	return {
		"active_threats": 12,
		"personnel_online": 247,
		"documents_processed": 1234,
		"ai_queries_today": 456,
		"last_updated": datetime.now().isoformat()
	}

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)
