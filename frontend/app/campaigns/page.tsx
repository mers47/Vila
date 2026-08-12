"use client";

import { useEffect, useState } from "react";
import { api, Campaign } from "@/components/api";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [channels, setChannels] = useState("");
  const [template, setTemplate] = useState("");

  const load = () => api.get("/campaigns/").then(data => { setCampaigns(data || []); setLoading(false); });
  useEffect(() => { load(); }, []);

  const create = async () => {
    await api.post("/campaigns/", { name, channels: channels.split(",").map(c => c.trim()), message_template: template, min_score: 60 });
    setName(""); setChannels(""); setTemplate(""); setShowForm(false);
    load();
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <h1>کمپین‌ها</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ کمپین جدید</button>
      </div>
      {showForm && (
        <div className="card" style={{ marginBottom: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <input className="input" placeholder="نام کمپین" value={name} onChange={e => setName(e.target.value)} />
          <input className="input" placeholder="کانال‌ها (مثلا WHATSAPP,TELEGRAM)" value={channels} onChange={e => setChannels(e.target.value)} />
          <textarea className="input" placeholder="متن پیام" value={template} onChange={e => setTemplate(e.target.value)} rows={3} />
          <button className="btn btn-primary" onClick={create}>ایجاد</button>
        </div>
      )}
      {loading ? <p>در حال بارگذاری...</p> : (
        <table className="table">
          <thead><tr><th>نام</th><th>وضعیت</th><th>کانال‌ها</th><th>حداقل امتیاز</th><th>تاریخ</th></tr></thead>
          <tbody>{campaigns.map(c => (
            <tr key={c.id}><td>{c.name}</td><td>{c.status}</td><td>{c.channels.join(", ")}</td><td>{c.min_score}</td><td>{new Date(c.created_at).toLocaleDateString("fa-IR")}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}