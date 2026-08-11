"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { LayoutDashboard, FileText, Plus, Building2 } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError";
import { cn } from "../../utils/cn";
import { ToastProvider } from "./ToastProvider";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";
const fetcher = <T,>(url: string) =>
  quotationFetch<T>(url, undefined, "Workspace could not be loaded.");

type Me = {
  profile: { name: string; email: string; imageUrl?: string | null };
};

const nav = [
  { label: "Desk", href: "/workspace", icon: LayoutDashboard },
  { label: "My quotations", href: "/workspace/quotations", icon: FileText },
  { label: "Accommodations", href: "/workspace/accommodations", icon: Building2 },
  { label: "New quotation", href: "/workspace/quotations/new", icon: Plus },
] as const;

function UserAvatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <span className="workspace-user-avatar" aria-hidden="true">
      {initials}
    </span>
  );
}

export default function WorkspaceShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { data, error } = useSWR<Me>(
    `${API_BASE}/api/v2/workspace/me`,
    fetcher
  );

  return (
    <ToastProvider>
      <div className="min-h-screen bg-[var(--color-surface-muted)] text-[var(--color-on-surface)]">
        <header className="border-b border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4 sm:px-8">
          <div className="mx-auto flex w-full max-w-[100rem] items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Link
                href="/workspace"
                className={cn(
                  getTypographyClassName("navTitle"),
                  "text-[var(--color-on-surface)] transition-colors hover:text-[var(--color-accent)]"
                )}
              >
                Travel Desk
              </Link>
            </div>
            <p
              className={cn(
                getTypographyClassName("navMeta"),
                "hidden text-[var(--color-muted)] sm:block"
              )}
            >
              {data?.profile.email ??
                (error ? apiErrorMessage(error) : "Loading your workspace…")}
            </p>
          </div>
        </header>

        <div className="mx-auto grid w-full max-w-[100rem] gap-6 px-5 py-6 lg:grid-cols-[15rem_minmax(0,1fr)] lg:px-8">
          <aside className="h-fit rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 shadow-[var(--elevation-card)]">
            <p
              className={cn(
                getTypographyClassName("overline"),
                "px-3 pb-3 text-[var(--color-muted)]"
              )}
            >
              Personal workspace
            </p>
            <nav
              className="flex gap-1 overflow-x-auto lg:flex-col"
              aria-label="Staff workspace"
            >
              {nav.map(({ label, href, icon: Icon }) => {
                const isActive = pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "workspace-nav-item shrink-0 rounded-[var(--radius-button)] px-3 py-3 transition-all",
                      isActive
                        ? "border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-xs"
                        : "border border-transparent text-[var(--color-on-surface)] hover:border-[var(--color-border)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]"
                    )}
                  >
                    <Icon size={16} aria-hidden="true" />
                    <span>{label}</span>
                  </Link>
                );
              })}
            </nav>

            {data?.profile ? (
              <div className="mt-5 flex items-center gap-3 border-t border-[var(--color-border)] px-3 pt-4">
                <UserAvatar name={data.profile.name} />
                <div className="min-w-0 flex-1">
                  <p
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "truncate text-[var(--color-on-surface)]"
                    )}
                  >
                    {data.profile.name}
                  </p>
                  <p
                    className={cn(
                      getTypographyClassName("caption"),
                      "text-[var(--color-muted)]"
                    )}
                  >
                    Travel Designer
                  </p>
                </div>
              </div>
            ) : null}
          </aside>
          <section className="min-w-0">{children}</section>
        </div>
      </div>
    </ToastProvider>
  );
}
