/**
 * API Configuration Utility
 * Handles base URL detection for subpath deployments
 * 
 * When the app is deployed at a subpath (e.g., /PatriotAI/),
 * API calls need to include that base path to work correctly.
 */

// Known app routes - these help us identify the base path
const APP_ROUTES = ['', 'login', 'ask-ai', 'uploads', 'reports', 'dashboard'];

/**
 * Detects the base path from the current window location
 * For example, if URL is https://example.com/PatriotAI/ask-ai,
 * this will return '/PatriotAI'
 */
function detectBasePath(): string {
  try {
    const pathname = window.location.pathname;
    // Remove leading/trailing slashes and split
    const cleanPath = pathname.replace(/^\/+|\/+$/g, '');
    const pathParts = cleanPath.split('/').filter(part => part && part !== 'index.html');
    
    // If no path parts, we're at root
    if (pathParts.length === 0) {
      return '';
    }
    
    // Check if first part is a known app route
    // If not, it's likely the base path (e.g., /PatriotAI)
    const firstPart = pathParts[0].toLowerCase();
    if (!APP_ROUTES.includes(firstPart)) {
      // This is likely the base path
      return `/${pathParts[0]}`;
    }
    
    // If first part is a known route but we're at a subpath,
    // check if there's a base path before it
    // For example: /PatriotAI/login -> base is /PatriotAI
    if (pathParts.length > 1) {
      // If we're at a known route, check if there's something before it
      const routeIndex = pathParts.findIndex(part => APP_ROUTES.includes(part.toLowerCase()));
      if (routeIndex > 0) {
        return '/' + pathParts.slice(0, routeIndex).join('/');
      }
    }
    
    // Special case: if we're at root path like /PatriotAI/ (no route specified),
    // check the HTML base tag or try to infer from public URL in manifest/head
    // For now, we'll try to get it from the document base
    const baseTag = document.querySelector('base');
    if (baseTag && baseTag.getAttribute('href')) {
      const baseHref = baseTag.getAttribute('href') || '';
      if (baseHref !== '/' && baseHref.startsWith('/')) {
        const basePath = baseHref.replace(/\/$/, '');
        if (basePath) return basePath;
      }
    }
  } catch (error) {
    console.warn('Error detecting base path:', error);
  }
  
  // Default to empty string (root deployment)
  return '';
}

/**
 * Gets the API base URL for making requests
 */
function getApiBaseUrl(): string {
  // Option 1: Use explicit API URL if set (for separate API server)
  // This allows overriding with an absolute URL
  if (process.env.REACT_APP_API_BASE_URL) {
    const apiUrl = process.env.REACT_APP_API_BASE_URL.trim();
    // Remove trailing slash
    const cleanUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
    // Ensure /api is included
    return cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
  }
  
  // Option 2: Use PUBLIC_URL if set at build time
  // PUBLIC_URL is typically set during build: PUBLIC_URL=/PatriotAI npm run build
  const publicUrl = process.env.PUBLIC_URL || '';
  if (publicUrl && publicUrl !== '/') {
    // Remove trailing slash
    const cleanBase = publicUrl.endsWith('/') ? publicUrl.slice(0, -1) : publicUrl;
    return `${cleanBase}/api`;
  }
  
  // Option 3: Auto-detect base path from current location
  // This is the fallback that works at runtime
  const basePath = detectBasePath();
  return `${basePath}/api`;
}

/**
 * API base URL - use this constant in your components
 * Example: '/PatriotAI/api' or '/api' depending on deployment
 * 
 * This will automatically detect the correct base path when:
 * - The app is deployed at a subpath like /PatriotAI/
 * - Or use PUBLIC_URL if set at build time
 * - Or use REACT_APP_API_BASE_URL if you need a separate API server
 */
export const API_BASE = getApiBaseUrl();

// Log the detected API base for debugging (remove in production if desired)
if (process.env.NODE_ENV === 'development') {
  console.log('API_BASE detected as:', API_BASE);
}

