"use client";

import { useRouter } from "next/navigation";

export default function LogoutButton() {
  const router = useRouter();
  return <button onClick={async () => { await fetch("/api/v1/auth/logout", { method: "POST" }); router.push("/login"); }} style={{ marginRight: "auto" }}>خروج</button>;
}