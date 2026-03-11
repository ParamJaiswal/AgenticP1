"use client";

import { useEffect, useState } from "react";
import { Key, Copy, Check, User, CreditCard, Bell } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import type { User as UserType, BillingUsage } from "@/types";
import { PLAN_NAMES } from "@/lib/constants";

export default function SettingsPage() {
  const [user, setUser] = useState<UserType | null>(null);
  const [billing, setBilling] = useState<BillingUsage | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [generatingKey, setGeneratingKey] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [u, b] = await Promise.all([api.getMe(), api.getBillingUsage()]);
        setUser(u);
        setBilling(b);
      } catch (e) {
        console.error(e);
      }
    }
    load();
  }, []);

  async function generateKey() {
    setGeneratingKey(true);
    try {
      const res = await api.generateApiKey();
      setApiKey(res.api_key);
    } finally {
      setGeneratingKey(false);
    }
  }

  async function revokeKey() {
    if (!confirm("Revoke API key?")) return;
    await api.revokeApiKey();
    setApiKey(null);
    if (user) setUser({ ...user, has_api_key: false });
  }

  function copyKey() {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <>
      <Header title="Settings" subtitle="Manage your account, API keys, and billing" />
      <div className="flex-1 p-6 space-y-6 max-w-2xl">
        {/* Profile */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-4 h-4 text-accent" />
              Profile
            </CardTitle>
          </CardHeader>
          <CardContent>
            {user && (
              <div className="space-y-2 text-sm">
                <div className="flex gap-3">
                  <span className="text-gray-500 w-32">Name</span>
                  <span className="font-medium">{user.full_name}</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-gray-500 w-32">Email</span>
                  <span className="font-medium">{user.email}</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-gray-500 w-32">Role</span>
                  <span className="font-medium capitalize">{user.role}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* API Keys */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="w-4 h-4 text-accent" />
              API Keys
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-500">
              Use API keys to authenticate programmatic access to the AgenticP1 API.
            </p>

            {apiKey ? (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <code className="flex-1 text-xs bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 font-mono break-all">
                    {apiKey}
                  </code>
                  <Button variant="secondary" size="sm" onClick={copyKey}>
                    {copied ? (
                      <Check className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-amber-600">
                  ⚠ Save this key now — it won't be shown again.
                </p>
                <Button variant="danger" size="sm" onClick={revokeKey}>
                  Revoke Key
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {user?.has_api_key && (
                  <p className="text-sm text-gray-600">You have an active API key.</p>
                )}
                <div className="flex gap-2">
                  <Button size="sm" onClick={generateKey} loading={generatingKey}>
                    Generate New API Key
                  </Button>
                  {user?.has_api_key && (
                    <Button variant="danger" size="sm" onClick={revokeKey}>
                      Revoke
                    </Button>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Billing */}
        {billing && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-accent" />
                Billing & Plan
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-gray-900">
                      {PLAN_NAMES[billing.plan as keyof typeof PLAN_NAMES] || billing.plan} Plan
                    </p>
                    <p className="text-sm text-gray-500">
                      ${billing.plan_price_usd}/month
                    </p>
                  </div>
                  <Button variant="secondary" size="sm">
                    Upgrade Plan
                  </Button>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Minutes Used</span>
                    <span className="font-medium">{billing.minutes_used}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Minutes Limit</span>
                    <span className="font-medium">
                      {billing.minutes_limit < 0 ? "Unlimited" : billing.minutes_limit}
                    </span>
                  </div>
                  {billing.overage_minutes > 0 && (
                    <div className="flex justify-between text-red-600">
                      <span>Overage</span>
                      <span>{billing.overage_minutes} min</span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* API Reference */}
        <Card>
          <CardHeader>
            <CardTitle>API Reference</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500 mb-3">
              Full API documentation is available at:
            </p>
            <div className="flex gap-2">
              <a
                href="/docs"
                target="_blank"
                className="text-sm text-accent hover:underline"
              >
                OpenAPI Docs (Swagger)
              </a>
              <span className="text-gray-300">|</span>
              <a
                href="/redoc"
                target="_blank"
                className="text-sm text-accent hover:underline"
              >
                ReDoc
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
