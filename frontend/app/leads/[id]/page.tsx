"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/components/api";

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [lead, setLead] = useState<any>(null);
  const [contacts, setContacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get(`/leads/${id}`), api.get(`/contacts/lead/${id}`)]).then(([l, c]) => {
      setLead(l); setContacts(c || []); setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  if (loading) return <p>در حال بارگذاری...</p>;
  if (!lead) return <p>لید یافت نشد</p>;

  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>{lead.business_name}</h1>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="card">
          <h3>اطلاعات پایه</h3>
          <p>صنعت: {lead.industry || "—"}</p>
          <p>شهر: {lead.city || "—"}</p>
          <p>استان: {lead.province || "—"}</p>
          <p>وب‌سایت: {lead.website ? <a href={lead.website}>{lead.website}</a> : "—"}</p>
        </div>
        <div className="card">
          <h3>وضعیت</h3>
          <p>امتیاز: {lead.score}</p>
          <p>وضعیت: {lead.status}</p>
          <p>دما: {lead.temperature}</p>
          <p>منبع: {lead.source}</p>
        </div>
      </div>
      <h2 style={{ marginTop: "2rem", marginBottom: "1rem" }}>راه‌های ارتباطی</h2>
      {contacts.length === 0 ? <p>بدون راه ارتباطی</p> : (
        <table className="table">
          <thead><tr><th>کانال</th><th>مقدار</th><th>وضعیت رضایت</th></tr></thead>
          <tbody>{contacts.map((c: any) => (
            <tr key={c.id}><td>{c.channel}</td><td>{c.value}</td><td>{c.consent_status}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}