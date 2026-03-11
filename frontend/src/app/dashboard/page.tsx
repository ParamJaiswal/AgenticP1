"use client";

import { useEffect, useState } from "react";
import { Phone, Activity, Clock, CheckCircle, TrendingUp, Plus } from "lucide-react";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { CallCard } from "@/components/dashboard/CallCard";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { PageLoader } from "@/components/ui/Loader";
import { api } from "@/lib/api";
import { formatDuration } from "@/lib/utils";
import type { DashboardStats, Call } from "@/types";
import Link from "next/link";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentCalls, setRecentCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [statsData, callsData] = await Promise.all([
          api.getDashboardStats(),
          api.listCalls({ limit: 5 }),
        ]);
        setStats(statsData);
        setRecentCalls(callsData.data || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <>
        <Header title="Dashboard" />
        <PageLoader />
      </>
    );
  }

  return (
    <>
      <Header
        title="Dashboard"
        subtitle="Real-time overview of your AI calling agents"
      />
      <div className="flex-1 p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Calls Today"
            value={stats?.calls_today ?? 0}
            icon={Phone}
            iconColor="text-accent"
          />
          <StatsCard
            title="Active Calls"
            value={stats?.active_calls ?? 0}
            subtitle="Currently in progress"
            icon={Activity}
            iconColor="text-green-600"
          />
          <StatsCard
            title="Avg Duration"
            value={formatDuration(stats?.avg_duration_seconds)}
            subtitle="This month"
            icon={Clock}
            iconColor="text-blue-600"
          />
          <StatsCard
            title="Resolution Rate"
            value={`${stats?.resolution_rate_percent ?? 0}%`}
            subtitle="Issues resolved by AI"
            icon={CheckCircle}
            iconColor="text-emerald-600"
          />
        </div>

        {/* Quick Actions */}
        <div className="flex gap-3">
          <Link href="/dashboard/calls">
            <Button variant="secondary" size="sm">
              <Phone className="w-4 h-4" />
              View All Calls
            </Button>
          </Link>
          <Link href="/dashboard/agents">
            <Button size="sm">
              <Plus className="w-4 h-4" />
              Configure Agent
            </Button>
          </Link>
          <Link href="/dashboard/analytics">
            <Button variant="secondary" size="sm">
              <TrendingUp className="w-4 h-4" />
              View Analytics
            </Button>
          </Link>
        </div>

        {/* Recent Calls */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900">Recent Calls</h2>
            <Link href="/dashboard/calls" className="text-sm text-accent hover:underline">
              View all →
            </Link>
          </div>
          {recentCalls.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 p-8 text-center">
              <Phone className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No calls yet.</p>
              <p className="text-gray-400 text-xs mt-1">
                Configure an agent and connect a phone number to get started.
              </p>
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {recentCalls.map((call) => (
                <CallCard key={call.id} call={call} />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
