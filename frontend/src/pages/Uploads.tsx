import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Trash2, Eye, Download, CheckCircle, AlertCircle, Scale, BookOpen, Gavel } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import { API_BASE } from '../utils/api';

interface UploadedDocument {
  id: string;
  filename: string;
  size: number;
  type: string;
  status: 'uploading' | 'indexed' | 'error';
  uploadedAt: Date;
  indexedAt?: Date;
  // Legal metadata
  caseName?: string;
  court?: string;
  year?: string;
  legalArea?: string;
  citation?: string;
}

const COURTS = [
  'Supreme Court',
  'Court of Appeal',
  'High Court',
  'Environment & Land Court (ELC)',
  'Employment & Labour Relations Court (ELRC)',
  'Magistrates Court',
  'Tribunal'
];

const LEGAL_AREAS = [
  'Constitutional',
  'Criminal',
  'Civil',
  'Commercial',
  'Land & Environment',
  'Family',
  'Employment',
  'Tax',
  'Administrative',
  'Other'
];

const Uploads: React.FC = () => {
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showMetadataForm, setShowMetadataForm] = useState(false);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState({
    caseName: '',
    court: '',
    year: new Date().getFullYear().toString(),
    legalArea: '',
    citation: ''
  });

  const uploadFile = async (file: File, meta: typeof metadata) => {
    const document: UploadedDocument = {
      id: Date.now().toString() + Math.random(),
      filename: file.name,
      size: file.size,
      type: file.type,
      status: 'uploading',
      uploadedAt: new Date(),
      ...meta
    };

    setDocuments(prev => [document, ...prev]);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setDocuments(prev =>
        prev.map(doc =>
          doc.id === document.id
            ? {
                ...doc,
                status: response.data.indexed ? 'indexed' : 'error',
                indexedAt: response.data.indexed ? new Date() : undefined
              }
            : doc
        )
      );

      toast.success(`${file.name} uploaded and indexed successfully`);
    } catch (error) {
      setDocuments(prev =>
        prev.map(doc =>
          doc.id === document.id
            ? { ...doc, status: 'error' }
            : doc
        )
      );
      toast.error(`Failed to upload ${file.name}`);
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setCurrentFile(acceptedFiles[0]);
      setShowMetadataForm(true);
    }
  }, []);

  const handleMetadataSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentFile) return;

    setShowMetadataForm(false);
    setIsUploading(true);
    await uploadFile(currentFile, metadata);
    setIsUploading(false);
    setCurrentFile(null);
    setMetadata({
      caseName: '',
      court: '',
      year: new Date().getFullYear().toString(),
      legalArea: '',
      citation: ''
    });
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxSize: 10 * 1024 * 1024,
    disabled: isUploading || showMetadataForm
  });

  const deleteDocument = (id: string) => {
    setDocuments(prev => prev.filter(doc => doc.id !== id));
    toast.success('Document removed');
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'indexed':
        return <CheckCircle className="w-5 h-5 text-legal-maroon" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <div className="w-5 h-5 border-2 border-legal-maroon border-t-transparent rounded-full animate-spin" />;
    }
  };

  const getCourtBadge = (court?: string) => {
    if (!court) return null;
    const badgeClass = court.includes('Supreme') ? 'court-badge supreme' :
                       court.includes('Appeal') ? 'court-badge appeal' :
                       'court-badge high';
    return <span className={badgeClass}>{court}</span>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-legal-maroon flex items-center justify-center shadow-legal">
            <BookOpen className="w-6 h-6 text-legal-gold" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-legal-text">
              Case & Statute Uploads
            </h1>
            <p className="text-legal-text-muted">
              Upload judgments for AI indexing
            </p>
          </div>
        </div>
        <div className="text-sm text-legal-text-muted bg-legal-gold-light px-4 py-2 rounded-lg border border-legal-gold/30">
          <span className="font-semibold text-legal-gold-dark">{documents.length}</span> documents uploaded
        </div>
      </div>

      {/* Metadata Form Modal */}
      {showMetadataForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-legal-maroon-light flex items-center justify-center">
                <Scale className="w-5 h-5 text-legal-maroon" />
              </div>
              <div>
                <h3 className="text-lg font-serif font-semibold text-legal-text">Document Metadata</h3>
                <p className="text-sm text-legal-text-muted">Add details for: {currentFile?.name}</p>
              </div>
            </div>

            <form onSubmit={handleMetadataSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-legal-text mb-1">Case Name / Title</label>
                <input
                  type="text"
                  value={metadata.caseName}
                  onChange={(e) => setMetadata(m => ({ ...m, caseName: e.target.value }))}
                  placeholder="e.g., Republic v. John Kamau"
                  className="w-full px-3 py-2 border border-legal-maroon/20 rounded-lg focus:ring-2 focus:ring-legal-maroon focus:border-transparent"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-legal-text mb-1">Court</label>
                  <select
                    value={metadata.court}
                    onChange={(e) => setMetadata(m => ({ ...m, court: e.target.value }))}
                    className="w-full px-3 py-2 border border-legal-maroon/20 rounded-lg focus:ring-2 focus:ring-legal-maroon focus:border-transparent"
                  >
                    <option value="">Select Court</option>
                    {COURTS.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-legal-text mb-1">Year</label>
                  <input
                    type="text"
                    value={metadata.year}
                    onChange={(e) => setMetadata(m => ({ ...m, year: e.target.value }))}
                    placeholder="2026"
                    className="w-full px-3 py-2 border border-legal-maroon/20 rounded-lg focus:ring-2 focus:ring-legal-maroon focus:border-transparent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-legal-text mb-1">Legal Area</label>
                  <select
                    value={metadata.legalArea}
                    onChange={(e) => setMetadata(m => ({ ...m, legalArea: e.target.value }))}
                    className="w-full px-3 py-2 border border-legal-maroon/20 rounded-lg focus:ring-2 focus:ring-legal-maroon focus:border-transparent"
                  >
                    <option value="">Select Area</option>
                    {LEGAL_AREAS.map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-legal-text mb-1">Citation (Optional)</label>
                  <input
                    type="text"
                    value={metadata.citation}
                    onChange={(e) => setMetadata(m => ({ ...m, citation: e.target.value }))}
                    placeholder="[2026] eKLR 1234"
                    className="w-full px-3 py-2 border border-legal-maroon/20 rounded-lg focus:ring-2 focus:ring-legal-maroon focus:border-transparent"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowMetadataForm(false);
                    setCurrentFile(null);
                  }}
                  className="flex-1 px-4 py-2.5 border border-legal-maroon/20 text-legal-text-muted rounded-lg hover:bg-legal-maroon-light transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2.5 btn-legal rounded-lg"
                >
                  Upload & Index
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Upload Area */}
      <div className="legal-card p-6">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
            isDragActive
              ? 'border-legal-maroon bg-legal-maroon-light'
              : 'border-legal-maroon/30 hover:border-legal-maroon hover:bg-legal-maroon-light/50'
          } ${isUploading || showMetadataForm ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} />
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-legal-maroon-light flex items-center justify-center">
            <Upload className="w-8 h-8 text-legal-maroon" />
          </div>
          <h3 className="text-lg font-serif font-semibold text-legal-text mb-2">
            {isDragActive ? 'Drop judgment here' : 'Upload Legal Documents'}
          </h3>
          <p className="text-legal-text-muted mb-4">
            Drag and drop judgments, rulings, or statutes here
          </p>
          <p className="text-sm text-legal-text-muted">
            Supports PDF, TXT, DOC, DOCX (max 10MB each)
          </p>
        </div>
      </div>

      {/* Documents List */}
      <div className="legal-card">
        <div className="px-6 py-4 border-b border-legal-maroon/10 flex items-center gap-3">
          <Gavel className="w-5 h-5 text-legal-gold" />
          <div>
            <h2 className="text-lg font-serif font-semibold text-legal-text">
              Indexed Documents
            </h2>
            <p className="text-sm text-legal-text-muted">Hati Zilizopakiwa</p>
          </div>
        </div>

        {documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-16 h-16 text-legal-maroon/30 mx-auto mb-4" />
            <p className="text-legal-text font-medium">No documents uploaded yet</p>
            <p className="text-sm text-legal-text-muted">Upload your first judgment to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-legal-maroon/10">
            {documents.map((doc) => (
              <div key={doc.id} className="p-6 hover:bg-legal-maroon-light/30 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start space-x-4 flex-1 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-legal-gold-light flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-legal-gold-dark" />
                    </div>
                    <div className="min-w-0 flex-1">
                      {doc.caseName ? (
                        <>
                          <h3 className="font-serif font-semibold text-legal-text truncate">{doc.caseName}</h3>
                          <p className="text-sm text-legal-text-muted truncate">{doc.filename}</p>
                        </>
                      ) : (
                        <h3 className="font-medium text-legal-text truncate">{doc.filename}</h3>
                      )}
                      
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        {getCourtBadge(doc.court)}
                        {doc.citation && (
                          <span className="text-xs font-mono text-legal-maroon bg-legal-maroon-light px-2 py-0.5 rounded">
                            {doc.citation}
                          </span>
                        )}
                        {doc.legalArea && (
                          <span className="text-xs text-legal-gold-dark bg-legal-gold-light px-2 py-0.5 rounded">
                            {doc.legalArea}
                          </span>
                        )}
                        {doc.year && (
                          <span className="text-xs text-legal-text-muted">{doc.year}</span>
                        )}
                      </div>

                      <div className="flex items-center space-x-3 text-xs text-legal-text-muted mt-2">
                        <span>{formatFileSize(doc.size)}</span>
                        <span>•</span>
                        <span>{doc.uploadedAt.toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 flex-shrink-0">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(doc.status)}
                      <span className={`text-sm font-medium ${
                        doc.status === 'indexed' ? 'text-legal-maroon' :
                        doc.status === 'error' ? 'text-red-600' :
                        'text-legal-gold-dark'
                      }`}>
                        {doc.status === 'indexed' ? 'Indexed' :
                         doc.status === 'error' ? 'Error' : 'Processing...'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => {/* View document */}}
                        className="p-2 text-legal-text-muted hover:text-legal-maroon transition-colors rounded-lg hover:bg-legal-maroon-light"
                        title="View document"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {/* Download document */}}
                        className="p-2 text-legal-text-muted hover:text-legal-gold-dark transition-colors rounded-lg hover:bg-legal-gold-light"
                        title="Download document"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deleteDocument(doc.id)}
                        className="p-2 text-legal-text-muted hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
                        title="Delete document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="bg-legal-gold-light border border-legal-gold/30 rounded-xl p-6">
        <div className="flex items-start gap-3">
          <Scale className="w-5 h-5 text-legal-gold-dark flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-serif font-semibold text-legal-text mb-2">
              Document Processing Guidelines
            </h3>
            <ul className="text-sm text-legal-text-muted space-y-1">
              <li>• Judgments are automatically indexed for AI-powered legal research</li>
              <li>• Add metadata (case name, court, year) for better searchability</li>
              <li>• Supported formats: PDF, TXT, DOC, DOCX (max 10MB per document)</li>
              <li>• Indexed documents can be queried in the Ask Legal AI section</li>
              <li>• Documents are processed securely and stored confidentially</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Uploads;
