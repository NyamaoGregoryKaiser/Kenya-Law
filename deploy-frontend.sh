#!/bin/bash

# Deploy script for PatriotAI Frontend
# This script finds where the app is currently deployed and updates it with the new build

echo "🔍 Finding where the app is currently deployed..."

# Common web server document root locations
POSSIBLE_LOCATIONS=(
    "/var/www/html/PatriotAI"
    "/var/www/PatriotAI"
    "/usr/share/nginx/html/PatriotAI"
    "/var/www/nginx-default/PatriotAI"
    "$HOME/www/PatriotAI"
    "$HOME/public_html/PatriotAI"
    "/opt/PatriotAI"
)

# Check nginx configuration
echo "Checking nginx configuration..."
NGINX_CONFIG=$(find /etc/nginx -name "*.conf" 2>/dev/null | xargs grep -l "PatriotAI" 2>/dev/null | head -1)
if [ ! -z "$NGINX_CONFIG" ]; then
    echo "Found nginx config mentioning PatriotAI: $NGINX_CONFIG"
    ROOT_PATH=$(grep -E "(root|alias)" "$NGINX_CONFIG" | grep -i patriot | grep -v "^#" | head -1 | awk '{print $2}' | tr -d ';')
    if [ ! -z "$ROOT_PATH" ]; then
        echo "📁 Detected deployment path from nginx: $ROOT_PATH"
        DEPLOY_PATH="$ROOT_PATH"
    fi
fi

# Check apache configuration
if [ -z "$DEPLOY_PATH" ]; then
    echo "Checking apache configuration..."
    APACHE_CONFIG=$(find /etc/apache2 -name "*.conf" 2>/dev/null | xargs grep -l "PatriotAI" 2>/dev/null | head -1)
    if [ ! -z "$APACHE_CONFIG" ]; then
        echo "Found apache config mentioning PatriotAI: $APACHE_CONFIG"
        ROOT_PATH=$(grep -E "DocumentRoot|Alias" "$APACHE_CONFIG" | grep -i patriot | grep -v "^#" | head -1 | awk '{print $2}')
        if [ ! -z "$ROOT_PATH" ]; then
            echo "📁 Detected deployment path from apache: $ROOT_PATH"
            DEPLOY_PATH="$ROOT_PATH"
        fi
    fi
fi

# Check if any of the common locations exist
if [ -z "$DEPLOY_PATH" ]; then
    echo "Checking common web server locations..."
    for loc in "${POSSIBLE_LOCATIONS[@]}"; do
        if [ -d "$loc" ]; then
            echo "📁 Found existing directory: $loc"
            DEPLOY_PATH="$loc"
            break
        fi
    done
fi

# If still not found, ask user or use a default
if [ -z "$DEPLOY_PATH" ]; then
    echo "⚠️  Could not automatically detect deployment path."
    echo "Please enter the full path where PatriotAI is deployed:"
    read -p "Deployment path: " DEPLOY_PATH
fi

# Verify the path exists
if [ ! -d "$DEPLOY_PATH" ]; then
    echo "❌ Error: Directory $DEPLOY_PATH does not exist!"
    echo "Creating directory..."
    sudo mkdir -p "$DEPLOY_PATH" || mkdir -p "$DEPLOY_PATH"
fi

# Build path
BUILD_PATH="$(pwd)/frontend/build"

if [ ! -d "$BUILD_PATH" ]; then
    echo "❌ Error: Build directory not found at $BUILD_PATH"
    echo "Please run 'npm run build' in the frontend directory first."
    exit 1
fi

echo ""
echo "🚀 Deploying frontend build..."
echo "Source: $BUILD_PATH"
echo "Destination: $DEPLOY_PATH"
echo ""

# Backup existing deployment (optional)
if [ -d "$DEPLOY_PATH" ] && [ "$(ls -A $DEPLOY_PATH 2>/dev/null)" ]; then
    BACKUP_DIR="${DEPLOY_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
    echo "📦 Creating backup at: $BACKUP_DIR"
    sudo cp -r "$DEPLOY_PATH" "$BACKUP_DIR" || cp -r "$DEPLOY_PATH" "$BACKUP_DIR"
fi

# Remove old files (except uploads or other important directories if they exist)
echo "🧹 Cleaning old files..."
sudo rm -rf "${DEPLOY_PATH}"/* "${DEPLOY_PATH}"/.[^.]* 2>/dev/null || rm -rf "${DEPLOY_PATH}"/* "${DEPLOY_PATH}"/.[^.]* 2>/dev/null

# Copy new build files
echo "📋 Copying new build files..."
sudo cp -r "$BUILD_PATH"/* "$DEPLOY_PATH/" || cp -r "$BUILD_PATH"/* "$DEPLOY_PATH/"

# Set proper permissions
echo "🔒 Setting permissions..."
sudo chown -R www-data:www-data "$DEPLOY_PATH" 2>/dev/null || sudo chown -R nginx:nginx "$DEPLOY_PATH" 2>/dev/null || true
sudo chmod -R 755 "$DEPLOY_PATH"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Clear your browser cache or do a hard refresh (Ctrl+Shift+R or Cmd+Shift+R)"
echo "2. Test the app at: https://172.20.16.155/PatriotAI/"
echo "3. Try the 'Ask AI' feature to verify API calls work"
echo ""
echo "If you need to restart the web server:"
echo "  sudo systemctl restart nginx   # for nginx"
echo "  sudo systemctl restart apache2 # for apache"

