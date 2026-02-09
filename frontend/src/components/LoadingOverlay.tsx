import React from 'react';
import { Scale } from 'lucide-react';

const LoadingOverlay: React.FC = () => {
  return (
    <div className="fixed inset-0 bg-legal-maroon flex items-center justify-center z-50">
      <div className="text-center">
        <div className="w-28 h-28 mx-auto mb-6 bg-white rounded-2xl flex items-center justify-center border-4 border-legal-gold animate-pulse p-2">
          <img 
            src="/assets/legal/kenya-law-logo.png" 
            alt="Kenya Law Reports" 
            className="w-full h-full object-contain"
          />
        </div>
        <h2 className="text-2xl font-serif font-bold text-white mb-2">Kenya Law Reports AI</h2>
        <p className="text-white/70 mb-4">Loading legal intelligence system...</p>
        <div className="flex items-center justify-center gap-2">
          <div className="w-2 h-2 bg-legal-gold rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-legal-gold rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-legal-gold rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
};

export default LoadingOverlay;
