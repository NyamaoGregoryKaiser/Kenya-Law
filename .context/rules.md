# Coding Rules – Kenya Law AI

## General

- Keep all behavior grounded in **Kenyan law**.
- RAG answers must be based **only on indexed documents**, not general model knowledge.
- When there is insufficient document context, return a clear “not found in your uploaded documents” style message.

## Backend Rules

- Keep FastAPI routes under /api/....
- Preserve existing endpoints:
  - POST /api/query
  - POST /api/upload
  - GET /api/documents
  - DELETE /api/documents/{filename}
- Preserve the sources + sources_detail structure from ag_system.generate_response().
- Any new RAG logic:
  - must respect the “documents only” constraint
  - must not introduce web search into the main Ask AI path.

## Frontend Rules

- Assume the app is deployed at /KenyaLawAI/ and always go through API_BASE.
- When showing sources:
  - group by document
  - show file name once; reveal chunks/passages on expand.
- Do not reintroduce web-search toggles in the Ask AI UI.

## Deployment

- For production builds:
  - Always build with PUBLIC_URL=/KenyaLawAI
  - Keep Nginx proxying /KenyaLawAI/api/ to the FastAPI backend.
