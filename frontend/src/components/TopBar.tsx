import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Bell, User, LogOut, Settings, Scale } from 'lucide-react';

const TopBar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="bg-legal-white border-b border-legal-border">
      {/* Maroon/Gold accent bar */}
      <div className="header-accent" />
      
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <img 
              src="/assets/legal/kenya-law-logo.png" 
              alt="Kenya Law Reports" 
              className="w-10 h-10 object-contain"
            />
            <div>
              <h2 className="text-xl font-serif font-bold text-legal-text">Kenya Law Reports AI</h2>
              <span className="text-sm text-legal-text-muted">Akili Bandia ya Sheria • Legal Intelligence Platform</span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <button 
              className="p-2 text-legal-text-muted hover:text-legal-maroon hover:bg-legal-maroon-light rounded-lg transition-colors" 
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
            </button>
            <button 
              className="p-2 text-legal-text-muted hover:text-legal-maroon hover:bg-legal-maroon-light rounded-lg transition-colors" 
              title="Settings"
            >
              <Settings className="w-5 h-5" />
            </button>
            
            <div className="h-8 w-px bg-legal-border" />
            
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 bg-legal-maroon rounded-lg flex items-center justify-center shadow-sm">
                <User className="w-4 h-4 text-white" />
              </div>
              <div className="text-sm">
                <div className="font-medium text-legal-text">{user?.name}</div>
                <div className="text-legal-text-muted capitalize text-xs">{user?.role}</div>
              </div>
              <button 
                onClick={logout} 
                className="p-2 text-legal-text-muted hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" 
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default TopBar;
