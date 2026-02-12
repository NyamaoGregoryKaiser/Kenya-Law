import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Scale,
  Upload, 
  FileText,
  BookOpen,
  Gavel
} from 'lucide-react';

const Sidebar: React.FC = () => {
  const menuItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Ask Legal AI', path: '/ask-ai', icon: Scale },
    { name: 'Case Uploads', path: '/uploads', icon: Upload },
    { name: 'Legal Reports', path: '/reports', icon: FileText },
    { name: 'Case Explorer', path: '/explorer', icon: BookOpen }
  ];

  return (
    <div className="w-64 sidebar-legal text-white min-h-screen relative">
      {/* Header with Legal Branding */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center space-x-3">
          <img 
            src="/assets/legal/kenya-law-logo.png" 
            alt="Kenya Law Reports" 
            className="w-12 h-12 object-contain"
          />
          <div>
            <h1 className="text-lg font-serif font-bold text-white">Kenya Law</h1>
            <p className="text-xs text-legal-gold">Reports AI</p>
          </div>
        </div>
        {/* Gold accent line */}
        <div className="mt-4 h-1 bg-gradient-to-r from-legal-gold via-legal-gold-dark to-transparent rounded-full" />
      </div>

      {/* Navigation */}
      <nav className="mt-6">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item flex items-center space-x-3 px-6 py-3.5 text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'active bg-white/15 text-white border-r-4 border-legal-gold'
                    : 'text-white/80 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon className="w-5 h-5" />
              <div>
                <div className="font-medium">{item.name}</div>
              </div>
            </NavLink>
          );
        })}
      </nav>

      {/* Quick Stats */}
      <div className="mx-4 mt-8 p-4 bg-white/10 rounded-lg border border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <Gavel className="w-4 h-4 text-legal-gold" />
          <span className="text-xs font-semibold text-legal-gold uppercase tracking-wide">Quick Stats</span>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-white/70">Judgments</span>
            <span className="text-legal-gold font-semibold">12,456</span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/70">Courts</span>
            <span className="text-legal-gold font-semibold">5</span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/70">AI Queries</span>
            <span className="text-legal-gold font-semibold">1,234</span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="absolute bottom-0 w-64 p-4 border-t border-white/10">
        <div className="text-center">
          <p className="text-xs text-white/50">Powered by</p>
          <p className="text-sm font-serif text-legal-gold">Kenya Law Reports</p>
          <p className="text-xs text-white/40 mt-1">Justice and Equality</p>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
