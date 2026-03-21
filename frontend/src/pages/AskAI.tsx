import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Send, Scale, BookOpen, Gavel, Globe, AlertCircle, MessageSquarePlus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import { API_BASE } from '../utils/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import type { Pluggable, PluggableList } from 'unified';

interface SourceDetail {
  document: string;
  chunks: string[];
}

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  sources?: string[];
  sourcesDetail?: SourceDetail[];
  confidence?: number;
  systemGuidance?: string;
}

interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ApiMessage {
  id: string;
  role: string;
  content: string;
  created_at: string;
  sources_detail?: SourceDetail[];
}

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

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [expandedSourceKey, setExpandedSourceKey] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const getDocumentDisplayName = (path: string) => {
    const parts = path.replace(/\\/g, '/').split('/');
    return parts[parts.length - 1] || path;
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadConversations = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/conversations`);
      setConversations(res.data?.conversations || []);
    } catch (e) {
      console.warn('Failed to load conversations:', e);
      setConversations([]);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const loadConversation = useCallback(async (conversationId: string) => {
    setLoadingConversation(true);
    setCurrentConversationId(conversationId);
    setMessages([]);
    try {
      const res = await axios.get(`${API_BASE}/conversations/${conversationId}`);
      const apiMessages: ApiMessage[] = res.data?.messages || [];
      const msgs: Message[] = apiMessages.map((m) => ({
        id: m.id,
        content: m.content,
        isUser: m.role === 'user',
        timestamp: new Date(m.created_at),
        sourcesDetail: m.sources_detail,
      }));
      setMessages(msgs);
    } catch (e) {
      toast.error('Failed to load conversation');
      console.error(e);
      setCurrentConversationId(null);
    } finally {
      setLoadingConversation(false);
    }
  }, []);

  const startNewChat = useCallback(async () => {
    try {
      const res = await axios.post(`${API_BASE}/conversations`);
      const conv = res.data;
      if (conv?.id) {
        setConversations((prev) => [conv, ...prev]);
        setCurrentConversationId(conv.id);
        setMessages([]);
      }
    } catch (e) {
      toast.error('Failed to start new chat');
      console.error(e);
    }
  }, []);

  const deleteCurrentChat = useCallback(async () => {
    if (!currentConversationId) return;
    try {
      await axios.delete(`${API_BASE}/conversations/${currentConversationId}`);
      setConversations((prev) => prev.filter((c) => c.id !== currentConversationId));
      setMessages([]);
      setCurrentConversationId(null);
      toast.success('Chat deleted');
    } catch (e) {
      toast.error('Failed to delete chat');
      console.error(e);
    }
  }, [currentConversationId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `tmp-${Date.now()}`,
      content: input,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/query`, {
        query: input,
        conversation_id: currentConversationId || undefined,
      });

      const rawAnswer: string = response.data.answer || '';
      let mainContent = normalizeResponseText(rawAnswer);
      let systemGuidance: string | undefined;

      const guidanceSegments = rawAnswer.split('---').map((seg: string) => seg.trim()).filter(Boolean);
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
        sourcesDetail: response.data.sources_detail || undefined,
        confidence: response.data.confidence,
        systemGuidance,
      };

      setMessages((prev) => [...prev, aiMessage]);

      const newConvId = response.data.conversation_id;
      if (newConvId && newConvId !== currentConversationId) {
        setCurrentConversationId(newConvId);
        loadConversations();
      }
    } catch (error) {
      toast.error('Failed to get AI response');
      console.error('Error:', error);
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex bg-legal-bg">
      {/* Sidebar: conversation history */}
      {sidebarOpen && (
        <aside className="w-64 flex-shrink-0 border-r border-legal-border bg-legal-white flex flex-col">
          <div className="p-3 border-b border-legal-border">
            <button
              type="button"
              onClick={startNewChat}
              className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-legal-maroon text-white hover:bg-legal-maroon-dark transition-colors font-medium text-sm"
            >
              <MessageSquarePlus className="w-4 h-4" />
              New Chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            <p className="text-xs font-medium text-legal-text-muted uppercase tracking-wide px-2 py-1.5">
              Past chats
            </p>
            {conversations.length === 0 && (
              <p className="text-sm text-legal-text-muted px-2 py-2">No conversations yet.</p>
            )}
            {conversations.map((conv) => (
              <button
                key={conv.id}
                type="button"
                onClick={() => loadConversation(conv.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg truncate text-sm transition-colors ${
                  currentConversationId === conv.id
                    ? 'bg-legal-maroon-light text-legal-maroon font-medium'
                    : 'text-legal-text hover:bg-legal-bg'
                }`}
                title={conv.title}
              >
                {conv.title || 'New Chat'}
              </button>
            ))}
          </div>
        </aside>
      )}

      <button
        type="button"
        onClick={() => setSidebarOpen((o) => !o)}
        className="flex-shrink-0 w-6 flex items-center justify-center bg-legal-border hover:bg-legal-maroon-light text-legal-text-muted hover:text-legal-maroon transition-colors"
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {sidebarOpen ? '‹' : '›'}
      </button>

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="bg-legal-white border-b border-legal-border p-4 shadow-sm flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-legal-maroon flex items-center justify-center">
                <Scale className="w-5 h-5 text-legal-gold" />
              </div>
              <div>
                <h1 className="text-xl font-serif font-bold text-legal-text">Ask Legal AI</h1>
                <p className="text-sm text-legal-text-muted">Ask questions about your indexed legal documents</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {currentConversationId && (
                <button
                  type="button"
                  onClick={deleteCurrentChat}
                  className="px-3 py-2 text-sm text-legal-text-muted hover:text-legal-maroon hover:bg-legal-maroon-light rounded-lg transition-colors flex items-center gap-1.5"
                  title="Delete this chat"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Chat
                </button>
              )}
              <button
                type="button"
                onClick={startNewChat}
                className="px-4 py-2 text-sm bg-legal-maroon-light text-legal-maroon rounded-lg hover:bg-legal-maroon/20 transition-colors font-medium"
              >
                New Chat
              </button>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loadingConversation && (
            <div className="flex justify-center items-center py-12">
              <div className="flex items-center gap-3 text-legal-text-muted">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-legal-maroon border-t-transparent" />
                <span>Loading conversation...</span>
              </div>
            </div>
          )}
          {!loadingConversation && messages.length === 0 && (
            <div className="text-center py-12">
              <div className="w-20 h-20 mx-auto mb-6 rounded-xl bg-legal-maroon flex items-center justify-center shadow-legal border-4 border-legal-gold">
                <Scale className="w-10 h-10 text-legal-gold" />
              </div>
              <h3 className="text-2xl font-serif font-semibold text-legal-text mb-2">Welcome to National Council for Law Reporting</h3>
              <p className="text-legal-text-muted mb-8 max-w-md mx-auto">
                Your intelligent legal research assistant. Search case law, analyze judgments, and get AI-powered legal insights.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
                <div className="legal-card p-5">
                  <BookOpen className="w-8 h-8 text-legal-maroon mx-auto mb-3" />
                  <h4 className="font-semibold text-legal-text">Case Law Research</h4>
                  <p className="text-sm text-legal-text-muted mt-1">Search and analyze Kenya&apos;s legal judgments</p>
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

          {!loadingConversation && messages.map((message) => {
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
                          <p className="text-xs uppercase tracking-wide text-legal-text-muted font-semibold">Assistant · National Council for Law Reporting</p>
                        </div>
                      </div>

                      <ReactMarkdown
                        remarkPlugins={markdownPlugins}
                        components={markdownComponents}
                        className="markdown-body text-legal-text"
                      >
                        {message.content}
                      </ReactMarkdown>

                      {((message.sourcesDetail && message.sourcesDetail.length > 0) || (message.sources && message.sources.length > 0)) && (
                        <div className="ai-section">
                          <p className="ai-section-title">📚 Sources & Citations</p>
                          {message.sourcesDetail && message.sourcesDetail.length > 0 ? (
                            <div className="mt-2 space-y-2">
                              {message.sourcesDetail.map((sd, docIdx) => {
                                const key = `${message.id}-${docIdx}`;
                                const isExpanded = expandedSourceKey === key;
                                const displayName = getDocumentDisplayName(sd.document);
                                const chunkCount = sd.chunks.length;
                                return (
                                  <div key={key} className="border border-legal-border rounded-lg overflow-hidden bg-legal-bg/50">
                                    <button
                                      type="button"
                                      onClick={() => setExpandedSourceKey(isExpanded ? null : key)}
                                      className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-legal-maroon-light/20 transition-colors"
                                    >
                                      <span className="text-sm font-medium text-legal-text truncate pr-2" title={sd.document}>
                                        {displayName}
                                      </span>
                                      <span className="text-xs text-legal-text-muted flex-shrink-0">
                                        {chunkCount} passage{chunkCount !== 1 ? 's' : ''} {isExpanded ? '▼' : '▶'}
                                      </span>
                                    </button>
                                    {isExpanded && (
                                      <div className="px-4 pb-3 pt-1 border-t border-legal-border space-y-3">
                                        {sd.chunks.map((chunk, chunkIdx) => (
                                          <div key={chunkIdx} className="text-sm text-legal-text-muted bg-white rounded p-3 border border-legal-border/50">
                                            <span className="text-xs font-medium text-legal-maroon block mb-1">Passage {chunkIdx + 1}</span>
                                            <p className="whitespace-pre-wrap">{chunk}</p>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="flex flex-wrap gap-2 mt-2">
                              {message.sources!.map((src, idx) => (
                                <span key={`${src}-${idx}`} className="source-chip">
                                  {src}
                                </span>
                              ))}
                            </div>
                          )}
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
        <div className="px-4 py-2 flex-shrink-0">
          <div className="flex items-center gap-2 text-xs text-legal-gold-dark bg-legal-gold-light rounded-lg px-3 py-2 border border-legal-gold/30">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>This is AI-generated legal information for research purposes only. Not a substitute for professional legal advice.</span>
          </div>
        </div>

        {/* Input */}
        <div className="bg-legal-white border-t border-legal-border p-4 flex-shrink-0">
          <form onSubmit={handleSubmit} className="flex space-x-4">
            <div className="flex-1">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={currentConversationId ? "Continue the conversation..." : "Ask about case law, legal principles, statutes, or get analysis..."}
                className="w-full px-4 py-3 border border-legal-border rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-gold focus:border-transparent text-legal-text placeholder:text-legal-text-muted"
                disabled={isLoading || loadingConversation}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading || loadingConversation}
              className="px-6 py-3 btn-legal rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-gold focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AskAI;
