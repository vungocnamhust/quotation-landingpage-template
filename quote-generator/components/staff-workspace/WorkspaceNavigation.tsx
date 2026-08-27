"use client";

import Link, { type LinkProps } from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  createContext,
  type ComponentPropsWithoutRef,
  type MouseEvent,
  type ReactNode,
  startTransition,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  shouldStartWorkspaceNavigation,
  workspaceRouteKey,
} from "../../lib/workspaceNavigation.ts";

type NavigationOptions = Parameters<ReturnType<typeof useRouter>["push"]>[1];

type WorkspaceNavigationContextValue = {
  pendingHref: string | null;
  beginNavigation: (href: string) => boolean;
  push: (href: string, options?: NavigationOptions) => void;
};

const WorkspaceNavigationContext = createContext<WorkspaceNavigationContextValue | null>(null);

type NavigationIntent = {
  href: string;
  sourceRouteKey: string;
  targetRouteKey: string;
};

function getCurrentRouteKey(pathname: string, search: string): string {
  return `${pathname}${search ? `?${search}` : ""}`;
}

export function WorkspaceNavigationProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [navigationIntent, setNavigationIntent] = useState<NavigationIntent | null>(null);
  const search = searchParams.toString();
  const currentRouteKey = getCurrentRouteKey(pathname, search);
  const [prevRouteKey, setPrevRouteKey] = useState(currentRouteKey);

  if (prevRouteKey !== currentRouteKey) {
    setPrevRouteKey(currentRouteKey);
    if (navigationIntent) {
      setNavigationIntent(null);
    }
  }

  const pendingHref =
    navigationIntent &&
    navigationIntent.sourceRouteKey === currentRouteKey &&
    navigationIntent.targetRouteKey !== currentRouteKey
      ? navigationIntent.href
      : null;

  useEffect(() => {
    if (!navigationIntent) return;
    const timer = setTimeout(() => {
      setNavigationIntent(null);
    }, 5000);
    return () => clearTimeout(timer);
  }, [navigationIntent]);

  const beginNavigation = useCallback(
    (href: string): boolean => {
      const targetRouteKey = workspaceRouteKey(href, window.location.origin);
      if (!targetRouteKey || targetRouteKey === currentRouteKey) return false;
      setNavigationIntent({ href, sourceRouteKey: currentRouteKey, targetRouteKey });
      return true;
    },
    [currentRouteKey],
  );

  const push = useCallback(
    (href: string, options?: NavigationOptions) => {
      beginNavigation(href);
      startTransition(() => {
        router.push(href, options);
      });
    },
    [beginNavigation, router],
  );

  const value = useMemo(
    () => ({ pendingHref, beginNavigation, push }),
    [beginNavigation, pendingHref, push],
  );

  return (
    <WorkspaceNavigationContext.Provider value={value}>
      {pendingHref ? (
        <>
          <div className="workspace-navigation-progress" aria-hidden="true">
            <div className="workspace-navigation-progress__bar" />
          </div>
          <p className="sr-only" role="status" aria-live="polite">
            Loading workspace destination…
          </p>
        </>
      ) : null}
      {children}
    </WorkspaceNavigationContext.Provider>
  );
}

export function useWorkspaceNavigation(): WorkspaceNavigationContextValue {
  const value = useContext(WorkspaceNavigationContext);
  if (!value) {
    throw new Error("useWorkspaceNavigation must be used inside WorkspaceNavigationProvider.");
  }
  return value;
}

type WorkspaceNavigationLinkProps = Omit<
  ComponentPropsWithoutRef<typeof Link>,
  "href" | "onClick" | "children"
> &
  Pick<LinkProps, "href"> & {
    children: ReactNode;
    onClick?: (event: MouseEvent<HTMLAnchorElement>) => void;
  };

export function WorkspaceNavigationLink({
  children,
  href,
  onClick,
  target,
  download,
  ...props
}: WorkspaceNavigationLinkProps) {
  const { pendingHref, beginNavigation } = useWorkspaceNavigation();
  const hrefString = typeof href === "string" ? href : href.pathname ?? "";
  const isPending = pendingHref === hrefString;

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event);
    if (event.defaultPrevented) return;
    if (isPending) {
      event.preventDefault();
      return;
    }
    if (
      shouldStartWorkspaceNavigation(
        {
          button: event.button,
          defaultPrevented: event.defaultPrevented,
          metaKey: event.metaKey,
          ctrlKey: event.ctrlKey,
          shiftKey: event.shiftKey,
          altKey: event.altKey,
          target,
          download: Boolean(download),
        },
        hrefString,
        window.location.origin,
      )
    ) {
      beginNavigation(hrefString);
    }
  };

  return (
    <Link
      {...props}
      href={href}
      target={target}
      download={download}
      onClick={handleClick}
      aria-busy={isPending || undefined}
      aria-disabled={isPending || undefined}
      data-workspace-navigation-pending={isPending || undefined}
    >
      {children}
      {isPending ? <span className="workspace-navigation-link__indicator" aria-hidden="true" /> : null}
    </Link>
  );
}
