# Project Context – Kenya Law AI

## Project Overview
Kenya Law AI is a legal research assistant focused on Kenyan law and jurisprudence.

It:
- Indexes uploaded court judgments and legal documents (DOC, DOCX, PDF, TXT)
- Lets users ask legal questions via “Ask Legal AI”
- Answers **only from the uploaded documents** (no external/web knowledge)

## Stack

- Frontend: React (Create React App), TypeScript
- Backend: Python, FastAPI, Uvicorn
- RAG: LangChain + Google Gemini (LLM + embeddings) + Chroma vector store
- Document processing: unstructured, pypdf, 
ltk
- Deployment:
  - Frontend served at /KenyaLawAI/ via Nginx
  - Backend FastAPI on http://127.0.0.1:8000, proxied as /KenyaLawAI/api/

## Key Backend Files

- ackend/main.py
  - FastAPI app, auth
  - Endpoints: /api/query, /api/upload, /api/documents, /api/prompts
  - QueryResponse includes sources and sources_detail (document ? chunks)

- ackend/rag_system.py
  - PatriotAIRAGSystem
  - Uses **only uploaded documents** for answers
  - generate_response:
    - Searches Chroma
    - Groups chunks by document path
    - Returns:
      - nswer
      - sources (unique document paths)
      - sources_detail (per-document chunks)
    - If no relevant docs: returns a “not found in your uploaded documents” message

## Key Frontend Files

- rontend/src/pages/AskAI.tsx
  - “Ask Legal AI” chat UI
  - Shows:
    - AI answer (Markdown)
    - **Sources grouped by document**:
      - each document shown once
      - clicking expands to show passages (“chunks”) used
  - Uses API_BASE from rontend/src/utils/api.ts (handles /KenyaLawAI base path)

- rontend/src/pages/Uploads.tsx
  - Upload & indexing UI
  - Lists documents from /api/documents
  - Delete calls DELETE /api/documents/{filename} and removes file + vector entries

## Behavior Guarantees

- Answers must be based **only** on uploaded/indexed documents.
- If no relevant content is found, the system clearly says so (no hallucinated law).
- Web search is disabled in the Ask AI flow in production.
