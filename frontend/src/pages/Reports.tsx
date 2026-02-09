import React, { useState, useEffect } from 'react';
import { FileText, Download, Eye, Calendar, Search, BarChart3, Scale, BookOpen, Gavel, PenTool } from 'lucide-react';

interface Report {
  id: string;
  title: string;
  type: 'case-brief' | 'legal-opinion' | 'research-memo' | 'comparative';
  status: 'draft' | 'review' | 'approved' | 'published';
  createdAt: Date;
  updatedAt: Date;
  author: string;
  summary: string;
  tags: string[];
  court?: string;
  citation?: string;
}

const Reports: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [filteredReports, setFilteredReports] = useState<Report[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Mock legal reports data
    const mockReports: Report[] = [
      {
        id: '1',
        title: 'Constitutional Petition Analysis: Right to Fair Hearing',
        type: 'case-brief',
        status: 'published',
        createdAt: new Date('2024-01-15'),
        updatedAt: new Date('2024-01-15'),
        author: 'Legal AI Assistant',
        summary: 'Analysis of constitutional provisions on fair hearing under Article 50 of the Constitution of Kenya.',
        tags: ['Constitutional', 'Fair Hearing', 'Article 50', 'Supreme Court'],
        court: 'Supreme Court',
        citation: '[2024] eKLR 1234'
      },
      {
        id: '2',
        title: 'Land Succession Rights: Comparative Analysis',
        type: 'comparative',
        status: 'approved',
        createdAt: new Date('2024-01-10'),
        updatedAt: new Date('2024-01-12'),
        author: 'Research Team',
        summary: 'Comparative study of land succession rights across East African jurisdictions.',
        tags: ['Land Law', 'Succession', 'Comparative', 'EAC'],
        court: 'High Court'
      },
      {
        id: '3',
        title: 'Employment Law: Unfair Dismissal Precedents',
        type: 'research-memo',
        status: 'review',
        createdAt: new Date('2024-01-08'),
        updatedAt: new Date('2024-01-14'),
        author: 'Legal AI Assistant',
        summary: 'Research memorandum on unfair dismissal case law and evolving judicial interpretation.',
        tags: ['Employment', 'Dismissal', 'Labour Law', 'ELRC'],
        court: 'ELRC'
      },
      {
        id: '4',
        title: 'Criminal Procedure: Bail Application Guidelines',
        type: 'legal-opinion',
        status: 'draft',
        createdAt: new Date('2024-01-05'),
        updatedAt: new Date('2024-01-05'),
        author: 'Legal AI Assistant',
        summary: 'Opinion on bail application procedures and factors considered by courts.',
        tags: ['Criminal', 'Bail', 'Procedure', 'High Court']
      }
    ];

    setReports(mockReports);
    setFilteredReports(mockReports);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let filtered = reports;

    if (searchTerm) {
      filtered = filtered.filter(report =>
        report.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        report.summary.toLowerCase().includes(searchTerm.toLowerCase()) ||
        report.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    if (filterType !== 'all') {
      filtered = filtered.filter(report => report.type === filterType);
    }

    if (filterStatus !== 'all') {
      filtered = filtered.filter(report => report.status === filterStatus);
    }

    setFilteredReports(filtered);
  }, [reports, searchTerm, filterType, filterStatus]);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'case-brief': return <FileText className="w-4 h-4" />;
      case 'legal-opinion': return <Scale className="w-4 h-4" />;
      case 'research-memo': return <BookOpen className="w-4 h-4" />;
      case 'comparative': return <BarChart3 className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'case-brief': return 'bg-legal-maroon-light text-legal-maroon';
      case 'legal-opinion': return 'bg-legal-gold-light text-legal-gold-dark';
      case 'research-memo': return 'bg-blue-50 text-blue-700';
      case 'comparative': return 'bg-purple-50 text-purple-700';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'case-brief': return 'Case Brief';
      case 'legal-opinion': return 'Legal Opinion';
      case 'research-memo': return 'Research Memo';
      case 'comparative': return 'Comparative Analysis';
      default: return type;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'bg-legal-maroon-light text-legal-maroon';
      case 'approved': return 'bg-blue-50 text-blue-700';
      case 'review': return 'bg-legal-gold-light text-legal-gold-dark';
      case 'draft': return 'bg-gray-100 text-gray-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const generateReport = () => {
    const newReport: Report = {
      id: Date.now().toString(),
      title: `AI Legal Analysis - ${new Date().toLocaleDateString()}`,
      type: 'case-brief',
      status: 'draft',
      createdAt: new Date(),
      updatedAt: new Date(),
      author: 'Legal AI Assistant',
      summary: 'AI-generated legal analysis based on current case law and indexed documents.',
      tags: ['AI Generated', 'Legal Analysis', 'Draft']
    };

    setReports(prev => [newReport, ...prev]);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-2 border-legal-maroon border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-legal-maroon to-legal-maroon-dark flex items-center justify-center shadow-legal">
            <Gavel className="w-6 h-6 text-legal-gold" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-legal-text">
              Legal Reports & Briefs
            </h1>
            <p className="text-legal-text-muted">
              Ripoti za Kisheria • Generate and manage legal analyses
            </p>
          </div>
        </div>
        <button
          onClick={generateReport}
          className="px-5 py-2.5 btn-legal rounded-lg flex items-center space-x-2"
        >
          <PenTool className="w-4 h-4" />
          <span>Generate Brief</span>
        </button>
      </div>

      {/* Filters */}
      <div className="legal-card p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-legal-text mb-2">
              Search Reports
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-legal-text-muted w-4 h-4" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by title, content, or tags..."
                className="w-full pl-10 pr-4 py-2.5 border border-legal-maroon/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-maroon focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-legal-text mb-2">
              Report Type
            </label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="w-full px-3 py-2.5 border border-legal-maroon/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-maroon focus:border-transparent"
            >
              <option value="all">All Types</option>
              <option value="case-brief">Case Brief</option>
              <option value="legal-opinion">Legal Opinion</option>
              <option value="research-memo">Research Memo</option>
              <option value="comparative">Comparative Analysis</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-legal-text mb-2">
              Status
            </label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="w-full px-3 py-2.5 border border-legal-maroon/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-maroon focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="published">Published</option>
              <option value="approved">Approved</option>
              <option value="review">Under Review</option>
              <option value="draft">Draft</option>
            </select>
          </div>
        </div>
      </div>

      {/* Reports Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredReports.map((report) => (
          <div key={report.id} className="legal-card hover:shadow-legal-lg transition-all duration-300">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${getTypeColor(report.type)}`}>
                      {getTypeIcon(report.type)}
                      {getTypeLabel(report.type)}
                    </span>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(report.status)}`}>
                      {report.status}
                    </span>
                  </div>
                  <h3 className="text-lg font-serif font-semibold text-legal-text mb-2 line-clamp-2">
                    {report.title}
                  </h3>
                  <p className="text-sm text-legal-text-muted line-clamp-2">
                    {report.summary}
                  </p>
                </div>
              </div>

              {report.citation && (
                <div className="mb-3 p-2 bg-legal-maroon-light rounded-lg">
                  <p className="text-xs font-mono text-legal-maroon">{report.citation}</p>
                  {report.court && <p className="text-xs text-legal-text-muted mt-0.5">{report.court}</p>}
                </div>
              )}

              <div className="flex flex-wrap gap-1.5 mb-4">
                {report.tags.slice(0, 4).map((tag, index) => (
                  <span
                    key={index}
                    className="px-2 py-0.5 bg-law-cream text-law-gray text-xs rounded border border-legal-maroon/10"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between text-xs text-legal-text-muted mb-4 pb-4 border-b border-legal-maroon/10">
                <span>By {report.author}</span>
                <span>{report.createdAt.toLocaleDateString()}</span>
              </div>

              <div className="flex items-center gap-2">
                <button className="flex-1 px-3 py-2 text-sm bg-legal-maroon-light text-legal-maroon rounded-lg hover:bg-legal-maroon/20 transition-colors flex items-center justify-center gap-1.5 font-medium">
                  <Eye className="w-4 h-4" />
                  View
                </button>
                <button className="flex-1 px-3 py-2 text-sm btn-legal rounded-lg flex items-center justify-center gap-1.5">
                  <Download className="w-4 h-4" />
                  Export
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredReports.length === 0 && (
        <div className="text-center py-12">
          <FileText className="w-16 h-16 text-legal-maroon/30 mx-auto mb-4" />
          <h3 className="text-lg font-serif font-semibold text-legal-text mb-2">
            No reports found
          </h3>
          <p className="text-legal-text-muted">
            Try adjusting your search criteria or generate a new report
          </p>
        </div>
      )}

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="legal-card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-legal-maroon-light rounded-xl">
              <FileText className="w-6 h-6 text-legal-maroon" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-legal-text-muted">Total Reports</p>
              <p className="text-2xl font-serif font-bold text-legal-text">{reports.length}</p>
            </div>
          </div>
        </div>

        <div className="legal-card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-legal-maroon-light rounded-xl">
              <Scale className="w-6 h-6 text-legal-maroon" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-legal-text-muted">Published</p>
              <p className="text-2xl font-serif font-bold text-legal-text">
                {reports.filter(r => r.status === 'published').length}
              </p>
            </div>
          </div>
        </div>

        <div className="legal-card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-legal-gold-light rounded-xl">
              <BookOpen className="w-6 h-6 text-legal-gold-dark" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-legal-text-muted">In Review</p>
              <p className="text-2xl font-serif font-bold text-legal-text">
                {reports.filter(r => r.status === 'review').length}
              </p>
            </div>
          </div>
        </div>

        <div className="legal-card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-50 rounded-xl">
              <Calendar className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-legal-text-muted">This Month</p>
              <p className="text-2xl font-serif font-bold text-legal-text">
                {reports.filter(r => r.createdAt.getMonth() === new Date().getMonth()).length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Legal Disclaimer */}
      <div className="bg-legal-gold-light border border-legal-gold/30 rounded-xl p-4 flex items-center gap-3">
        <Scale className="w-5 h-5 text-legal-gold-dark flex-shrink-0" />
        <p className="text-sm text-legal-gold-dark">
          <strong>Disclaimer:</strong> These reports are for informational and research purposes only. 
          They do not constitute legal advice. Consult a qualified advocate for legal matters.
        </p>
      </div>
    </div>
  );
};

export default Reports;
