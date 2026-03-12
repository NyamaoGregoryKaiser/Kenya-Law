import React, { useState, useCallback } from 'react';
import { FileText, Trash2, Eye, Download, CheckCircle, AlertCircle, Scale, BookOpen, Gavel } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import { API_BASE } from '../utils/api';

interface UploadedDocument {
  id: string;
  filename: string;
  size: number;
  type: string;
  status: 'uploading' | 'indexed' | 'uploaded' | 'error';
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
  const [loadingList, setLoadingList] = useState(true);
  const [showAllDocuments, setShowAllDocuments] = useState(false);
  const [totalIndexed, setTotalIndexed] = useState(0);
  const [totalUploaded, setTotalUploaded] = useState(0);
  const RECENT_LIMIT = 10;

  const fetchDocuments = useCallback(async (opts?: { showAll?: boolean }) => {
    try {
      const showAll = Boolean(opts?.showAll);
      const limitParam = showAll ? '0' : '50';
      const res = await axios.get(`${API_BASE}/documents?limit=${limitParam}`);
      const documents = res.data?.documents || [];
      setTotalIndexed(Number(res.data?.total_indexed ?? 0));
      setTotalUploaded(Number(res.data?.total_uploaded ?? 0));
      console.log(`Fetched ${documents.length} documents from API`);
      const list = documents.map((d: { filename: string; size: number; uploaded_at: string; indexed: boolean; indexed_at?: string | null }) => ({
        id: d.filename,
        filename: d.filename,
        size: d.size,
        type: '',
        status: d.indexed ? 'indexed' as const : 'uploaded' as const,
        uploadedAt: new Date(d.uploaded_at),
        indexedAt: d.indexed_at ? new Date(d.indexed_at) : undefined,
      }));
      console.log(`Mapped ${list.length} documents, setting state`);
      setDocuments(list);
    } catch (error: any) {
      console.error('Error fetching documents:', error);
      toast.error('Failed to load documents. Please refresh the page.');
      // Don't clear documents on error - keep existing ones
    } finally {
      setLoadingList(false);
    }
  }, []);

  React.useEffect(() => {
    fetchDocuments({ showAll: false });
  }, [fetchDocuments]);

