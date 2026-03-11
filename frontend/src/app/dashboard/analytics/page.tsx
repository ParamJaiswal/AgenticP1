"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { CallVolumeChart, SentimentChart } from "@/components/dashboard/AnalyticsChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageLoader } from "@/components/ui/Loader";
import { api } from "@/lib/api";
import { BarChart3, CheckCircle, Clock, TrendingUp } from "lucide-react";
import type { BillingUsage, CallVolumeData, SentimentData } from "@/types";

export default function AnalyticsPage() {
  const [callVolume, setCallVolume] = useState<CallVolumeData[]>([]);
  const [sentiment, setSentiment] = useState<SentimentData>({});
  const [billing, setBilling] = useState<BillingUsage | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [vol, sent, bill] = await Promise.all([
          api.getCallVolume(30),
          api.getSentimentDistribution(),
          api.getBillingUsage(),
        ]);
        setCallVolume(vol.data || []);
        setSentiment(sent.data || {});
        setBilling(bill);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <>
        <Header title="Analytics" />
        <PageLoader />
      </>
    );
  }

  const totalCalls = callVolume.reduce((sum, d) => sum + d.calls, 0);

  return (
    <>
      <Header title="Analytics" subtitle="Performance insights for your AI agents" />
      <div className="flex-1 p-6 space-y-6">
        {/* Stats row */}
        {billing && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatsCard
              title="Minutes Used"
              value={billing.minutes_used}
              subtitle={`of ${billing.minutes_limit < 0 ? "∞" : billing.minutes_limit} this month`}
              icon={Clock}
            />
            <StatsCard
              title="Total Calls (30d)"
              value={totalCalls}
              icon={BarChart3}
            />
            <StatsCard
              title="Plan"
              value={billing.plan.charAt(0).toUpperCase() + billing.plan.slice(1)}
              subtitle={`$${billing.plan_price_usd}/month`}
              icon={TrendingUp}
            />
            <StatsCard
              title="Overage"
              value={`${billing.overage_minutes} min`}
              icon={CheckCircle}
            />
          </div>
        )}

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Call Volume (Last 30 Days)</CardTitle>
            </CardHeader>
            <CardContent>
              {callVolume.length === 0 ? (
                <div className="flex items-center justify-center h-[260px] text-gray-400 text-sm">
                  No call data yet
                </div>
              ) : (
                <CallVolumeChart data={callVolume} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Sentiment Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <SentimentChart data={sentiment} />
            </CardContent>
          </Card>
        </div>

        {/* Usage progress */}
        {billing && billing.minutes_limit > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Monthly Usage</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Minutes Used</span>
                  <span className="font-medium">
                    {billing.minutes_used} / {billing.minutes_limit} min
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2.5">
                  <div
                    className="bg-accent h-2.5 rounded-full transition-all"
                    style={{
                      width: `${Math.min(
                        100,
                        (billing.minutes_used / billing.minutes_limit) * 100
                      )}%`,
                    }}
                  />
                </div>
                {billing.minutes_remaining > 0 && (
                  <p className="text-xs text-gray-500">
                    {billing.minutes_remaining} minutes remaining this month
                  </p>
                )}
                {billing.overage_minutes > 0 && (
                  <p className="text-xs text-red-600">
                    {billing.overage_minutes} overage minutes — consider upgrading your plan
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
