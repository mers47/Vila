"use client";

import { useEffect, useState } from "react";
import { api } from "@/components/api";

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  useEffect(() => { api.get("/audit-logs/?limit=50").then(data => setLogs(data || [])); }, []);

  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>گزارشات حسابرسی</h1>
      {logs.length === 0 ? <p>بدون رویداد</p> : (
        <table className="table">
          <thead><tr><th>عملیات</th><th>نوع</th><th>شناسه</th><th>تاریخ</th></tr></thead>
          <tbody>{logs.map((log: any) => (
            <tr key={log.id}><td>{log.action}</td><td>{log.entity_type}</td><td>{log.entity_id?.slice(0, 8) || "—"}</td><td>{new Date(log.created_at).toLocaleDateString("fa-IR")}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}