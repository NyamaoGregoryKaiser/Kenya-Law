import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Scale, 
  BookOpen, 
  FileText, 
  Gavel,
  Clock,
  TrendingUp,
  Building2,
  Search,
  FileUp,
  MessageSquare
} from 'lucide-react';
import axios from 'axios';
import MetricCard from '../components/MetricCard';
import { API_BASE } from '../utils/api';

interface RecentDocument {
  filename: string;
  uploaded_at: string;
  indexed_at: string | null;
}

interface DataSources {
  case_law?: {
    total?: number;
    complete_total?: number;
    by_court?: Record<string, number>;
  };
  legislation?: {
    total?: number;
    complete_total?: number;
    acts_in_force?: number;
    repealed_statutes?: number;
  };
  kenya_gazette?: {
    total?: number;
    complete_total?: number;
    years?: number[];
  };
}

const Dashboard: React.FC = () => {
  const [metricsData, setMetricsData] = React.useState<{
    judgments_indexed: number;
    documents_uploaded: number;
    ai_queries_today: number;
    total_ai_queries: number;
    active_users_today?: number;
    active_users_7d?: number;
    last_updated: string;
    recent_documents?: RecentDocument[];
    coverage_min_year?: number | null;
    coverage_max_year?: number | null;
    data_sources?: DataSources | null;
  } | null>(null);

  React.useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get(`${API_BASE}/dashboard/metrics`);
        setMetricsData(res.data);
      } catch (e) {
        console.error('Failed to load dashboard metrics', e);
      }
    };
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, []);

  const metrics = [
    { 
      title: 'Judgments Indexed', 
      value: (metricsData?.judgments_indexed ?? 0).toLocaleString(), 
      change: '', 
      changeType: 'neutral' as const, 
      icon: BookOpen, 
      color: 'maroon' as const 
    },
    { 
      title: 'Documents Uploaded', 
      value: (metricsData?.documents_uploaded ?? 0).toLocaleString(), 
      change: '', 
      changeType: 'neutral' as const, 
      icon: FileText, 
      color: 'gold' as const 
    },
    { 
      title: 'Active Users', 
      value: (metricsData?.active_users_today ?? 0).toLocaleString(), 
      change: `7d: ${(metricsData?.active_users_7d ?? 0).toLocaleString()}`,
      changeType: 'neutral' as const, 
      icon: Building2, 
      color: 'maroon' as const 
    },
    { 
      title: 'AI Queries Today', 
      value: (metricsData?.ai_queries_today ?? 0).toLocaleString(), 
      change: '', 
      changeType: 'neutral' as const, 
      icon: MessageSquare, 
      color: 'gold' as const 
    }
  ];

  const recentDocs = metricsData?.recent_documents ?? [];
  const dataSources: DataSources | undefined | null = metricsData?.data_sources;
  // Percentages should reflect COMPLETE document status by source
  const caseLawTotal = dataSources?.case_law?.total ?? 0;
  const legislationTotal = dataSources?.legislation?.total ?? 0;
  const gazetteTotal = dataSources?.kenya_gazette?.total ?? 0;
  const caseLawComplete = dataSources?.case_law?.complete_total ?? caseLawTotal;
  const legislationComplete = dataSources?.legislation?.complete_total ?? legislationTotal;
  const gazetteComplete = dataSources?.kenya_gazette?.complete_total ?? gazetteTotal;
  const allSourcesTotal = caseLawComplete + legislationComplete + gazetteComplete;
  const pct = (v: number) => (allSourcesTotal > 0 ? Math.round((v / allSourcesTotal) * 100) : 0);

  const formatRelativeTime = (iso: string | null) => {
    if (!iso) return '—';
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      {/* Hero Banner - Maroon */}
      <div className="relative overflow-hidden rounded-lg border border-legal-border legal-gradient">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute inset-0" style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }} />
        </div>
        <div className="relative p-8 text-white">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 rounded-lg bg-white flex items-center justify-center border-2 border-legal-gold/50 p-1">
              <img
                src="/assets/legal/kenya-law-logo.png"
                alt="National Council for Law Reporting logo"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <div className="text-white/80 text-sm mt-1">
                Explore indexed legal documents and analytics.
              </div>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-white/10 backdrop-blur rounded-lg p-4 border border-white/10">
              <p className="text-sm text-white/70">Legal Corpus</p>
              <p className="mt-1 text-2xl font-serif font-bold text-legal-gold">
                {(metricsData?.judgments_indexed ?? 0).toLocaleString()}+
              </p>
              <p className="text-xs text-white/60">Judgments indexed</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4 border border-white/10">
              <p className="text-sm text-white/70">Motto</p>
              <p className="mt-1 font-serif font-semibold text-legal-gold">Justice and Equality</p>
            </div>
          </div>
        </div>
        {/* Gold accent bar */}
        <div className="h-1.5 bg-legal-gold" />
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-serif font-bold text-legal-text">Judicial Dashboard</h2>
          <p className="text-legal-text-muted mt-1">Legal intelligence and case law overview</p>
        </div>
        <div className="flex items-center space-x-2 text-sm text-legal-text-muted">
          <Clock className="w-4 h-4" />
          <span>Last updated: {metricsData?.last_updated ? new Date(metricsData.last_updated).toLocaleTimeString() : '—'}</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric, index) => (
          <MetricCard key={index} {...metric} />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Data Sources */}
        <div className="lg:col-span-2">
          <div className="legal-card p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-xl font-serif font-semibold text-legal-text">Data Sources</h3>
                <p className="text-sm text-legal-text-muted mt-1">
                  Breakdown of indexed documents by source type.
                </p>
              </div>
              <TrendingUp className="w-5 h-5 text-legal-gold" />
            </div>

            <div className="space-y-4">
              <div className="text-xs text-legal-text-muted">
                Total indexed across sources: {allSourcesTotal.toLocaleString()}
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-legal-text">Case law documents</p>
                    <span className="text-sm font-semibold text-legal-maroon">
                      {caseLawTotal.toLocaleString()} ({pct(caseLawComplete)}%)
                    </span>
                  </div>
                  <p className="text-xs text-legal-text-muted mb-1">
                    Courts: {(dataSources?.case_law?.by_court && Object.keys(dataSources.case_law.by_court).length) || 0}
                  </p>
                  <div className="h-2 rounded bg-legal-bg border border-legal-border overflow-hidden">
                    <div className="h-full bg-legal-maroon" style={{ width: `${pct(caseLawComplete)}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-legal-text">Legislation documents</p>
                    <span className="text-sm font-semibold text-legal-maroon">
                      {legislationTotal.toLocaleString()} ({pct(legislationComplete)}%)
                    </span>
                  </div>
                  <p className="text-xs text-legal-text-muted mb-1">
                    Acts in force: {dataSources?.legislation?.acts_in_force ?? 0}, Repealed: {dataSources?.legislation?.repealed_statutes ?? 0}
                  </p>
                  <div className="h-2 rounded bg-legal-bg border border-legal-border overflow-hidden">
                    <div className="h-full bg-legal-gold" style={{ width: `${pct(legislationComplete)}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-legal-text">Kenya Gazette documents</p>
                    <span className="text-sm font-semibold text-legal-maroon">
                      {gazetteTotal.toLocaleString()} ({pct(gazetteComplete)}%)
                    </span>
                  </div>
                  <p className="text-xs text-legal-text-muted mb-1">
                    {dataSources?.kenya_gazette?.years && dataSources.kenya_gazette.years.length > 0
                      ? (() => {
                          const years = dataSources.kenya_gazette!.years!;
                          const minY = years[0];
                          const maxY = years[years.length - 1];
                          return minY === maxY ? `Year ${minY}` : `Years ${minY} – ${maxY}`;
                        })()
                      : 'No gazettes indexed yet'}
                  </p>
                  <div className="h-2 rounded bg-legal-bg border border-legal-border overflow-hidden">
                    <div className="h-full bg-legal-maroon-dark" style={{ width: `${pct(gazetteComplete)}%` }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Judgments */}
        <div className="legal-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-serif font-semibold text-legal-text">Recent Judgments</h3>
            </div>
            <Gavel className="w-5 h-5 text-legal-gold" />
          </div>
          
          <div className="space-y-4">
            {recentDocs.length === 0 && (
              <p className="text-sm text-legal-text-muted py-4">No indexed judgments yet. Upload documents from the Uploads page.</p>
            )}
            {recentDocs.map((doc) => (
              <div
                key={doc.filename}
                className="p-4 rounded-lg bg-legal-bg border border-legal-border hover:border-legal-gold/50 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-serif font-semibold text-legal-text text-sm truncate" title={doc.filename}>
                      {doc.filename}
                    </h4>
                    <p className="text-xs text-legal-maroon font-mono mt-1 truncate">{doc.filename}</p>
                  </div>
                  <span className="court-badge high">Indexed</span>
                </div>
                <div className="flex items-center justify-between mt-3 text-xs text-legal-text-muted">
                  <span className="px-2 py-0.5 bg-legal-gold-light text-legal-gold-dark rounded border border-legal-gold/30">
                    Document
                  </span>
                  <span>{formatRelativeTime(doc.indexed_at ?? doc.uploaded_at)}</span>
                </div>
              </div>
            ))}
          </div>

          <Link
            to="/uploads"
            className="block w-full mt-4 py-2.5 text-sm font-medium text-center text-legal-maroon hover:text-legal-maroon-dark border border-legal-maroon/30 rounded-lg hover:bg-legal-maroon-light transition-colors"
          >
            View All Documents
          </Link>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="legal-card p-6">
        <h3 className="text-xl font-serif font-semibold text-legal-text mb-2">Quick Actions</h3>
        <p className="text-sm text-legal-text-muted mb-4">Shortcuts</p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Link to="/ask-ai" className="flex items-center space-x-3 p-4 rounded-lg btn-legal">
            <Search className="w-5 h-5" />
            <div className="text-left">
              <div className="font-medium">Search Case Law</div>
            </div>
          </Link>
          <Link to="/ask-ai" className="flex items-center space-x-3 p-4 rounded-lg btn-legal">
            <Scale className="w-5 h-5" />
            <div className="text-left">
              <div className="font-medium">Ask Legal AI</div>
            </div>
          </Link>
          <Link to="/uploads" className="flex items-center space-x-3 p-4 rounded-lg btn-legal-maroon">
            <FileUp className="w-5 h-5" />
            <div className="text-left">
              <div className="font-medium">Upload Judgment</div>
            </div>
          </Link>
          <Link to="/ask-ai" className="flex items-center space-x-3 p-4 rounded-lg btn-legal">
            <FileText className="w-5 h-5" />
            <div className="text-left">
              <div className="font-medium">Generate Brief</div>
            </div>
          </Link>
        </div>
      </div>

      {/* Legal Disclaimer */}
      <div className="legal-disclaimer">
        <strong>Disclaimer:</strong> This platform provides legal information for research purposes only. 
        It does not constitute legal advice. Please consult a qualified advocate for legal matters.
      </div>
    </div>
  );
};

export default Dashboard;
