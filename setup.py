#!/usr/bin/env python3
"""
PatriotAI Defense Hub Setup Script
Automated setup and configuration for the defense intelligence platform
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✓ {command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return None

def check_requirements():
    """Check if required tools are installed"""
    print("Checking requirements...")
    
    requirements = {
        "docker": "docker --version",
        "docker-compose": "docker-compose --version",
        "node": "node --version",
        "npm": "npm --version",
        "python": "python --version"
    }
    
    for tool, command in requirements.items():
        if run_command(command):
            print(f"✓ {tool} is installed")
        else:
            print(f"✗ {tool} is not installed")
            return False
    
    return True

def setup_environment():
    """Set up environment variables"""
    print("\nSetting up environment...")
    
    env_file = Path(".env")
    if not env_file.exists():
        shutil.copy("env.example", ".env")
        print("✓ Created .env file from template")
        print("⚠️  Please edit .env file with your API keys")
    else:
        print("✓ .env file already exists")

def setup_frontend():
    """Set up the frontend React application"""
    print("\nSetting up frontend...")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("✗ Frontend directory not found")
        return False
    
    # Install dependencies
    if run_command("npm install", cwd=frontend_dir):
        print("✓ Frontend dependencies installed")
        return True
    else:
        print("✗ Failed to install frontend dependencies")
        return False

def setup_backend():
    """Set up the backend Python application"""
    print("\nSetting up backend...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("✗ Backend directory not found")
        return False
    
    # Create virtual environment
    venv_dir = backend_dir / ".venv"
    if not venv_dir.exists():
        if run_command("python -m venv .venv", cwd=backend_dir):
            print("✓ Virtual environment created")
        else:
            print("✗ Failed to create virtual environment")
            return False
    
    # Install dependencies
    pip_cmd = str(venv_dir / "Scripts" / "pip") if os.name == 'nt' else str(venv_dir / "bin" / "pip")
    if run_command(f"{pip_cmd} install -r requirements.txt", cwd=backend_dir):
        print("✓ Backend dependencies installed")
        return True
    else:
        print("✗ Failed to install backend dependencies")
        return False

def create_directories():
    """Create necessary directories"""
    print("\nCreating directories...")
    
    directories = [
        "uploads",
        "backend/chroma_db",
        "backend/logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {directory}")

def main():
    """Main setup function"""
    print("🇰🇪 PatriotAI Defense Hub Setup")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Please install the required tools and try again")
        sys.exit(1)
    
    # Setup steps
    setup_environment()
    create_directories()
    
    if not setup_frontend():
        print("\n❌ Frontend setup failed")
        sys.exit(1)
    
    if not setup_backend():
        print("\n❌ Backend setup failed")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: docker-compose up")
    print("3. Access the application at http://localhost:3000")
    print("\nDemo credentials:")
    print("- Admin: admin@patriotai.ke / demo123")
    print("- Analyst: analyst@patriotai.ke / demo123")

if __name__ == "__main__":
    main()
