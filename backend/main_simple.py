"""
Kenya Law Reports AI - Simplified Backend
A minimal version for legal intelligence without heavy AI dependencies
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="Kenya Law Reports AI",
    version="1.0.0",
    description="AI-powered legal intelligence platform for Kenya Law Reports"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
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
    user_rank: Optional[str] = None  # Reused for legal roles

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    timestamp: datetime
    rank_applied: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    indexed: bool

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
    prompt_text: Optional[str] = None
    is_active: bool = True

class PromptListResponse(BaseModel):
    prompts: List[Prompt]

# Mock user for demo
def get_current_user():
    return {"id": "1", "role": "admin", "name": "Demo User"}

# Legal prompts
LEGAL_PROMPTS = [
    {
        "id": "case-summary",
        "title": "Case Summary",
        "description": "Summarize the key facts, issues, holdings, and reasoning of a case.",
        "prompt_text": "You are a legal research assistant. Provide a comprehensive case summary including: 1) Facts of the case, 2) Legal issues, 3) Holdings/Judgment, 4) Reasoning/Ratio decidendi, 5) Significance/Impact.",
        "is_active": True
    },
    {
        "id": "legal-principle",
        "title": "Legal Principle Extraction",
        "description": "Extract the core legal principles and ratio decidendi from a judgment.",
        "prompt_text": "You are a legal analyst. Extract and explain the core legal principles (ratio decidendi) from the case or legal query. Include relevant statutory provisions and how they were interpreted.",
        "is_active": True
    },
    {
        "id": "case-precedents",
        "title": "Case Precedents",
        "description": "Find and analyze relevant precedents and how they apply.",
        "prompt_text": "You are a legal researcher. Identify relevant case precedents, explain their holdings, and analyze how they apply to the current legal question. Include citations where possible.",
        "is_active": True
    },
    {
        "id": "statutory-interpretation",
        "title": "Statutory Interpretation",
        "description": "Interpret statutes and legal provisions in context.",
        "prompt_text": "You are a legal expert in statutory interpretation. Analyze the relevant statutory provisions, apply appropriate canons of construction, and explain how the law should be interpreted in this context.",
        "is_active": True
    },
    {
        "id": "legal-opinion",
        "title": "Legal Opinion (Non-binding)",
        "description": "Provide a preliminary legal analysis on a matter.",
        "prompt_text": "You are providing a preliminary legal opinion for research purposes only. Analyze the legal issues, applicable law, and provide a reasoned opinion. Include appropriate caveats that this is not formal legal advice.",
        "is_active": True
    },
    {
        "id": "comparative-law",
        "title": "Comparative Case Law",
        "description": "Compare legal approaches across different jurisdictions.",
        "prompt_text": "You are a comparative law researcher. Analyze how different jurisdictions (Kenya, East Africa, Commonwealth) have approached similar legal issues. Highlight similarities, differences, and trends.",
        "is_active": True
    }
]

# Routes
@app.get("/")
async def root():
    return {
        "message": "Kenya Law Reports AI API",
        "version": "1.0.0",
        "description": "AI-powered legal intelligence for Kenya Law Reports"
    }

@app.get("/api/prompts", response_model=PromptListResponse)
async def list_prompts():
    """Get available legal analysis prompts"""
    return {"prompts": LEGAL_PROMPTS}

@app.post("/api/query", response_model=QueryResponse)
async def query_ai(request: QueryRequest):
    """
    Process legal AI queries with mock responses
    """
    try:
        query_lower = request.query.lower()
        
        # Legal role context
        role_context = ""
        if request.user_rank:
            role_context = f"[Responding for: {request.user_rank}] "
        
        # Mock legal AI responses based on query content
        if "constitution" in query_lower or "article" in query_lower:
            answer = f"{role_context}**Constitutional Analysis**\n\n" \
                    f"Based on your query: '{request.query}'\n\n" \
                    "**Relevant Constitutional Provisions:**\n" \
                    "The Constitution of Kenya, 2010 provides the supreme law of the Republic. " \
                    "Key provisions relevant to this query include:\n\n" \
                    "- **Article 10**: National values and principles of governance\n" \
                    "- **Article 19-51**: Bill of Rights\n" \
                    "- **Article 159**: Judicial authority and principles\n\n" \
                    "**Interpretation:**\n" \
                    "Courts have consistently held that constitutional provisions must be interpreted " \
                    "purposively to give effect to the values and principles enshrined therein.\n\n" \
                    "**Key Cases:**\n" \
                    "- *Communications Commission of Kenya v Royal Media Services* [2014] eKLR\n" \
                    "- *Mumo Matemu v Trusted Society of Human Rights Alliance* [2013] eKLR"
            sources = ["Constitution of Kenya, 2010", "Kenya Law Reports", "Supreme Court Decisions"]
            
        elif "criminal" in query_lower or "penal" in query_lower:
            answer = f"{role_context}**Criminal Law Analysis**\n\n" \
                    f"Query: '{request.query}'\n\n" \
                    "**Applicable Law:**\n" \
                    "The Penal Code (Cap 63) and Criminal Procedure Code govern criminal matters in Kenya.\n\n" \
                    "**Key Principles:**\n" \
                    "1. Presumption of innocence (Article 50(2)(a), Constitution)\n" \
                    "2. Burden of proof on prosecution - beyond reasonable doubt\n" \
                    "3. Right to fair trial and legal representation\n\n" \
                    "**Relevant Precedents:**\n" \
                    "- *Republic v Danson Mwangi* [2019] eKLR - Standard of proof\n" \
                    "- *Joseph Kimani Njau v Republic* [2014] eKLR - Right to fair hearing"
            sources = ["Penal Code Cap 63", "Criminal Procedure Code", "Court of Appeal Decisions"]
            
        elif "land" in query_lower or "property" in query_lower:
            answer = f"{role_context}**Land & Property Law Analysis**\n\n" \
                    f"Query: '{request.query}'\n\n" \
                    "**Legal Framework:**\n" \
                    "Land matters in Kenya are governed by:\n" \
                    "- Constitution of Kenya, 2010 (Chapter Five)\n" \
                    "- Land Act, 2012\n" \
                    "- Land Registration Act, 2012\n" \
                    "- Environment and Land Court Act, 2011\n\n" \
                    "**Key Principles:**\n" \
                    "1. Land in Kenya is held in trust for the people\n" \
                    "2. Categories: Public, Community, and Private land\n" \
                    "3. ELC has exclusive jurisdiction over land disputes\n\n" \
                    "**Relevant Cases:**\n" \
                    "- *Coastal Aquaculture Ltd v County Government of Mombasa* [2020] eKLR\n" \
                    "- *Isack M'Inanga Kiebia v Isaaya Theuri M'Lintari* [2018] eKLR"
            sources = ["Land Act 2012", "Constitution Chapter Five", "Environment & Land Court"]
            
        elif "employment" in query_lower or "labour" in query_lower or "labor" in query_lower:
            answer = f"{role_context}**Employment & Labour Law Analysis**\n\n" \
                    f"Query: '{request.query}'\n\n" \
                    "**Legal Framework:**\n" \
                    "- Employment Act, 2007\n" \
                    "- Labour Relations Act, 2007\n" \
                    "- Labour Institutions Act, 2007\n" \
                    "- Constitution Article 41 (Labour rights)\n\n" \
                    "**Key Principles:**\n" \
                    "1. Fair labour practices and reasonable working conditions\n" \
                    "2. Protection against unfair dismissal\n" \
                    "3. Right to form and join trade unions\n\n" \
                    "**ELRC Jurisdiction:**\n" \
                    "Employment disputes are heard by the Employment & Labour Relations Court.\n\n" \
                    "**Relevant Cases:**\n" \
                    "- *Kenya Airways Ltd v Aviation & Allied Workers Union* [2014] eKLR\n" \
                    "- *Coca-Cola Central, East & West Africa v Maria Kagai Ligaga* [2015] eKLR"
            sources = ["Employment Act 2007", "ELRC Decisions", "Labour Relations Act"]
            
        elif "contract" in query_lower or "agreement" in query_lower:
            answer = f"{role_context}**Contract Law Analysis**\n\n" \
                    f"Query: '{request.query}'\n\n" \
                    "**Legal Framework:**\n" \
                    "Contract law in Kenya is primarily based on:\n" \
                    "- Law of Contract Act (Cap 23)\n" \
                    "- Common law principles\n" \
                    "- Specific statutes for particular contracts\n\n" \
                    "**Essential Elements:**\n" \
                    "1. Offer and acceptance\n" \
                    "2. Consideration\n" \
                    "3. Intention to create legal relations\n" \
                    "4. Capacity to contract\n" \
                    "5. Legality of purpose\n\n" \
                    "**Remedies for Breach:**\n" \
                    "- Damages\n" \
                    "- Specific performance\n" \
                    "- Rescission\n" \
                    "- Injunction"
            sources = ["Law of Contract Act Cap 23", "High Court Commercial Division", "Kenya Law Reports"]
            
        else:
            answer = f"{role_context}**Legal Research Analysis**\n\n" \
                    f"Query: '{request.query}'\n\n" \
                    "**General Analysis:**\n" \
                    "Thank you for your legal query. Based on the information provided:\n\n" \
                    "**Applicable Legal Framework:**\n" \
                    "This matter may involve multiple areas of Kenyan law. Key considerations include:\n\n" \
                    "1. **Constitutional provisions** - The Constitution of Kenya, 2010 as the supreme law\n" \
                    "2. **Statutory law** - Relevant Acts of Parliament\n" \
                    "3. **Case law** - Precedents from superior courts\n" \
                    "4. **Subsidiary legislation** - Regulations and rules\n\n" \
                    "**Recommended Next Steps:**\n" \
                    "- Identify the specific legal area(s) involved\n" \
                    "- Research relevant statutes and case law\n" \
                    "- Consider jurisdictional issues\n" \
                    "- Consult a qualified advocate for specific advice\n\n" \
                    "**Disclaimer:**\n" \
                    "This is AI-generated legal information for research purposes only."
            sources = ["Kenya Law Reports", "Statutes Database", "Legal Research"]
        
        if request.use_web_search:
            sources.append("External Legal Databases")
            answer += "\n\n**Note:** Web search enabled - additional sources consulted."
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence=0.85,
            timestamp=datetime.now(),
            rank_applied=request.user_rank
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and mock index legal documents
    """
    try:
        # Create uploads directory
        os.makedirs("uploads", exist_ok=True)
        
        # Save file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Mock indexing
        document_id = f"doc_{datetime.now().timestamp()}"
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="uploaded",
            indexed=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/map/events", response_model=List[MapEvent])