  const uploadFile = async (file: File) => {
    const document: UploadedDocument = {
      id: Date.now().toString() + Math.random(),
      filename: file.name,
      size: file.size,
      type: file.type,
      status: 'uploading',
      uploadedAt: new Date(),
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
                status: response.data.indexed ? 'indexed' : 'uploaded',
                indexedAt: response.data.indexed ? new Date() : undefined
              }
            : doc
        )
      );

      if (response.data.indexed) {
        toast.success(`${file.name} uploaded and indexed for AI search`);
      } else {
        const msg = response.data.index_message || 'Indexing unavailable. Check backend logs.';
        toast.success(`${file.name} uploaded. ${msg}`, { duration: 6000 });
      }
      
      // Refresh document list to ensure accurate status from backend
      await fetchDocuments({ showAll: showAllDocuments });
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    setIsUploading(true);
    try {
      for (const f of files) {
        // sequential upload to avoid overloading the backend
        // eslint-disable-next-line no-await-in-loop
        await uploadFile(f);
      }
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const deleteDocument = async (id: string) => {
    try {
      // id is the filename - encode it properly for URL
      const encodedFilename = encodeURIComponent(id);
      const deleteUrl = `${API_BASE}/documents/${encodedFilename}`;
      console.log(`Deleting document: ${id}`);
      console.log(`Encoded filename: ${encodedFilename}`);
      console.log(`Delete URL: ${deleteUrl}`);
      console.log(`API_BASE: ${API_BASE}`);
      
      const response = await axios.delete(deleteUrl);
      console.log('Delete response status:', response.status);
      console.log('Delete response data:', response.data);
      
      if (response.status === 200 || response.status === 204) {
        // Only remove from state if delete was successful
        setDocuments(prev => prev.filter(doc => doc.id !== id));
        toast.success('Document deleted successfully');
        
        // Refresh the list to ensure consistency
        await fetchDocuments({ showAll: showAllDocuments });
      } else {
        throw new Error(`Unexpected status code: ${response.status}`);
      }
    } catch (error: any) {
      console.error('Delete error details:', {
        message: error.message,
        response: error.response,
        status: error.response?.status,
        data: error.response?.data,
        url: error.config?.url
      });
      const errorMessage = error.response?.data?.detail || error.response?.statusText || error.message || 'Failed to delete document';
      toast.error(`Delete failed: ${errorMessage}`);
      // Don't remove from state if delete failed
    }
  };

  const viewDocument = (doc: UploadedDocument) => {
    // Open the backend download URL in a new tab; browser will preview if possible
    const encoded = encodeURIComponent(doc.filename);
    const url = `${API_BASE.replace(/\/+$/, '')}/documents/${encoded}/download`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const downloadDocument = (doc: UploadedDocument) => {
    const encoded = encodeURIComponent(doc.filename);
    const url = `${API_BASE.replace(/\/+$/, '')}/documents/${encoded}/download`;
    // Creating an anchor ensures "Save as" in some browsers
    const a = document.createElement('a');
    a.href = url;
    a.download = doc.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
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
      case 'uploaded':
        return <FileText className="w-5 h-5 text-legal-gold-dark" />;
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

  const recentFiles = [...documents]
    .filter((d) => d.status === 'indexed')
    .sort((a, b) => (new Date(b.indexedAt || b.uploadedAt).getTime() - new Date(a.indexedAt || a.uploadedAt).getTime()))
    .slice(0, showAllDocuments ? undefined : RECENT_LIMIT);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold">Case & Statute Uploads</h2>
          <p className="text-sm text-gray-500">Upload judgments for AI indexing</p>
          <p className="text-sm text-gray-500 mt-1">
            <span className="font-semibold">{totalIndexed}</span> indexed documents (of {totalUploaded} uploaded)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={async () => {
              setLoadingList(true);
              const next = !showAllDocuments;
              setShowAllDocuments(next);
              await fetchDocuments({ showAll: next });
            }}
            className="px-4 py-2 rounded-lg border border-legal-border bg-legal-white text-legal-text hover:bg-legal-bg transition-colors text-sm font-medium"
            disabled={loadingList || isUploading}
          >
            {showAllDocuments ? 'Show recent only' : 'View all documents'}
          </button>

          <button
            onClick={() => document.getElementById("fileInput")?.click()}
            className="px-4 py-2 rounded-lg bg-[#8B1E3F] text-white hover:opacity-90"
            disabled={isUploading}
          >
            + Add Document
          </button>

          <input
            id="fileInput"
            type="file"
            accept=".pdf,.txt,.doc,.docx"
            multiple
            className="hidden"
            onChange={handleFileUpload}
          />
        </div>
      </div>

      {/* Drag-and-drop + metadata modal removed by request */}

      {/* Documents List */}
      <div className="legal-card">
        <div className="px-6 py-4 border-b border-legal-maroon/10 flex items-center gap-3">
          <Gavel className="w-5 h-5 text-legal-gold" />
          <div>
            <h2 className="text-lg font-serif font-semibold text-legal-text">
              Recently Indexed Files
            </h2>
            <p className="text-sm text-legal-text-muted">Latest indexed documents</p>
          </div>
        </div>

        {loadingList ? (
          <div className="p-12 text-center">
            <div className="w-10 h-10 border-2 border-legal-maroon border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-legal-text-muted">Loading documents...</p>
          </div>
        ) : recentFiles.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-16 h-16 text-legal-maroon/30 mx-auto mb-4" />
            <p className="text-legal-text font-medium">No indexed documents yet</p>
            <p className="text-sm text-legal-text-muted">Upload documents to begin indexing</p>
          </div>
        ) : (
          <div className="divide-y divide-legal-maroon/10">
            {recentFiles.map((doc) => (
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
                        <span>{(doc.indexedAt || doc.uploadedAt).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 flex-shrink-0">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon('indexed')}
                      <span className="text-sm font-medium text-legal-maroon">Indexed</span>
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => viewDocument(doc)}
                        className="p-2 text-legal-text-muted hover:text-legal-maroon transition-colors rounded-lg hover:bg-legal-maroon-light"
                        title="View document"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => downloadDocument(doc)}
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
        <div className="flex items-center gap-3">
          <button
            onClick={async () => {
              setLoadingList(true);
              const next = !showAllDocuments;
              setShowAllDocuments(next);
              await fetchDocuments({ showAll: next });
            }}
            className="px-4 py-2 rounded-lg border border-legal-border bg-legal-white text-legal-text hover:bg-legal-bg transition-colors text-sm font-medium"
            disabled={loadingList}
          >
            {showAllDocuments ? 'Show recent only' : 'View all documents'}
          </button>
        </div>
      </div>

      {/* Full-screen overlay while uploading/indexing */}
      {isUploading && (
        <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-2xl px-6 py-5 flex items-center gap-4 max-w-md w-[90%]">
            <div className="w-8 h-8 border-2 border-legal-maroon border-t-transparent rounded-full animate-spin" />
            <div>
              <p className="font-semibold text-legal-text">
                Uploading and indexing document…
              </p>
              <p className="text-sm text-legal-text-muted">
                This may take a moment while we process your judgment and add it to the AI index.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Uploads;
