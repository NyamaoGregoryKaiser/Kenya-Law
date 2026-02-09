# PatriotAI Defense Hub - Deployment Guide

## Quick Start

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
Edit `.env` file with your API keys:
```bash
# Required for AI responses
OPENAI_API_KEY=your_openai_api_key_here

# Required for web search
SERPAPI_API_KEY=your_serpapi_key_here
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Access Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Manual Setup (Development)

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Features Overview

### 🏠 Dashboard
- Real-time metrics and KPIs
- Interactive Kenya map with event pins
- Recent alerts and notifications
- Quick action buttons

### 🤖 Ask AI Console
- RAG-powered intelligence queries
- Document-based Q&A
- Real-time web search integration
- Confidence scoring and source attribution

### 📁 Document Upload
- Support for PDF, TXT, DOC, DOCX
- Automatic document indexing
- Vector-based search and retrieval
- Metadata tracking

### 📊 Reports
- Generate intelligence reports
- Filter and search capabilities
- Status tracking (draft, review, approved)
- Export functionality

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

### AI Queries
- `POST /api/query` - Process AI queries with RAG
- `POST /api/upload` - Upload and index documents
- `GET /api/documents` - List uploaded documents

### Map Data
- `GET /api/map/events` - Get map events and alerts
- `POST /api/map/events` - Add new map event

### Reports
- `GET /api/reports` - List intelligence reports
- `POST /api/reports` - Generate new report
- `GET /api/reports/{id}` - Get specific report

## Configuration

### Environment Variables
- `OPENAI_API_KEY` - OpenAI API key for AI responses
- `SERPAPI_API_KEY` - SerpAPI key for web search
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `MILVUS_HOST` - Milvus vector database host
- `MILVUS_PORT` - Milvus vector database port

### Database Setup
The application uses PostgreSQL for metadata and Milvus for vector storage:
- PostgreSQL: Stores user data, reports, and metadata
- Milvus: Stores document embeddings for RAG
- Redis: Caching and background task queue

## Security Features

### Authentication
- Role-based access control (Admin/Analyst)
- JWT token authentication
- Session management

### Data Protection
- Document encryption at rest
- Secure file upload validation
- API rate limiting
- CORS configuration

## Monitoring and Logs

### Application Logs
- Backend logs: `backend/logs/`
- Docker logs: `docker-compose logs`

### Health Checks
- Backend health: `GET /health`
- Database connectivity: `GET /api/health/db`
- Vector store status: `GET /api/health/vector`

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000, 8000, 5432, 6379, 19530 are available
2. **API key errors**: Verify OpenAI and SerpAPI keys in `.env`
3. **Database connection**: Check PostgreSQL container status
4. **Vector store**: Ensure Milvus is running and accessible

### Performance Optimization

1. **Vector Database**: Increase Milvus memory allocation
2. **Caching**: Configure Redis memory limits
3. **File Storage**: Use external storage for production
4. **Load Balancing**: Deploy multiple backend instances

## Production Deployment

### Docker Swarm
```bash
docker stack deploy -c docker-compose.yml patriotai
```

### Kubernetes
```bash
kubectl apply -f k8s/
```

### Environment Variables for Production
```bash
DEBUG=False
SECRET_KEY=your_secure_secret_key
DATABASE_URL=postgresql://user:pass@prod-db:5432/patriotai
REDIS_URL=redis://prod-redis:6379
```

## Production Deployment (Static Files)

### Deploying Frontend Build to Server

After building the frontend with `npm run build`, deploy the built files to your web server:

#### 1. Find Where the App is Currently Deployed

Run these commands on your server to find the deployment location:

```bash
# Check nginx configuration
sudo grep -r "PatriotAI" /etc/nginx/ 2>/dev/null | grep -E "(root|alias)"

# Check apache configuration  
sudo grep -r "PatriotAI" /etc/apache2/ 2>/dev/null | grep -E "(DocumentRoot|Alias)"

# Check common web server locations
ls -la /var/www/html/PatriotAI
ls -la /var/www/PatriotAI
ls -la /usr/share/nginx/html/PatriotAI
```

#### 2. Deploy the Build Files

Once you know the deployment path (let's call it `/path/to/PatriotAI`):

```bash
# Navigate to project directory
cd ~/demos/Defence-ai

# Make sure build exists
ls -la frontend/build/

# Backup existing files (optional but recommended)
sudo cp -r /path/to/PatriotAI /path/to/PatriotAI_backup_$(date +%Y%m%d_%H%M%S)

# Remove old files
sudo rm -rf /path/to/PatriotAI/*

# Copy new build files
sudo cp -r frontend/build/* /path/to/PatriotAI/

# Set proper permissions
sudo chown -R www-data:www-data /path/to/PatriotAI
sudo chmod -R 755 /path/to/PatriotAI
```

#### 3. Restart Web Server (if needed)

```bash
# For nginx
sudo systemctl restart nginx

# For apache
sudo systemctl restart apache2
```

#### 4. Quick Deploy Script

You can also use the provided deploy script:

```bash
# Make script executable
chmod +x deploy-frontend.sh

# Run the script
./deploy-frontend.sh
```

#### 5. Verify Deployment

1. Clear browser cache or do a hard refresh (Ctrl+Shift+R)
2. Visit: https://172.20.16.155/PatriotAI/
3. Test the "Ask AI" feature to verify API calls work

### Troubleshooting Deployment

If the app still doesn't work after deployment:

1. **Check file permissions:**
   ```bash
   ls -la /path/to/PatriotAI
   sudo chown -R www-data:www-data /path/to/PatriotAI
   ```

2. **Check web server logs:**
   ```bash
   # Nginx
   sudo tail -f /var/log/nginx/error.log
   
   # Apache
   sudo tail -f /var/log/apache2/error.log
   ```

3. **Verify build files:**
   ```bash
   ls -la frontend/build/static/js/
   ls -la frontend/build/index.html
   ```

4. **Check API calls in browser console:**
   - Open browser developer tools (F12)
   - Go to Network tab
   - Try "Ask AI" feature
   - Verify API calls go to `/PatriotAI/api/query` instead of `/api/query`

## Support

For technical support or questions:
- Documentation: `/docs` endpoint
- Issues: GitHub Issues
- Email: support@patriotai.ke

## License

This project is licensed under the MIT License - see the LICENSE file for details.
