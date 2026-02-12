import React from 'react';
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
import MapWidget from '../components/MapWidget';
import MetricCard from '../components/MetricCard';

const Dashboard: React.FC = () => {
  const metrics = [
    { title: 'Judgments Indexed', value: '12,456', change: '+156', changeType: 'increase' as const, icon: BookOpen, color: 'maroon' as const },
    { title: 'Active Cases', value: '847', change: '+23', changeType: 'increase' as const, icon: Scale, color: 'gold' as const },
    { title: 'Courts Covered', value: '5', change: '', changeType: 'neutral' as const, icon: Building2, color: 'maroon' as const },
    { title: 'AI Queries Today', value: '1,234', change: '+89', changeType: 'increase' as const, icon: MessageSquare, color: 'gold' as const }
  ];

  const recentJudgments = [
    {
      id: 1,
      caseName: 'Republic v. John Kamau',
      court: 'High Court',
      citation: '[2024] eKLR 1234',
      date: '2 hours ago',
      type: 'Criminal'
    },
    {
      id: 2,
      caseName: 'Mwangi & Another v. KRA',
      court: 'Court of Appeal',
      citation: '[2024] eKLR 1189',
      date: '5 hours ago',
      type: 'Tax'
    },
    {
      id: 3,
      caseName: 'In Re: Estate of Ochieng',
      court: 'High Court',
      citation: '[2024] eKLR 1156',
      date: '1 day ago',
      type: 'Succession'
    },
    {
      id: 4,
      caseName: 'Wanjiku v. Nairobi County',
      court: 'ELC',
      citation: '[2024] eKLR 1098',
      date: '2 days ago',
      type: 'Land'
    }
  ];

  const courtStats = [
    { name: 'Supreme Court', count: 234, color: 'bg-legal-maroon' },
    { name: 'Court of Appeal', count: 1567, color: 'bg-legal-maroon/80' },
    { name: 'High Court', count: 8234, color: 'bg-legal-gold' },
    { name: 'ELC', count: 1456, color: 'bg-legal-gold/80' },
    { name: 'ELRC', count: 965, color: 'bg-legal-maroon/60' }
  ];

  const getCourtBadgeClass = (court: string) => {
    switch (court) {
      case 'Supreme Court': return 'court-badge supreme';
      case 'Court of Appeal': return 'court-badge appeal';
      case 'High Court': return 'court-badge high';
      default: return 'court-badge high';
    }
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
                alt="Kenya Law Reports" 
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold tracking-tight">Kenya Law Reports AI</h1>
              <p className="text-white/80 mt-1">Legal intelligence and case law for Kenya</p>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white/10 backdrop-blur rounded-lg p-4 border border-white/10">
              <p className="text-sm text-white/70">Legal Corpus</p>
              <p className="mt-1 text-2xl font-serif font-bold text-legal-gold">12,456+</p>
              <p className="text-xs text-white/60">Judgments indexed</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4 border border-white/10">
              <p className="text-sm text-white/70">Coverage</p>
              <p className="mt-1 text-2xl font-serif font-bold text-legal-gold">1963 – 2024</p>
              <p className="text-xs text-white/60">Years of jurisprudence</p>
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
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
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
        {/* Court Distribution */}
        <div className="lg:col-span-2">
          <div className="legal-card p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-xl font-serif font-semibold text-legal-text">Court Distribution</h3>
              </div>
              <TrendingUp className="w-5 h-5 text-legal-gold" />
            </div>
            
            {/* Court Stats */}
            <div className="space-y-4">
              {courtStats.map((court, index) => (
                <div key={index} className="flex items-center gap-4">
                  <div className="w-32 text-sm font-medium text-legal-text">{court.name}</div>
                  <div className="flex-1 h-8 bg-legal-maroon-light rounded overflow-hidden">
                    <div 
                      className={`h-full ${court.color} rounded flex items-center justify-end pr-3 transition-all duration-500`}
                      style={{ width: `${(court.count / 8234) * 100}%` }}
                    >
                      <span className="text-xs font-semibold text-white">{court.count.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Map Widget */}
            <div className="mt-6 pt-6 border-t border-legal-border">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-legal-text">Courts by Region</h4>
              </div>
              <MapWidget />
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
            {recentJudgments.map((judgment) => (
              <div
                key={judgment.id}
                className="p-4 rounded-lg bg-legal-bg border border-legal-border hover:border-legal-gold/50 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-serif font-semibold text-legal-text text-sm truncate">
                      {judgment.caseName}
                    </h4>
                    <p className="text-xs text-legal-maroon font-mono mt-1">{judgment.citation}</p>
                  </div>
                  <span className={getCourtBadgeClass(judgment.court)}>
                    {judgment.court}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-3 text-xs text-legal-text-muted">
                  <span className="px-2 py-0.5 bg-legal-gold-light text-legal-gold-dark rounded border border-legal-gold/30">
                    {judgment.type}
                  </span>
                  <span>{judgment.date}</span>
                </div>
              </div>
            ))}
          </div>

          <button className="w-full mt-4 py-2.5 text-sm font-medium text-legal-maroon hover:text-legal-maroon-dark border border-legal-maroon/30 rounded-lg hover:bg-legal-maroon-light transition-colors">
            View All Judgments
          </button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="legal-card p-6">
        <h3 className="text-xl font-serif font-semibold text-legal-text mb-2">Quick Actions</h3>
        <p className="text-sm text-legal-text-muted mb-4">Shortcuts</p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <button className="flex items-center space-x-3 p-4 rounded-lg btn-legal">
            <Search className="w-5 h-5" />
            <div className="text-left">
              <div className="font-medium">Search Case Law</div>
            </div>
          </button>
          <button className="flex items-center space-x-3 p-4 rounded-lg btn-legal">
            <Scale className="w-5 h-5" />
            <div className="text-left">
              <div className="font-medium">Ask Legal AI</div>
            </div>
          </button>
          <button className="flex items-center space-x-3 p-4 rounded-lg btn-legal-maroon">
            <FileUp className="w-5 h-5" />
            <div className="text-left">
              <div className="font-medium">Upload Judgment</div>
            </div>
          </button>
          <button className="flex items-center space-x-3 p-4 rounded-lg btn-legal">
            <FileText className="w-5 h-5" />
            <div className="text-left">
              <div className="font-medium">Generate Brief</div>
            </div>
          </button>
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
