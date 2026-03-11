"use client";

import { useEffect, useState, useCallback } from "react";
import { Upload, Link, Trash2, FileText, Globe, CheckCircle, AlertCircle, Loader2, Search } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { PageLoader } from "@/components/ui/Loader";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { KnowledgeDocument } from "@/types";

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [addingUrl, setAddingUrl] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [searching, setSearching] = useState(false);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    loadDocs();
  }, []);

  async function loadDocs() {
    setLoading(true);
    try {
      const res = await api.listDocuments();
      setDocs(res.data || []);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await api.uploadDocument(file);
      }
      await loadDocs();
    } finally {
      setUploading(false);
    }
  }

  async function handleAddUrl() {
    if (!urlInput.trim()) return;
    setAddingUrl(true);
    try {
      await api.addUrl(urlInput.trim());
      setUrlInput("");
      await loadDocs();
    } finally {
      setAddingUrl(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this document?")) return;
    await api.deleteDocument(id);
    await loadDocs();
  }

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await api.searchKnowledgeBase(searchQuery);
      setSearchResults(res.results || []);
    } finally {
      setSearching(false);
    }
  }

  const statusBadge = (status: string) => {
    if (status === "ready") return <Badge variant="success">Ready</Badge>;
    if (status === "error") return <Badge variant="error">Error</Badge>;
    return <Badge variant="info">Processing</Badge>;
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFileUpload(e.dataTransfer.files);
  }, []);

  if (loading) {
    return (
      <>
        <Header title="Knowledge Base" />
        <PageLoader />
      </>
    );
  }

  return (
    <>
      <Header
        title="Knowledge Base"
        subtitle="Upload documents for your AI agents to reference"
      />
      <div className="flex-1 p-6 space-y-6">
        {/* Upload Zone */}
        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            dragging ? "border-accent bg-accent/5" : "border-gray-200 bg-white"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <Upload className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-600 font-medium">Drag & drop files here</p>
          <p className="text-gray-400 text-sm mt-1">PDF, TXT, DOCX supported</p>
          <label className="mt-4 inline-block">
            <input
              type="file"
              accept=".pdf,.txt,.docx"
              multiple
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
              disabled={uploading}
            />
            <Button size="sm" loading={uploading} className="cursor-pointer">
              {uploading ? "Uploading..." : "Browse Files"}
            </Button>
          </label>
        </div>

        {/* URL Input */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
            <Globe className="w-4 h-4 text-accent" />
            Add URL
          </p>
          <div className="flex gap-2">
            <Input
              placeholder="https://yourcompany.com/faq"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="flex-1"
              onKeyDown={(e) => e.key === "Enter" && handleAddUrl()}
            />
            <Button size="sm" onClick={handleAddUrl} loading={addingUrl}>
              <Link className="w-4 h-4" />
              Add URL
            </Button>
          </div>
        </div>

        {/* Search Preview */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
            <Search className="w-4 h-4 text-accent" />
            Search Preview
          </p>
          <div className="flex gap-2">
            <Input
              placeholder="Test a question..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1"
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Button variant="secondary" size="sm" onClick={handleSearch} loading={searching}>
              Search
            </Button>
          </div>
          {searchResults.length > 0 && (
            <div className="mt-3 space-y-2">
              {searchResults.map((result, i) => (
                <div key={i} className="text-xs bg-gray-50 rounded-lg p-2.5 text-gray-700">
                  {result}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Documents List */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-50">
            <p className="text-sm font-medium text-gray-700">{docs.length} Documents</p>
          </div>
          {docs.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">
              No documents uploaded yet.
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50"
                >
                  <div className="flex-shrink-0 text-gray-400">
                    {doc.doc_type === "url" ? (
                      <Globe className="w-4 h-4" />
                    ) : (
                      <FileText className="w-4 h-4" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {doc.filename}
                    </p>
                    <p className="text-xs text-gray-400">
                      {formatDate(doc.created_at)} · {doc.chunk_count} chunks
                    </p>
                    {doc.error_message && (
                      <p className="text-xs text-red-600 mt-0.5">{doc.error_message}</p>
                    )}
                  </div>
                  {statusBadge(doc.status)}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(doc.id)}
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
