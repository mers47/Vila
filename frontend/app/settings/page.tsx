"use client";

import { useState } from "react";
import { api } from "@/components/api";

export default function SettingsPage() {
  const [profileName, setProfileName] = useState("");
  const [message, setMessage] = useState("");

  const createProfile = async () => {
    try {
      await api.post("/scoring/profiles", { name: profileName, is_active: true });
      setMessage("پروفایل امتیازدهی ساخته شد");
    } catch {
      setMessage("خطا در ایجاد پروفایل");
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>تنظیمات</h1>
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>پروفایل امتیازدهی</h3>
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
          <input className="input" placeholder="نام پروفایل" value={profileName} onChange={e => setProfileName(e.target.value)} />
          <button className="btn btn-primary" onClick={createProfile}>ایجاد</button>
        </div>
        {message && <p style={{ marginTop: "0.5rem" }}>{message}</p>}
      </div>
      <div className="card">
        <h3>وضعیت اتصال</h3>
        <p>API: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1"}</p>
        <p>محیط: توسعه</p>
      </div>
    </div>
  );
}