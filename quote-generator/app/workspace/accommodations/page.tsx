import WorkspaceAccommodationList from "../../../components/staff-workspace/WorkspaceAccommodationList";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

export default function AccommodationsPage() {
  return (
    <main className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p
            className={cn(
              getTypographyClassName("overline"),
              "text-[var(--color-accent)]"
            )}
          >
            Catalog management
          </p>
          <h1
            className={cn(
              getTypographyClassName("pageTitle"),
              "mt-2 text-[var(--color-on-surface)]"
            )}
          >
            Accommodations
          </h1>
          <p
            className={cn(
              getTypographyClassName("bodyLg"),
              "mt-2 text-[var(--color-muted)]"
            )}
          >
            Manage hotel & resort profiles, default check-in/out rules, and property media across destinations.
          </p>
        </div>
      </header>

      <WorkspaceAccommodationList />
    </main>
  );
}
