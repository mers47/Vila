import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import LogoutButton from "@/components/LogoutButton";

export const metadata: Metadata = {
  title: "Lead Platform",
  description: "پلتفرم مشتری‌یابی و مدیریت لید",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <nav className="nav">
          <Link href="/">داشبورد</Link>
          <Link href="/leads">لیدها</Link>
          <Link href="/campaigns">کمپین‌ها</Link>
          <Link href="/followups">پیگیری</Link>
          <Link href="/sales">فروش</Link>
          <Link href="/ops">عملیات</Link>
          <Link href="/settings">تنظیمات</Link>
          <LogoutButton />
        </nav>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}