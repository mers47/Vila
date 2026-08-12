"use client";

import { useEffect, useState } from "react";
import { api } from "@/components/api";

export default function FollowupsPage() {
  const [leads, setLeads] = useState<any[]>([]);
  useEffect(() => { api.get("/leads/?status=CONTACTED").then(data => setLeads(data || [])); }, []);

  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>لیست پیگیری</h1>
      {leads.length === 0 ? <p>موردی برای پیگیری نیست</p> : (
        <table className="table">
          <thead><tr><th>نام</th><th>آخرین تماس</th><th>وضعیت</th></tr></thead>
          <tbody>{leads.map((l: any) => (
            <tr key={l.id}>
              <td>{l.business_name}</td>
              <td>{l.last_contact_at ? new Date(l.last_contact_at).toLocaleDateString("fa-IR") : "—"}</td>
              <td><span className="badge badge-warning">{l.status}</span></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}