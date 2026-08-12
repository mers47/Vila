"use client";

import { useEffect, useState } from "react";
import { api, Lead } from "@/components/api";

export default function Dashboard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/leads/?limit=10").then(data => { setLeads(data || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const stats = { total: leads.length, qualified: leads.filter(l => l.status === "QUALIFIED").length, contacted: leads.filter(l => l.status === "CONTACTED").length };

  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>داشبورد</h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
        <div className="card"><h3>کل لیدها</h3><p style={{ fontSize: "2rem", fontWeight: 700 }}>{stats.total}</p></div>
        <div className="card"><h3>واجد شرایط</h3><p style={{ fontSize: "2rem", fontWeight: 700, color: "var(--success)" }}>{stats.qualified}</p></div>
        <div className="card"><h3>تماس گرفته شده</h3><p style={{ fontSize: "2rem", fontWeight: 700, color: "var(--primary)" }}>{stats.contacted}</p></div>
      </div>
      <h2 style={{ marginBottom: "1rem" }}>آخرین لیدها</h2>
      {loading ? <p>در حال بارگذاری...</p> : (
        <table className="table">
          <thead><tr><th>نام</th><th>صنعت</th><th>شهر</th><th>امتیاز</th><th>وضعیت</th></tr></thead>
          <tbody>{leads.map(l => (
            <tr key={l.id}><td>{l.business_name}</td><td>{l.industry || "—"}</td><td>{l.city || "—"}</td><td>{l.score}</td><td><span className={`badge ${l.status === "QUALIFIED" ? "badge-success" : "badge-neutral"}`}>{l.status}</span></td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}