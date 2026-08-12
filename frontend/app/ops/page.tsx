"use client";

import { useEffect, useState } from "react";
import { api } from "@/components/api";

export default function OpsPage() {
  const [dashboard, setDashboard] = useState<any>(null);
  useEffect(() => { api.get("/ops/dashboard").then(data => setDashboard(data)).catch(() => {}); }, []);

  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>مرکز عملیات</h1>
      {!dashboard ? <p>در حال بارگذاری... (نیاز به دسترسی ادمین)</p> : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
            <div className="card"><h3>پیام‌های ناموفق</h3><p style={{ fontSize: "2rem", fontWeight: 700, color: "var(--danger)" }}>{dashboard.failed_messages}</p></div>
            <div className="card"><h3>رویدادهای Outbox</h3><p style={{ fontSize: "2rem", fontWeight: 700 }}>{dashboard.pending_outbox_events}</p></div>
          </div>
          <h2>مدارشکن‌ها (Circuit Breakers)</h2>
          <table className="table">
            <thead><tr><th>Provider</th><th>وضعیت</th><th>زمان باقی‌مانده</th></tr></thead>
            <tbody>{dashboard.circuit_breakers && Object.entries(dashboard.circuit_breakers).map(([k, v]: any) => (
              <tr key={k}><td>{k}</td><td><span className={`badge ${v.open ? "badge-danger" : "badge-success"}`}>{v.open ? "باز" : "بسته"}</span></td><td>{v.retry_in_seconds}s</td></tr>
            ))}</tbody>
          </table>
        </>
      )}
    </div>
  );
}