# 🇰🇪 PatriotAI Defense Hub

**Kituo cha Ulinzi cha AI** - A comprehensive AI-powered intelligence platform for Kenya's defense sector, built with Open WebUI integration.

## 🎯 Overview

PatriotAI Defense Hub is a full-stack web application that demonstrates how artificial intelligence can support decision-making in Kenya's defense sector. The platform combines document intelligence, real-time web search, interactive mapping, and advanced analytics to provide comprehensive situational awareness and decision support.

## ✨ Key Features

### 🤖 **Ask AI Console** / *Uliza AI*
- **RAG-Powered Intelligence**: Query internal documents and get AI-powered responses
- **Real-time Web Search**: Integrate live intelligence from web sources
- **Multi-language Support**: English and Swahili interface
- **Source Attribution**: Track information sources and confidence levels

### 📁 **Document Intelligence** / *Ujasusi wa Hati*
- **Multi-format Support**: PDF, TXT, DOC, DOCX document processing
- **Vector Indexing**: Advanced document search using embeddings
- **Metadata Tracking**: Document provenance and version control
- **Batch Processing**: Upload and process multiple documents

### 🗺️ **Interactive Map Dashboard** / *Dashibodi ya Ramani*
- **Kenya Operations Map**: Real-time visualization of defense operations
- **Event Pinning**: Mark and track security events and alerts
- **Geospatial Analysis**: Location-based intelligence and threat assessment
- **Custom Markers**: Different event types with color-coded severity

### 📊 **Intelligence Reports** / *Ripoti za Ujasusi*
- **Automated Report Generation**: AI-powered intelligence briefings
- **Status Tracking**: Draft, review, approval, and publication workflow
- **Search and Filter**: Advanced filtering by type, status, and content
- **Export Capabilities**: Download reports in multiple formats

### 🔐 **Role-Based Access Control**
- **Admin Role**: Full system access and configuration
- **Analyst Role**: Intelligence analysis and reporting capabilities
- **Secure Authentication**: JWT-based authentication with session management
- **Audit Logging**: Track user actions and system access

## 🏗️ Architecture

### Frontend Stack
- **React 18** with TypeScript
- **Tailwind CSS** for Kenyan-themed styling
- **Open WebUI Components** for consistent UI
- **Leaflet.js** for interactive mapping
- **Axios** for API communication
- **React Router** for navigation

### Backend Stack
- **FastAPI** with Python 3.11
- **Open WebUI Integration** for AI capabilities
- **LangChain** for RAG implementation
- **ChromaDB** for vector storage
- **PostgreSQL** for metadata storage
- **Redis** for caching and background tasks

### AI & ML Components
- **Retrieval-Augmented Generation (RAG)**
- **HuggingFace Embeddings** for document vectors
- **OpenAI GPT** for language processing
- **Web Search Integration** via SerpAPI
- **Document Processing** with PyPDF, Unstructured

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ and npm
- Python 3.11+
- Git

### 1. Clone and Setup
```bash
git clone <repository-url>
cd patriot-ai-defense-hub
python setup.py
```

### 2. Configure Environment
```bash
# Copy environment template
cp env.example .env

# Edit .env with your API keys
nano .env
```

Required API keys:
- `OPENAI_API_KEY`: For AI responses
- `SERPAPI_API_KEY`: For web search

### 3. Start Services
```bash
# Start all services with Docker
docker-compose up -d

# Or start manually for development
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm start
```

### 4. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 5. Demo Login
- **Admin**: `admin@patriotai.ke` / `demo123`
- **Analyst**: `analyst@patriotai.ke` / `demo123`

## 🎨 Design System

### Kenyan Flag Color Palette
- **Black**: `#000000` - Authority and strength
- **Red**: `#BB0000` - Blood shed for freedom
- **Green**: `#006400` - Natural wealth and agriculture
- **White**: `#FFFFFF` - Peace and unity

### Typography
- **Primary Font**: Inter (Google Fonts)
- **Headings**: Bold, clear hierarchy
- **Body Text**: Readable, accessible sizing

