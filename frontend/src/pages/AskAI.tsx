import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Globe, Scale, BookOpen, Gavel, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import { API_BASE } from '../utils/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import type { Pluggable, PluggableList } from 'unified';

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  sources?: string[];
  confidence?: number;
  systemGuidance?: string;
  roleApplied?: string | null;
}

// Legal roles
const LEGAL_ROLES = [
  'Law Student',
  'Legal Researcher',
  'Paralegal',
  'Advocate',
  'State Counsel',
  'Magistrate',
  'Judge',
  'Journalist / Public'
] as const;

type LegalRole = typeof LEGAL_ROLES[number];

const AskAI: React.FC = () => {
  const normalizeResponseText = (text: string) => {
    let normalized = (text || '').trim();
    if (/^content=/i.test(normalized)) {
      normalized = normalized.replace(/^content='?/i, '');
      normalized = normalized.replace(/'$/i, '');
    }
    normalized = normalized.replace(/\\n/g, '\n').replace(/\\t/g, '\t');
    return normalized.trim();
  };

  const markdownPlugins: PluggableList = useMemo(
    () => [remarkGfm, remarkBreaks as unknown as Pluggable],
    []
  );

  const markdownComponents = useMemo(() => {
    const heading = (Tag: keyof JSX.IntrinsicElements, className: string) =>
      ({ children, ...rest }: any) =>
        React.createElement(Tag, { className, ...rest }, children);

    return {
      p: ({ children, ...rest }: any) => (
        <p className="mb-2 leading-relaxed" {...rest}>
          {children}
        </p>
      ),
      h1: heading('h3', 'text-xl font-serif font-semibold mt-4 mb-2 text-legal-text'),
      h2: heading('h4', 'text-lg font-serif font-semibold mt-4 mb-2 text-legal-text'),
      h3: heading('h5', 'text-base font-semibold mt-3 mb-2 text-legal-text'),
      ul: ({ children, ...rest }: any) => (
        <ul className="mb-3 list-disc list-inside space-y-1" {...rest}>
          {children}
        </ul>
      ),
      ol: ({ children, ...rest }: any) => (
        <ol className="mb-3 list-decimal list-inside space-y-1" {...rest}>
          {children}
        </ol>
      ),
      li: ({ children, ...rest }: any) => (
        <li className="leading-relaxed" {...rest}>
          {children}
        </li>
      ),
      blockquote: ({ children, ...rest }: any) => (
        <blockquote className="border-l-4 border-legal-gold pl-4 italic mb-3 bg-legal-gold-light py-2 rounded-r" {...rest}>
          {children}
        </blockquote>
      ),
      strong: ({ children, ...rest }: any) => (
        <strong className="font-semibold text-legal-maroon" {...rest}>
          {children}
        </strong>
      ),
    };
  }, []);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useWebSearch, setUseWebSearch] = useState(false);
  const [role, setRole] = useState<LegalRole | ''>('Advocate');
  const [presetId, setPresetId] = useState<string>('');
  const [usePreset, setUsePreset] = useState<boolean>(true);
  const [serverPrompts, setServerPrompts] = useState<{ id: string; title: string; description: string }[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get(`${API_BASE}/prompts`);
        const list = (res.data?.prompts || []).filter((p: any) => p.is_active !== false);
        setServerPrompts(list.map((p: any) => ({ id: p.id, title: p.title, description: p.description })));
        if (list.length > 0) setPresetId(list[0].id);
      } catch (e) {
        const fallback = [
          { id: 'case-summary', title: 'Case Summary', description: 'Summarize the key facts, issues, holdings, and reasoning of a case.' },
          { id: 'legal-principle', title: 'Legal Principle Extraction', description: 'Extract the core legal principles and ratio decidendi from a judgment.' },
          { id: 'case-precedents', title: 'Case Precedents', description: 'Find and analyze relevant precedents and how they apply.' },
          { id: 'statutory-interpretation', title: 'Statutory Interpretation', description: 'Interpret statutes and legal provisions in context.' },
          { id: 'legal-opinion', title: 'Legal Opinion (Non-binding)', description: 'Provide a preliminary legal analysis on a matter.' },
          { id: 'comparative-law', title: 'Comparative Case Law', description: 'Compare legal approaches across different jurisdictions.' }
        ];
        setServerPrompts(fallback);
        setPresetId('case-summary');
      }
    })();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const system_prompt = usePreset ? presetId : undefined;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/query`, {
        query: input,
        use_web_search: useWebSearch,
        system_prompt,
        user_rank: role || undefined
      });

      const rawAnswer: string = response.data.answer || '';
      let mainContent = normalizeResponseText(rawAnswer);
      let systemGuidance;

      const guidanceSegments = rawAnswer.split('---').map(seg => seg.trim()).filter(Boolean);
      if (guidanceSegments.length > 1) {
        mainContent = normalizeResponseText(guidanceSegments[0]);
        const guidanceCandidate = guidanceSegments.slice(1).join(' --- ');
        systemGuidance = normalizeResponseText(
          guidanceCandidate.replace(/^System guidance applied:\s*/i, '')
        );
      }

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: mainContent,
        isUser: false,
        timestamp: new Date(),
        sources: response.data.sources,
        confidence: response.data.confidence,
        systemGuidance,
        roleApplied: response.data.rank_applied || null
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      toast.error('Failed to get AI response');
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => setMessages([]);

  return (
    <div className="h-full flex flex-col bg-legal-bg">
      {/* Header */}
      <div className="bg-legal-white border-b border-legal-border p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-legal-maroon flex items-center justify-center">
              <Scale className="w-5 h-5 text-legal-gold" />
            </div>
            <div>
              <h1 className="text-xl font-serif font-bold text-legal-text">Ask Legal AI</h1>
              <p className="text-sm text-legal-text-muted">Legal Research Assistant</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input 
                type="checkbox" 
                checked={useWebSearch} 
                onChange={(e) => setUseWebSearch(e.target.checked)} 
                className="w-4 h-4 text-legal-gold focus:ring-legal-gold border-legal-border rounded" 
              />
              <span className="text-sm text-legal-text-muted">Include Web Sources</span>
            </label>
            <button 
              onClick={clearChat} 
              className="px-4 py-2 text-sm bg-legal-maroon-light text-legal-maroon rounded-lg hover:bg-legal-maroon/20 transition-colors font-medium"
            >
              Clear Chat
            </button>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-legal-white border-b border-legal-border p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-legal-text mb-2">
              Your Role
            </label>
            <select 
              value={role} 
              onChange={(e) => setRole(e.target.value as LegalRole)} 
              className="w-full px-3 py-2.5 border border-legal-border rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-gold focus:border-transparent bg-white text-legal-text"
            >
              <option value="">(General User)</option>
              {LEGAL_ROLES.map(r => (<option key={r} value={r}>{r}</option>))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-legal-text mb-2">
              Analysis Type
            </label>
            <select 
              value={presetId} 
              onChange={(e) => setPresetId(e.target.value)} 
              className="w-full px-3 py-2.5 border border-legal-border rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-gold focus:border-transparent bg-white text-legal-text"
            >
              {serverPrompts.map(p => (<option key={p.id} value={p.id}>{p.title}</option>))}
            </select>
            <p className="text-xs text-legal-text-muted mt-1.5">{serverPrompts.find(p => p.id === presetId)?.description}</p>
          </div>
          <div className="flex items-end">
            <label className="inline-flex items-center space-x-2 cursor-pointer">
              <input 
                type="checkbox" 
                className="w-4 h-4 text-legal-gold focus:ring-legal-gold border-legal-border rounded" 
                checked={usePreset} 
                onChange={(e) => setUsePreset(e.target.checked)} 
              />
              <span className="text-sm text-legal-text-muted">Apply analysis preset</span>
            </label>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="w-20 h-20 mx-auto mb-6 rounded-xl bg-legal-maroon flex items-center justify-center shadow-legal border-4 border-legal-gold">
              <Scale className="w-10 h-10 text-legal-gold" />
            </div>
            <h3 className="text-2xl font-serif font-semibold text-legal-text mb-2">Welcome to Kenya Law AI</h3>
            <p className="text-legal-text-muted mb-8 max-w-md mx-auto">
              Your intelligent legal research assistant. Search case law, analyze judgments, and get AI-powered legal insights.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
              <div className="legal-card p-5">
                <BookOpen className="w-8 h-8 text-legal-maroon mx-auto mb-3" />
                <h4 className="font-semibold text-legal-text">Case Law Research</h4>
                <p className="text-sm text-legal-text-muted mt-1">Search and analyze Kenya's legal judgments</p>
              </div>
              <div className="legal-card p-5">
                <Gavel className="w-8 h-8 text-legal-gold mx-auto mb-3" />
                <h4 className="font-semibold text-legal-text">Legal Analysis</h4>
                <p className="text-sm text-legal-text-muted mt-1">Get AI-powered interpretation of legal principles</p>
              </div>
              <div className="legal-card p-5">
                <Globe className="w-8 h-8 text-legal-maroon-dark mx-auto mb-3" />
                <h4 className="font-semibold text-legal-text">Statute Search</h4>
                <p className="text-sm text-legal-text-muted mt-1">Find relevant laws and regulations</p>
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => {
          const isUser = message.isUser;
          return (
            <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-3xl rounded-lg ${
                  isUser ? 'bg-legal-maroon text-white px-5 py-4' : 'bg-transparent'
                }`}
              >
                {isUser ? (
                  <div>
                    <div className="text-xs uppercase tracking-wide opacity-70 mb-1">Your Query</div>
                    <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
                    <div className="text-xs opacity-70 mt-2">{message.timestamp.toLocaleTimeString()}</div>
                  </div>
                ) : (
                  <div className="ai-response-card">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-lg bg-legal-maroon-light flex items-center justify-center">
                          <Scale className="w-4 h-4 text-legal-maroon" />
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-legal-text-muted font-semibold">Kenya Law AI Response</p>
                          {message.roleApplied && (
                            <p className="text-xs text-legal-maroon">Tailored for {message.roleApplied}</p>
                          )}
                        </div>
                      </div>
                      {typeof message.confidence === 'number' && (
                        <span className="ai-badge">
                          <Scale className="w-3 h-3" />
                          Confidence {Math.round(message.confidence * 100)}%
                        </span>
                      )}
                    </div>

                    <ReactMarkdown
                      remarkPlugins={markdownPlugins}
                      components={markdownComponents}
                      className="markdown-body text-legal-text"
                    >
                      {message.content}
                    </ReactMarkdown>

                    {message.sources && message.sources.length > 0 && (
                      <div className="ai-section">
                        <p className="ai-section-title">📚 Sources & Citations</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {message.sources.map((src, idx) => (
                            <span key={`${src}-${idx}`} className="source-chip">
                              {src}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {message.systemGuidance && (
                      <div className="guidance-box">
                        <p className="ai-section-title mb-1">⚖️ Analysis Framework</p>
                        <p className="text-sm text-legal-text-muted leading-relaxed">{message.systemGuidance}</p>
                      </div>
                    )}

                    <div className="ai-meta-row">
                      <span>{message.timestamp.toLocaleTimeString()}</span>
                      {message.roleApplied && <span>Role: {message.roleApplied}</span>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-legal-text px-5 py-4 rounded-lg shadow-legal border border-legal-border">
              <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-legal-maroon border-t-transparent"></div>
                <span className="text-legal-text-muted">Analyzing legal query...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Legal Disclaimer */}
      <div className="px-4 py-2">
        <div className="flex items-center gap-2 text-xs text-legal-gold-dark bg-legal-gold-light rounded-lg px-3 py-2 border border-legal-gold/30">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>This is AI-generated legal information for research purposes only. Not a substitute for professional legal advice.</span>
        </div>
      </div>

      {/* Input */}
      <div className="bg-legal-white border-t border-legal-border p-4">
        <form onSubmit={handleSubmit} className="flex space-x-4">
          <div className="flex-1">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about case law, legal principles, statutes, or get analysis..."
              className="w-full px-4 py-3 border border-legal-border rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-gold focus:border-transparent text-legal-text placeholder:text-legal-text-muted"
              disabled={isLoading}
            />
          </div>
          <button 
            type="submit" 
            disabled={!input.trim() || isLoading} 
            className="px-6 py-3 btn-legal rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-gold focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default AskAI;
