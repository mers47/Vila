"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Lead } from "@/components/api";

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    api.get(`/leads/?${params.toString()}`).then(data => { setLeads(data || []); setLoading(false); }).catch(() => setLoading(false));
  }, [search, status]);

  const statusBadge = (s: string) => {
    const map: Record<string, string> = { QUALIFIED: "badge-success", CONTACTED: "badge-warning", CONVERTED: "badge-success", DISQUALIFIED: "badge-danger" };
    return map[s] || "badge-neutral";
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1>لیدها</h1>
        <Link href="/leads/new" className="btn btn-primary">+ لید جدید</Link>
      </div>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <input className="input" style={{ maxWidth: 300 }} placeholder="جستجوی نام..." value={search} onChange={e => setSearch(e.target.value)} />
        <select className="input" style={{ maxWidth: 200 }} value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">همه وضعیت‌ها</option>
          <option value="NEW">جدید</option>
          <option value="CONTACTED">تماس گرفته شده</option>
          <option value="QUALIFIED">واجد شرایط</option>
          <option value="CONVERTED">تبدیل شده</option>
        </select>
      </div>
      {loading ? <p>در حال بارگذاری...</p> : (
        <table className="table">
          <thead><tr><th>نام</th><th>صنعت</th><th>شهر</th><th>امتیاز</th><th>وضعیت</th><th>عملیات</th></tr></thead>
          <tbody>{leads.map(l => (
            <tr key={l.id}>
              <td><Link href={`/leads/${l.id}`}>{l.business_name}</Link></td>
              <td>{l.industry || "—"}</td><td>{l.city || "—"}</td><td>{l.score}</td>
              <td><span className={`badge ${statusBadge(l.status)}`}>{l.status}</span></td>
              <td><Link href={`/leads/${l.id}`}>مشاهده</Link></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}