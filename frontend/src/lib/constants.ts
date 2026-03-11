export const PLAN_NAMES = {
  starter: "Starter",
  growth: "Growth",
  pro: "Pro",
  enterprise: "Enterprise",
} as const;

export const PLAN_PRICES = {
  starter: 49,
  growth: 149,
  pro: 399,
  enterprise: 999,
} as const;

export const PERSONALITY_OPTIONS = [
  { value: "professional", label: "Professional" },
  { value: "friendly", label: "Friendly" },
  { value: "casual", label: "Casual" },
];

export const INDUSTRY_OPTIONS = [
  { value: "general", label: "General Business" },
  { value: "healthcare", label: "Healthcare / Dental" },
  { value: "real_estate", label: "Real Estate" },
  { value: "ecommerce", label: "E-Commerce" },
  { value: "restaurant", label: "Restaurant / Food" },
  { value: "legal", label: "Legal Services" },
  { value: "finance", label: "Finance / Insurance" },
  { value: "hospitality", label: "Hospitality / Hotels" },
];

export const VOICE_OPTIONS = [
  { value: "en_US-amy-low", label: "Amy (US Female)" },
  { value: "en_US-ryan-low", label: "Ryan (US Male)" },
  { value: "en_GB-alba-medium", label: "Alba (UK Female)" },
  { value: "en_US-kathleen-low", label: "Kathleen (US Female)" },
];

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
