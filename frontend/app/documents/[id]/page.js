"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiFetch } from "../../../lib/api";
import { Card, Spinner, StatusBadge, TypeBadge } from "../../../components/ui";

const FIELDS = [
  ["document_type", "Document Type", "select"],
  ["invoice_number", "Invoice #", "text"],
  ["invoice_date", "Invoice Date", "text"],
  ["supplier_name", "Supplier", "text"],
  ["customer_name", "Customer", "text"],
  ["merchant_name", "Merchant", "text"],
  ["transaction_date", "Transaction Date", "text"],
  ["payment_method", "Payment Method", "text"],
  ["currency", "Currency", "text"],
  ["subtotal", "Subtotal", "number"],
  ["tax", "Tax", "number"],
  ["total", "Total", "number"],
];
const DOC_TYPES = ["invoice", "receipt", "statement", "unknown"];

export default function DocumentPage() {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [allDocs, setAllDocs] = useState([]);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [msg, setMsg] = useState("");
  const [verifyTarget, setVerifyTarget] = useState("");
  const [verifyResult, setVerifyResult] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/documents/${id}`);
      setDoc(data);
      setForm(data.invoice || {});
    } catch (e) {
      setError(String(e));
    }
  }, [id]);

  useEffect(() => {
    load();
    apiFetch("/api/documents").then((d) => setAllDocs(Array.isArray(d) ? d : [])).catch(() => {});
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  if (error) {
    return (
      <main className="max-w-4xl mx-auto p-8">
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl">{error}</div>
      </main>
    );
  }
  if (!doc) {
    return (
      <main className="max-w-4xl mx-auto p-8 space-y-4">
        <div className="h-8 w-64 bg-gray-100 rounded-lg animate-pulse-soft" />
        <div className="h-64 bg-gray-100 rounded-2xl animate-pulse-soft" />
      </main>
    );
  }

  const inv = doc.invoice;
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value === "" ? null : e.target.value });

  const save = async () => {
    if (!inv) return;
    setSaving(true);
    setMsg("");
    try {
      const payload = {};
      for (const [k] of FIELDS) {
        const v = form[k];
        payload[k] = k === "subtotal" || k === "tax" || k === "total"
          ? (v !== null && v !== "" ? Number(v) : null)
          : v;
      }
      await apiFetch(`/api/invoices/${inv.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      setMsg("Saved and re-validated.");
      load();
    } catch (e) {
      setMsg(`Error: ${e.message}`);
    }
    setSaving(false);
  };

  const reprocess = async () => {
    setReprocessing(true);
    try {
      await apiFetch(`/api/documents/${id}/reprocess`, { method: "POST" });
      load();
    } finally {
      setReprocessing(false);
    }
  };

  const runVerify = async () => {
    if (!verifyTarget) return;
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await apiFetch(`/api/documents/${id}/verify/${verifyTarget}`, { method: "POST" });
      setVerifyResult(res);
    } catch (e) {
      setVerifyResult({ error: String(e) });
    } finally {
      setVerifying(false);
    }
  };

  const unresolvedIssues = (doc.validation_issues || []).filter((i) => !i.resolved);

  return (
    <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link href="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Dashboard
          </Link>
          <div className="flex items-center gap-3 mt-2">
            <h1 className="text-2xl font-bold text-gray-900 truncate max-w-xl">{doc.filename}</h1>
            {inv?.document_type && <TypeBadge type={inv.document_type} />}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={doc.status} />
          <button
            onClick={reprocess}
            disabled={reprocessing}
            className="inline-flex items-center gap-2 text-sm border border-gray-200 rounded-xl px-4 py-2 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {reprocessing && <Spinner />}
            Reprocess
          </button>
        </div>
      </div>

      {doc.error_message && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">{doc.error_message}</div>
      )}

      {/* Validation issues */}
      {unresolvedIssues.length > 0 && (
        <Card className="p-5 border-amber-200 bg-amber-50/50">
          <div className="flex items-center gap-2 mb-3">
            <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            <h2 className="font-semibold text-amber-800">Validation issues ({unresolvedIssues.length})</h2>
          </div>
          <ul className="space-y-1.5 text-sm text-amber-700">
            {unresolvedIssues.map((i) => (
              <li key={i.id} className="flex items-start gap-2">
                <span className={`mt-0.5 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${i.severity === "error" ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600"}`}>
                  {i.severity}
                </span>
                <span>{i.field && <strong>{i.field}: </strong>}{i.message}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {!inv ? (
        <Card className="p-10 text-center text-gray-400">
          {doc.status === "failed" ? "Processing failed — see error above" : "Extraction in progress..."}
        </Card>
      ) : (
        <>
          {/* Extracted data */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-gray-900">Extracted data</h2>
              {inv.corrected_by_user && (
                <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">Corrected by user</span>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {FIELDS.map(([k, label, type]) => (
                <label key={k} className="block">
                  <span className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">{label}</span>
                  {type === "select" ? (
                    <select
                      value={form[k] ?? "unknown"}
                      onChange={set(k)}
                      className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 capitalize"
                    >
                      {DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  ) : (
                    <input
                      type={type === "number" ? "number" : "text"}
                      step="any"
                      value={form[k] ?? ""}
                      onChange={set(k)}
                      className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  )}
                </label>
              ))}
            </div>
            <div className="mt-5 flex items-center gap-3">
              <button
                onClick={save}
                disabled={saving}
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
              >
                {saving && <Spinner />}
                Save corrections
              </button>
              {msg && <span className="text-sm text-gray-500">{msg}</span>}
            </div>
          </Card>

          {/* Line items */}
          {inv.line_items?.length > 0 && (
            <Card className="overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h2 className="font-semibold text-gray-900">Line items <span className="text-gray-400 font-normal">({inv.line_items.length})</span></h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-400 uppercase tracking-wider border-b border-gray-100">
                      <th className="px-6 py-3 font-medium">Description</th>
                      <th className="px-6 py-3 font-medium text-right">Qty</th>
                      <th className="px-6 py-3 font-medium text-right">Unit Price</th>
                      <th className="px-6 py-3 font-medium text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {inv.line_items.map((li) => (
                      <tr key={li.id} className="hover:bg-gray-50/60">
                        <td className="px-6 py-3 text-gray-700">{li.description || "—"}</td>
                        <td className="px-6 py-3 text-right text-gray-600">{li.quantity ?? "—"}</td>
                        <td className="px-6 py-3 text-right text-gray-600">{li.unit_price ?? "—"}</td>
                        <td className="px-6 py-3 text-right font-medium text-gray-800">{li.amount ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}

      {/* Cross-document verification */}
      <Card className="p-6">
        <h2 className="font-semibold text-gray-900 mb-1">Cross-document verification</h2>
        <p className="text-sm text-gray-500 mb-4">
          Compare against another processed document — e.g. PDF invoice vs Excel record.
        </p>
        <div className="flex gap-2">
          <select
            value={verifyTarget}
            onChange={(e) => setVerifyTarget(e.target.value)}
            className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select document to compare...</option>
            {allDocs.filter((d) => d.id !== id && d.invoice).map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename} ({d.invoice.invoice_number || d.invoice.document_type})
              </option>
            ))}
          </select>
          <button
            onClick={runVerify}
            disabled={!verifyTarget || verifying}
            className="inline-flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
          >
            {verifying && <Spinner />}
            Verify
          </button>
        </div>
        {verifyResult && (
          <div className={`mt-4 p-4 rounded-xl text-sm ${
            verifyResult.error
              ? "bg-red-50 border border-red-200 text-red-700"
              : verifyResult.valid
              ? "bg-emerald-50 border border-emerald-200 text-emerald-700"
              : "bg-amber-50 border border-amber-200 text-amber-700"
          }`}>
            {verifyResult.error ? verifyResult.error : (
              <>
                <div className="font-semibold mb-2">
                  {verifyResult.valid ? "Records match" : "Mismatches found — manual review required"}
                </div>
                <ul className="space-y-1">
                  {verifyResult.issues.map((i, idx) => (
                    <li key={idx}>• [{i.severity}] {i.field ? `${i.field}: ` : ""}{i.message}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </Card>

      {/* Extracted text */}
      {doc.extracted_text && (
        <Card className="p-6">
          <details>
            <summary className="font-semibold text-gray-900 cursor-pointer hover:text-indigo-600 transition-colors">
              Extracted text <span className="text-gray-400 font-normal">({doc.extracted_text.length.toLocaleString()} chars)</span>
            </summary>
            <pre className="mt-4 text-xs bg-gray-50 border border-gray-100 p-4 rounded-xl overflow-auto max-h-96 whitespace-pre-wrap text-gray-600">
              {doc.extracted_text}
            </pre>
          </details>
        </Card>
      )}

      {/* Processing history timeline */}
      {doc.history?.length > 0 && (
        <Card className="p-6">
          <details>
            <summary className="font-semibold text-gray-900 cursor-pointer hover:text-indigo-600 transition-colors">
              Processing history <span className="text-gray-400 font-normal">({doc.history.length} events)</span>
            </summary>
            <ul className="mt-4 space-y-3">
              {doc.history.map((h, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${h.status === "completed" ? "bg-emerald-500" : h.status === "failed" ? "bg-red-500" : "bg-blue-400 animate-pulse-soft"}`} />
                  <div>
                    <span className="text-gray-400 text-xs">{new Date(h.created_at).toLocaleString()}</span>
                    <span className="ml-2 font-medium text-gray-700">{h.stage}</span>
                    <span className="ml-2 text-gray-500">{h.status}{h.detail ? ` — ${h.detail}` : ""}</span>
                  </div>
                </li>
              ))}
            </ul>
          </details>
        </Card>
      )}
    </main>
  );
}
