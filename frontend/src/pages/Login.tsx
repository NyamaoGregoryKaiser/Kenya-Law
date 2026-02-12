import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Eye, EyeOff, BookOpen } from 'lucide-react';
import toast from 'react-hot-toast';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(email, password);
      toast.success('Login successful!');
      navigate('/');
    } catch (error) {
      toast.error('Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-legal-maroon flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background pattern */}
      <div 
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />
      
      <div className="max-w-md w-full relative">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="w-28 h-28 bg-white rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-2xl relative border-4 border-legal-gold p-2">
            <img 
              src="/assets/legal/kenya-law-logo.png" 
              alt="Kenya Law Reports" 
              className="w-full h-full object-contain"
            />
          </div>
          <h1 className="text-3xl font-serif font-bold text-white mb-2">
            Kenya Law Reports AI
          </h1>
          <p className="text-white/70">
            Legal intelligence for Kenya&apos;s law reports
          </p>
          <div className="mt-4 flex items-center justify-center gap-2">
            <BookOpen className="w-4 h-4 text-legal-gold" />
            <span className="text-legal-gold text-sm font-medium">Justice and Equality</span>
          </div>
        </div>

        {/* Login Form */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-2xl font-serif font-bold text-legal-text mb-2 text-center">
            Welcome Back
          </h2>
          <p className="text-legal-text-muted text-center mb-6">Sign in to access legal intelligence</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-legal-text mb-2">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-legal-border rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-gold focus:border-transparent transition-all"
                placeholder="advocate@kenyalaw.ai"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-legal-text mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 pr-12 border border-legal-border rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-gold focus:border-transparent transition-all"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-legal-text-muted hover:text-legal-maroon transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-legal py-3 px-4 rounded-lg font-semibold focus:outline-none focus:ring-2 focus:ring-legal-gold focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-5 h-5 border-2 border-legal-text/30 border-t-legal-text rounded-full animate-spin" />
                  Signing In...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <div className="text-center mt-8">
          <p className="text-white/50 text-sm">
            © 2024 Kenya Law Reports AI. All rights reserved.
          </p>
          <p className="text-white/30 text-xs mt-1">
            Powered by Legal Intelligence
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
