const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
    return null;
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  get: (path: string) => request(path),
  post: (path: string, body?: unknown) => request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: (path: string, body: unknown) => request(path, { method: "PATCH", body: JSON.stringify(body) }),
};

export interface Lead {
  id: string;
  business_name: string;
  industry: string | null;
  city: string | null;
  score: number;
  status: string;
  temperature: string;
  created_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  status: string;
  min_score: number;
  channels: string[];
  message_template: string;
  created_at: string;
}