"use client";

import { useEffect, useState } from "react";
import { Plus, Bot, Trash2, Edit } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/Loader";
import { api } from "@/lib/api";
import type { AgentConfig } from "@/types";
import { PERSONALITY_OPTIONS, INDUSTRY_OPTIONS } from "@/lib/constants";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingAgent, setEditingAgent] = useState<AgentConfig | null>(null);

  const defaultForm = {
    name: "",
    description: "",
    industry: "general",
    personality: "professional" as AgentConfig["personality"],
    greeting_message: "Hello! Thank you for calling. How can I help you today?",
    phone_number: "",
    tools_enabled: {
      book_appointment: false,
      check_order_status: false,
      transfer_to_human: true,
      send_sms: false,
      add_to_waitlist: false,
    },
  };

  const [form, setForm] = useState(defaultForm);

  useEffect(() => {
    loadAgents();
  }, []);

  async function loadAgents() {
    setLoading(true);
    try {
      const res = await api.listAgents();
      setAgents(res.data || []);
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditingAgent(null);
    setForm(defaultForm);
    setShowModal(true);
  }

  function openEdit(agent: AgentConfig) {
    setEditingAgent(agent);
    setForm({
      name: agent.name,
      description: agent.description,
      industry: agent.industry,
      personality: agent.personality,
      greeting_message: agent.greeting_message,
      phone_number: agent.phone_number || "",
      tools_enabled: agent.tools_enabled as typeof defaultForm.tools_enabled,
    });
    setShowModal(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      if (editingAgent) {
        await api.updateAgent(editingAgent.id, form);
      } else {
        await api.createAgent(form);
      }
      setShowModal(false);
      await loadAgents();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this agent?")) return;
    await api.deleteAgent(id);
    await loadAgents();
  }

  if (loading) {
    return (
      <>
        <Header title="Agents" />
        <PageLoader />
      </>
    );
  }

  return (
    <>
      <Header title="AI Agents" subtitle="Configure and manage your AI calling agents" />
      <div className="flex-1 p-6 space-y-4">
        <div className="flex justify-end">
          <Button size="sm" onClick={openCreate}>
            <Plus className="w-4 h-4" />
            New Agent
          </Button>
        </div>

        {agents.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-100 p-12 text-center">
            <Bot className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 font-medium">No agents configured yet</p>
            <p className="text-gray-400 text-sm mt-1 mb-4">
              Create your first AI agent to start handling calls.
            </p>
            <Button size="sm" onClick={openCreate}>
              <Plus className="w-4 h-4" />
              Create Agent
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-9 h-9 bg-accent/10 rounded-lg flex items-center justify-center">
                      <Bot className="w-5 h-5 text-accent" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 text-sm">{agent.name}</p>
                      <p className="text-xs text-gray-400 capitalize">{agent.industry}</p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(agent)}>
                      <Edit className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(agent.id)}>
                      <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    </Button>
                  </div>
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">
                  {agent.description || agent.greeting_message}
                </p>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(agent.tools_enabled || {})
                    .filter(([, v]) => v)
                    .map(([k]) => (
                      <span
                        key={k}
                        className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full"
                      >
                        {k.replace(/_/g, " ")}
                      </span>
                    ))}
                </div>
                {agent.phone_number && (
                  <p className="text-xs text-gray-400">📞 {agent.phone_number}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title={editingAgent ? "Edit Agent" : "Create Agent"}
        className="max-w-xl"
      >
        <div className="space-y-4">
          <Input
            label="Agent Name"
            placeholder="e.g., Dental Clinic Support"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
            <select
              className="input-field"
              value={form.industry}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
            >
              {INDUSTRY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Personality</label>
            <select
              className="input-field"
              value={form.personality}
              onChange={(e) => setForm({ ...form, personality: e.target.value as "friendly" | "professional" | "casual" })}
            >
              {PERSONALITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Greeting Message</label>
            <textarea
              className="input-field h-20 resize-none"
              value={form.greeting_message}
              onChange={(e) => setForm({ ...form, greeting_message: e.target.value })}
            />
          </div>
          <Input
            label="Phone Number (optional)"
            placeholder="+15551234567"
            value={form.phone_number}
            onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enabled Tools
            </label>
            <div className="space-y-2">
              {Object.entries(form.tools_enabled).map(([key, enabled]) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        tools_enabled: {
                          ...form.tools_enabled,
                          [key]: e.target.checked,
                        },
                      })
                    }
                    className="rounded border-gray-300 text-accent focus:ring-accent"
                  />
                  <span className="text-sm text-gray-700">
                    {key.replace(/_/g, " ")}
                  </span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <Button
              className="flex-1"
              onClick={handleSave}
              loading={saving}
              disabled={!form.name}
            >
              {editingAgent ? "Save Changes" : "Create Agent"}
            </Button>
            <Button
              variant="secondary"
              className="flex-1"
              onClick={() => setShowModal(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
