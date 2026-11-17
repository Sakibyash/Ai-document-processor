"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiFetch, uploadFile } from "../lib/api";
import { Card, EmptyState, FileIcon, Spinner, StatCard, StatusBadge, TypeBadge } from "../components/ui";

export default function Dashboard() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [semantic, setSemantic] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ done: 0, total: 0 });
  const [uploadResults, setUploadResults] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [showBulk, setShowBulk] = useState(false);
  const [queue, setQueue] = useState([]); // {id, file, status: pending|uploading|done|error, error}
  const fileInput = useRef(null);
  const bulkInput = useRef(null);

  const ACCEPTED = [".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".xlsx", ".xls", ".csv", ".txt", ".md", ".docx"];
  const MAX_MB = 50;

  const loadDocs = useCallback(async (initial = false) => {
    try {
      const data = await apiFetch("/api/documents");
      setDocs(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(String(e));
    } finally {
      if (initial) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocs(true);
    const t = setInterval(() => loadDocs(false), 5000);
    return () => clearInterval(t);
  }, [loadDocs]);

  const addToQueue = (fileList) => {
    const incoming = Array.from(fileList || []);
    const items = incoming.map((file) => {
      const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
      let err = null;
      if (!ACCEPTED.includes(ext)) err = `Unsupported type ${ext}`;
      else if (file.size > MAX_MB * 1024 * 1024) err = `Exceeds ${MAX_MB} MB`;
      else if (file.size === 0) err = "Empty file";
      return { id: `${file.name}-${file.size}-${Math.random().toString(36).slice(2, 7)}`, file, status: err ? "error" : "pending", error: err };
    });
    setQueue((q) => {
      const existing = new Set(q.map((i) => `${i.file.name}-${i.file.size}`));
      return [...q, ...items.filter((i) => !existing.has(`${i.file.name}-${i.file.size}`))];
    });
  };

  const removeFromQueue = (id) => setQueue((q) => q.filter((i) => i.id !== id));

  const uploadQueue = async () => {
    const pending = queue.filter((i) => i.status === "pending" || i.status === "error");
    if (!pending.length) return;
    setUploading(true);
    setError("");
    setUploadResults(null);
    // mark all as uploading, then process in batches of 4
    setQueue((q) => q.map((i) => (pending.some((p) => p.id === i.id) ? { ...i, status: "uploading", error: null } : i)));
    const ok = [];
    const failed = [];
    for (let i = 0; i < pending.length; i += 4) {
      const batch = pending.slice(i, i + 4);
      await Promise.all(
        batch.map(async (item) => {
          try {
            await uploadFile(item.file);
            ok.push(item.file.name);
            setQueue((q) => q.map((x) => (x.id === item.id ? { ...x, status: "done" } : x)));
          } catch (e) {
            failed.push(`${item.file.name}: ${e.message}`);
            setQueue((q) => q.map((x) => (x.id === item.id ? { ...x, status: "error", error: e.message } : x)));
          }
        })
      );
      setUploadProgress({ done: Math.min(i + batch.length, pending.length), total: pending.length });
    }
    setUploadResults({ ok: ok.length, failed });
    setUploading(false);
    loadDocs();
  };

  const clearQueue = () => { setQueue([]); setUploadResults(null); };

  const onFiles = async (fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    setUploading(true);
    setError("");
    setUploadResults(null);
    setUploadProgress({ done: 0, total: files.length });
    const ok = [];
    const failed = [];
    // Upload in batches of 4 to balance speed and server load
    for (let i = 0; i < files.length; i += 4) {
      const batch = files.slice(i, i + 4);
      await Promise.all(
        batch.map(async (file) => {
          try {
            await uploadFile(file);
            ok.push(file.name);
          } catch (e) {
            failed.push(`${file.name}: ${e.message}`);
          }
        })
      );
      setUploadProgress({ done: Math.min(i + batch.length, files.length), total: files.length });
    }
    setUploadResults({ ok: ok.length, failed });
    setUploading(false);
    if (fileInput.current) fileInput.current.value = "";
    loadDocs();
  };

  const runSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return loadDocs();
    try {
      const endpoint = semantic ? "/api/search/semantic" : "/api/search";
      const data = await apiFetch(`${endpoint}?q=${encodeURIComponent(query)}`);
      setDocs(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(String(e));
    }
  };

  const stats = {
    total: docs.length,
    completed: docs.filter((d) => d.status === "completed").length,
    processing: docs.filter((d) => d.status === "processing" || d.status === "uploaded").length,
    failed: docs.filter((d) => d.status === "failed").length,
    withInvoice: docs.filter((d) => d.invoice).length,
  };
  const visible = statusFilter ? docs.filter((d) => d.status === statusFilter) : docs;

  return (
    <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">DocIntel</h1>
          <p className="text-gray-500 mt-1">AI-powered document intelligence for invoices & receipts</p>
        </div>
        <form onSubmit={runSearch} className="flex gap-2 items-center">
          <div className="relative">
            <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search documents..."
              className="border border-gray-200 rounded-xl pl-9 pr-3 py-2.5 w-80 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <label className="flex items-center gap-1.5 text-sm text-gray-600 bg-white border border-gray-200 rounded-xl px-3 py-2.5 cursor-pointer hover:border-gray-300">
            <input type="checkbox" checked={semantic} onChange={(e) => setSemantic(e.target.checked)} className="accent-indigo-600" />
            Semantic
          </label>
          <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors">
            Search
          </button>
          <button
            onClick={() => setShowBulk(true)}
            className="inline-flex items-center gap-2 border border-indigo-200 text-indigo-700 hover:bg-indigo-50 px-5 py-2.5 rounded-xl font-medium transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            Bulk Upload
          </button>
        </form>
      </header>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">{error}</div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Total documents" value={stats.total} accent="bg-gray-100 text-gray-600"
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" /></svg>} />
        <StatCard label="Completed" value={stats.completed} accent="bg-emerald-100 text-emerald-600"
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} />
        <StatCard label="Processing" value={stats.processing} accent="bg-blue-100 text-blue-600"
          icon={<Spinner className="w-5 h-5" />} />
        <StatCard label="Failed" value={stats.failed} accent="bg-red-100 text-red-600"
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>} />
        <StatCard label="Extracted" value={stats.withInvoice} accent="bg-indigo-100 text-indigo-600"
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>} />
      </div>

      {/* Upload dropzone */}
      <div
        onClick={() => fileInput.current.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          onFiles(e.dataTransfer.files);
        }}
        className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
          dragging ? "border-indigo-500 bg-indigo-50" : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"
        }`}
      >
        {uploading ? (
          <div className="space-y-3">
            <div className="flex items-center justify-center gap-3 text-indigo-600">
              <Spinner className="w-5 h-5" />
              Uploading {uploadProgress.done}/{uploadProgress.total} files...
            </div>
            <div className="max-w-xs mx-auto h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress.total ? (uploadProgress.done / uploadProgress.total) * 100 : 0}%` }}
              />
            </div>
          </div>
        ) : (
          <>
            <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-indigo-100 text-indigo-600 flex items-center justify-center">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <p className="font-medium text-gray-700">Drop documents here or click to upload</p>
            <p className="text-sm text-gray-400 mt-1">Multiple files supported — PDF · Images · XLSX/XLS/CSV · TXT/MD · DOCX — up to 50 MB each</p>
          </>
        )}
        <input
          ref={fileInput}
          type="file"
          multiple
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff,.bmp,.webp,.xlsx,.xls,.csv,.txt,.md,.docx"
          onChange={(e) => onFiles(e.target.files)}
        />
      </div>

      {/* Upload results */}
      {uploadResults && (
        <div className={`p-4 rounded-xl text-sm border ${
          uploadResults.failed.length
            ? "bg-amber-50 border-amber-200 text-amber-800"
            : "bg-emerald-50 border-emerald-200 text-emerald-700"
        }`}>
          <span className="font-semibold">{uploadResults.ok} file{uploadResults.ok === 1 ? "" : "s"} uploaded</span>
          {uploadResults.failed.length > 0 && (
            <ul className="mt-2 space-y-1">
              {uploadResults.failed.map((f, i) => <li key={i}>• {f}</li>)}
            </ul>
          )}
        </div>
      )}

      {/* Bulk upload modal */}
      {showBulk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={() => !uploading && setShowBulk(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div>
                <h2 className="font-semibold text-gray-900">Bulk upload</h2>
                <p className="text-xs text-gray-400 mt-0.5">PDF · Images · Excel/CSV · TXT/MD · DOCX — up to {MAX_MB} MB each</p>
              </div>
              <button onClick={() => !uploading && setShowBulk(false)} className="text-gray-400 hover:text-gray-600 p-1">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              {/* Drop area inside modal */}
              <div
                onClick={() => bulkInput.current.click()}
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => { e.preventDefault(); setDragging(false); addToQueue(e.dataTransfer.files); }}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                  dragging ? "border-indigo-500 bg-indigo-50" : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"
                }`}
              >
                <p className="text-sm font-medium text-gray-600">Drop files here or click to browse</p>
                <p className="text-xs text-gray-400 mt-1">Select multiple files at once — mixed formats are fine</p>
                <input
                  ref={bulkInput}
                  type="file"
                  multiple
                  className="hidden"
                  accept={ACCEPTED.join(",")}
                  onChange={(e) => { addToQueue(e.target.files); e.target.value = ""; }}
                />
              </div>

              {/* Queue list */}
              {queue.length > 0 && (
                <div className="border border-gray-100 rounded-xl overflow-hidden">
                  <div className="max-h-64 overflow-y-auto divide-y divide-gray-50">
                    {queue.map((item) => (
                      <div key={item.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                        <FileIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <span className="flex-1 truncate text-gray-700">{item.file.name}</span>
                        <span className="text-xs text-gray-400">{(item.file.size / 1024).toFixed(0)} KB</span>
                        {item.status === "pending" && <span className="text-xs text-gray-400">Ready</span>}
                        {item.status === "uploading" && <Spinner className="w-4 h-4 text-indigo-500" />}
                        {item.status === "done" && <span className="text-xs font-medium text-emerald-600">Uploaded</span>}
                        {item.status === "error" && <span className="text-xs font-medium text-red-500" title={item.error}>Failed</span>}
                        {item.status !== "uploading" && item.status !== "done" && (
                          <button onClick={() => removeFromQueue(item.id)} className="text-gray-300 hover:text-red-500">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {queue.length === 0 && !uploadResults && (
                <div className="text-center text-sm text-gray-400 py-6">No files selected yet</div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
              <div className="text-sm text-gray-500">
                {queue.filter((i) => i.status === "pending").length} ready · {queue.filter((i) => i.status === "done").length} uploaded
                {uploadResults?.failed.length > 0 && <span className="text-red-500"> · {uploadResults.failed.length} failed</span>}
              </div>
              <div className="flex gap-2">
                <button onClick={clearQueue} disabled={uploading || queue.length === 0} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl disabled:opacity-40">
                  Clear
                </button>
                <button
                  onClick={uploadQueue}
                  disabled={uploading || !queue.some((i) => i.status === "pending" || i.status === "error")}
                  className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
                >
                  {uploading && <Spinner className="w-4 h-4" />}
                  Upload {queue.filter((i) => i.status === "pending" || i.status === "error").length || ""} file{queue.filter((i) => i.status === "pending" || i.status === "error").length === 1 ? "" : "s"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Documents table */}
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Documents</h2>
          <div className="flex gap-1.5">
            {["", "uploaded", "processing", "completed", "failed"].map((s) => (
              <button
                key={s || "all"}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  statusFilter === s ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {s ? s.charAt(0).toUpperCase() + s.slice(1) : "All"}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="p-10 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded-xl animate-pulse-soft" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <EmptyState title="No documents yet" hint="Upload your first document above to get started" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 uppercase tracking-wider border-b border-gray-100">
                  <th className="px-5 py-3 font-medium">File</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium">Invoice #</th>
                  <th className="px-5 py-3 font-medium">Supplier / Merchant</th>
                  <th className="px-5 py-3 font-medium text-right">Total</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {visible.map((d) => {
                  const inv = d.invoice;
                  return (
                    <tr key={d.id} className="hover:bg-gray-50/80 transition-colors group">
                      <td className="px-5 py-3.5">
                        <Link href={`/documents/${d.id}`} className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-gray-100 text-gray-500 flex items-center justify-center group-hover:bg-indigo-100 group-hover:text-indigo-600 transition-colors">
                            <FileIcon className="w-4 h-4" />
                          </div>
                          <span className="font-medium text-gray-800 group-hover:text-indigo-600 transition-colors max-w-[220px] truncate">
                            {d.filename}
                          </span>
                        </Link>
                      </td>
                      <td className="px-5 py-3.5"><TypeBadge type={inv?.document_type} /></td>
                      <td className="px-5 py-3.5 text-gray-600">{inv?.invoice_number || "—"}</td>
                      <td className="px-5 py-3.5 text-gray-600 max-w-[200px] truncate">
                        {inv?.supplier_name || inv?.merchant_name || "—"}
                      </td>
                      <td className="px-5 py-3.5 text-right font-medium text-gray-800">
                        {inv?.total != null ? `${inv.currency || ""} ${Number(inv.total).toLocaleString()}`.trim() : "—"}
                      </td>
                      <td className="px-5 py-3.5"><StatusBadge status={d.status} /></td>
                      <td className="px-5 py-3.5 text-gray-400 text-xs">
                        {d.created_at ? new Date(d.created_at).toLocaleString() : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </main>
  );
}
