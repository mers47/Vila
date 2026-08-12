"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/components/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/auth/login", { email, password });
      router.push("/");
    } catch {
      setError("ایمیل یا رمز عبور اشتباه است");
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: "4rem auto" }}>
      <h1 style={{ textAlign: "center", marginBottom: "2rem" }}>ورود به پلتفرم</h1>
      <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <input className="input" type="email" placeholder="ایمیل" value={email} onChange={e => setEmail(e.target.value)} required />
        <input className="input" type="password" placeholder="رمز عبور" value={password} onChange={e => setPassword(e.target.value)} required />
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        <button className="btn btn-primary" type="submit">ورود</button>
      </form>
    </div>
  );
}