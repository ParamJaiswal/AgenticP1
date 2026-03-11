"use client";

import { Call } from "@/types";
import { formatDate, formatDuration, sentimentBadge, statusBadge } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

interface CallCardProps {
  call: Call;
  onClick?: () => void;
}

export function CallCard({ call, onClick }: CallCardProps) {
  return (
    <div
      className={cn(
        "bg-white rounded-xl border border-gray-100 p-4 space-y-3",
        onClick && "cursor-pointer hover:border-accent/30 hover:shadow-sm transition-all"
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium text-gray-900 text-sm">
            {call.caller_number || call.called_number || "Unknown"}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">{formatDate(call.created_at)}</p>
        </div>
        <div className="flex gap-1.5 flex-wrap justify-end">
          <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", statusBadge(call.status))}>
            {call.status}
          </span>
          {call.sentiment_label && (
            <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", sentimentBadge(call.sentiment_label))}>
              {call.sentiment_label}
            </span>
          )}
        </div>
      </div>
      <div className="flex gap-4 text-xs text-gray-500">
        <span>⏱ {formatDuration(call.duration_seconds)}</span>
        <span>📞 {call.direction}</span>
        {call.resolution && <span>✓ {call.resolution}</span>}
      </div>
      {call.summary && (
        <p className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2 line-clamp-2">
          {call.summary}
        </p>
      )}
    </div>
  );
}