async def get_map_events():
    """
    Get court locations for the Kenya map
    """
    courts = [
        MapEvent(
            id="1",
            title="Supreme Court of Kenya",
            description="Highest court - 234 judgments indexed",
            latitude=-1.2921,
            longitude=36.8219,
            event_type="supreme",
            severity="high",
            timestamp=datetime.now()
        ),
        MapEvent(
            id="2",
            title="High Court - Mombasa",
            description="High Court station - 1,234 judgments indexed",
            latitude=-4.0437,
            longitude=39.6682,
            event_type="high",
            severity="medium",
            timestamp=datetime.now()
        ),
        MapEvent(
            id="3",
            title="High Court - Kisumu",
            description="High Court station - 892 judgments indexed",
            latitude=-0.0917,
            longitude=34.7680,
            event_type="high",
            severity="medium",
            timestamp=datetime.now()
        ),
        MapEvent(
            id="4",
            title="Court of Appeal - Nairobi",
            description="Appellate court - 1,567 judgments indexed",
            latitude=-1.2833,
            longitude=36.8167,
            event_type="appeal",
            severity="high",
            timestamp=datetime.now()
        )
    ]
    
    return courts

@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """
    Get legal dashboard metrics and statistics
    """
    return {
        "total_judgments": 12456,
        "active_cases": 847,
        "courts_covered": 5,
        "ai_queries_today": 1234,
        "recent_uploads": 156,
        "last_updated": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Kenya Law Reports AI",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
