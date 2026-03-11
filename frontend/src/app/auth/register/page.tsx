"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Bot } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    organization_name: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.register(form);
      router.push("/dashboard");
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-accent rounded-xl mb-3">
            <Bot className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">AgenticP1</h1>
          <p className="text-gray-500 text-sm mt-1">Start your free trial today</p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Create your account</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Full Name"
              placeholder="John Smith"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
            <Input
              label="Company Name"
              placeholder="Acme Dental Clinic"
              value={form.organization_name}
              onChange={(e) => setForm({ ...form, organization_name: e.target.value })}
              required
            />
            <Input
              label="Work Email"
              type="email"
              placeholder="you@company.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
            <Input
              label="Password"
              type="password"
              placeholder="Min. 8 characters"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              minLength={8}
            />

            {error && (
              <div className="bg-red-50 text-red-700 text-sm rounded-lg px-4 py-3 border border-red-100">
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              loading={loading}
              disabled={!form.email || !form.password || !form.full_name || !form.organization_name}
            >
              Create Account
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-accent hover:underline font-medium">
              Sign in
            </Link>
          </div>

          <p className="mt-4 text-xs text-center text-gray-400">
            By signing up, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>
    </div>
  );
}
