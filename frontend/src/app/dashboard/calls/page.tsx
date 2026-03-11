"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PageLoader } from "@/components/ui/Loader";
import { api } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/utils";
import type { Call, TranscriptTurn } from "@/types";
import { Download } from "lucide-react";

export default function CallsPage() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedCall, setSelectedCall] = useState<Call | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    loadCalls();
  }, []);

  async function loadCalls() {
    setLoading(true);
    try {
      const res = await api.listCalls({ limit: 50 });
      setCalls(res.data || []);
      setTotal(res.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function openCall(call: Call) {
    setLoadingDetail(true);
    setSelectedCall(call);
    try {
      const detail = await api.getCall(call.id);
      setSelectedCall(detail);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDetail(false);
    }
  }

  function exportCSV() {
    const header = "ID,Date,Caller,Duration,Sentiment,Resolution,Status\n";
    const rows = calls
      .map(
        (c) =>
          `${c.id},${c.created_at},${c.caller_number || ""},${c.duration_seconds || 0},${c.sentiment_label || ""},${c.resolution || ""},${c.status}`
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "calls.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const sentimentVariant = (s: string | null) => {
    if (s === "positive") return "success";
    if (s === "negative") return "error";
    return "default";
  };

  const statusVariant = (s: string) => {
    if (s === "completed") return "success";
    if (s === "active") return "info";
    if (s === "failed") return "error";
    return "default";
  };

  return (
    <>
      <Header title="Call History" subtitle={`${total} total calls`} />
      <div className="flex-1 p-6 space-y-4">
        <div className="flex justify-end">
          <Button variant="secondary" size="sm" onClick={exportCSV}>
            <Download className="w-4 h-4" />
            Export CSV
          </Button>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <Table
            loading={loading}
            emptyMessage="No calls found."
            columns={[
              {
                key: "created_at",
                header: "Date",
                render: (v) => <span className="text-xs">{formatDate(v as string)}</span>,
              },
              {
                key: "caller_number",
                header: "Caller",
                render: (v, row) => (v as string) || (row as Call).called_number || "—",
              },
              {
                key: "duration_seconds",
                header: "Duration",
                render: (v) => formatDuration(v as number),
              },
              {
                key: "sentiment_label",
                header: "Sentiment",
                render: (v) =>
                  v ? (
                    <Badge variant={sentimentVariant(v as string)}>
                      {v as string}
                    </Badge>
                  ) : (
                    "—"
                  ),
              },
              {
                key: "resolution",
                header: "Resolution",
                render: (v) => (v as string) || "—",
              },
              {
                key: "status",
                header: "Status",
                render: (v) => (
                  <Badge variant={statusVariant(v as string)}>{v as string}</Badge>
                ),
              },
              {
                key: "id",
                header: "",
                render: (_, row) => (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openCall(row as Call)}
                  >
                    View
                  </Button>
                ),
              },
            ]}
            data={calls as unknown as Record<string, unknown>[]}
          />
        </div>
      </div>

      {/* Call detail modal */}
      <Modal
        open={!!selectedCall}
        onClose={() => setSelectedCall(null)}
        title={`Call — ${formatDate(selectedCall?.created_at)}`}
        className="max-w-2xl"
      >
        {loadingDetail ? (
          <PageLoader />
        ) : selectedCall ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-gray-500 text-xs">Caller</p>
                <p className="font-medium">{selectedCall.caller_number || "—"}</p>
              </div>
              <div>
                <p className="text-gray-500 text-xs">Duration</p>
                <p className="font-medium">{formatDuration(selectedCall.duration_seconds)}</p>
              </div>
              <div>
                <p className="text-gray-500 text-xs">Sentiment</p>
                <p className="font-medium">{selectedCall.sentiment_label || "—"}</p>
              </div>
              <div>
                <p className="text-gray-500 text-xs">Resolution</p>
                <p className="font-medium">{selectedCall.resolution || "—"}</p>
              </div>
            </div>

            {selectedCall.summary && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-1">Summary</p>
                <p className="text-sm bg-gray-50 rounded-lg p-3">{selectedCall.summary}</p>
              </div>
            )}

            {selectedCall.transcript_turns && selectedCall.transcript_turns.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">Transcript</p>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {selectedCall.transcript_turns.map((turn, i) => (
                    <div
                      key={i}
                      className={`flex gap-2 ${turn.role === "user" ? "justify-start" : "justify-end"}`}
                    >
                      <div
                        className={`max-w-xs rounded-xl px-3 py-2 text-sm ${
                          turn.role === "user"
                            ? "bg-gray-100 text-gray-800"
                            : "bg-accent text-white"
                        }`}
                      >
                        <p className="text-xs opacity-60 mb-0.5 capitalize">{turn.role}</p>
                        {turn.content}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </Modal>
    </>
  );
}
