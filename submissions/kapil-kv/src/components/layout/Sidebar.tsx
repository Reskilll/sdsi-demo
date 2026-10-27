"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/utils/cn";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/tickets", label: "Tickets", icon: "🎫" },
  { href: "/sla-policies", label: "SLA Policies", icon: "⚙️" },
  { href: "/assignee-groups", label: "Assignee Groups", icon: "👥" },
  { href: "/holidays", label: "Holidays", icon: "📅" },
  { href: "/reports", label: "Reports", icon: "📈" },
  { href: "/settings", label: "Settings", icon: "🔧" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-56 flex-shrink-0 border-r border-[var(--border)] bg-[var(--muted)] lg:block">
      <div className="flex h-14 items-center border-b border-[var(--border)] px-4">
        <Link href="/dashboard" className="text-lg font-bold text-[var(--primary)]">
          SLA Tracker
        </Link>
      </div>
      <nav className="p-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                      : "text-[var(--foreground)] hover:bg-[var(--border)]",
                  )}
                >
                  <span className="text-lg">{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}