### Iconography
- **Shield**: Defense and protection
- **Spear**: Traditional strength
- **Map**: Geographic awareness
- **Document**: Intelligence and knowledge

## 📡 API Endpoints

### Authentication
- `POST /api/auth/login` - User authentication
- `POST /api/auth/logout` - User logout
- `GET /api/auth/profile` - User profile

### AI Intelligence
- `POST /api/query` - Process AI queries with RAG
- `POST /api/upload` - Upload and index documents
- `GET /api/documents` - List uploaded documents
- `DELETE /api/documents/{id}` - Delete document

### Geospatial Data
- `GET /api/map/events` - Get map events and alerts
- `POST /api/map/events` - Add new map event
- `PUT /api/map/events/{id}` - Update event
- `DELETE /api/map/events/{id}` - Remove event

### Intelligence Reports
- `GET /api/reports` - List intelligence reports
- `POST /api/reports` - Generate new report
- `GET /api/reports/{id}` - Get specific report
- `PUT /api/reports/{id}` - Update report
- `DELETE /api/reports/{id}` - Delete report

### System Health
- `GET /health` - Application health check
- `GET /api/health/db` - Database connectivity
- `GET /api/health/vector` - Vector store status

## 🔧 Configuration

### Environment Variables
```bash
# AI Services
OPENAI_API_KEY=your_openai_api_key
SERPAPI_API_KEY=your_serpapi_key

# Database
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port

# Vector Database
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Application
DEBUG=True
SECRET_KEY=your_secret_key
```

### Docker Services
- **Frontend**: React development server
- **Backend**: FastAPI application
- **PostgreSQL**: Primary database
- **Redis**: Caching and queues
- **Milvus**: Vector database
- **MinIO**: Object storage

## 🛡️ Security Features

### Data Protection
- **Encryption at Rest**: All documents encrypted
- **Secure Upload**: File validation and sanitization
- **API Rate Limiting**: Prevent abuse and DoS
- **CORS Configuration**: Controlled cross-origin access

### Authentication & Authorization
- **JWT Tokens**: Secure session management
- **Role-based Access**: Granular permissions
- **Session Timeout**: Automatic logout
- **Audit Logging**: Track all user actions

### Network Security
- **HTTPS Ready**: SSL/TLS configuration
- **Input Validation**: Prevent injection attacks
- **File Upload Security**: Malware scanning
- **API Authentication**: Token-based access

## 📈 Performance & Monitoring

### Metrics Dashboard
- **System Health**: Real-time status monitoring
- **Performance Metrics**: Response times and throughput
- **User Activity**: Login patterns and usage
- **Error Tracking**: Exception monitoring and alerting

### Optimization
- **Caching Strategy**: Redis for frequent queries
- **Database Indexing**: Optimized query performance
- **CDN Integration**: Static asset delivery
- **Load Balancing**: Horizontal scaling support

## 🚀 Deployment

### Production Deployment
```bash
# Docker Swarm
docker stack deploy -c docker-compose.yml patriotai

# Kubernetes
kubectl apply -f k8s/

# Manual deployment
./deploy.sh production
```

### Environment-Specific Configs
- **Development**: Local development with hot reload
- **Staging**: Production-like testing environment
- **Production**: Optimized for performance and security

## 📚 Documentation

- **API Documentation**: Available at `/docs` endpoint
- **User Guide**: Comprehensive usage instructions
- **Developer Guide**: Technical implementation details
- **Deployment Guide**: Production setup instructions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check `/docs` endpoint
- **Issues**: GitHub Issues for bug reports
- **Email**: support@patriotai.ke
- **Community**: Join our Discord server

## 🙏 Acknowledgments

- **Open WebUI** for the excellent AI interface framework
- **LangChain** for RAG implementation
- **Kenya Defense Forces** for domain expertise
- **Open Source Community** for the amazing tools and libraries

---

**PatriotAI Defense Hub** - *Empowering Kenya's defense through artificial intelligence*

*Kituo cha Ulinzi cha AI - Kuimarisha ulinzi wa Kenya kupitia akili ya bandia*
