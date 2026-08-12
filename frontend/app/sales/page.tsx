"use client";

import { useEffect, useState } from "react";
import { api } from "@/components/api";

export default function SalesPage() {
  const [handoffs, setHandoffs] = useState<any[]>([]);
  useEffect(() => { api.get("/sales/handoffs").then(data => setHandoffs(data || [])); }, []);

  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>ارجاعات فروش</h1>
      {handoffs.length === 0 ? <p>بدون ارجاع</p> : (
        <table className="table">
          <thead><tr><th>لید</th><th>وضعیت</th><th>دلیل</th><th>تاریخ</th></tr></thead>
          <tbody>{handoffs.map((h: any) => (
            <tr key={h.id}><td>{h.lead_id}</td><td><span className={`badge ${h.status === "CLAIMED" ? "badge-success" : "badge-warning"}`}>{h.status}</span></td><td>{h.reason}</td><td>{new Date(h.created_at).toLocaleDateString("fa-IR")}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}