export type WorkspaceNavigationClick = {
  button: number;
  defaultPrevented: boolean;
  metaKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
  altKey: boolean;
  target?: string;
  download?: boolean;
};

export const DEFAULT_WORKSPACE_ORIGIN = "https://workspace.local";

export function workspaceRouteKey(
  href: string,
  origin = DEFAULT_WORKSPACE_ORIGIN,
): string | null {
  try {
    const url = new URL(href, origin);
    if (url.origin !== origin || (url.pathname !== "/workspace" && !url.pathname.startsWith("/workspace/"))) {
      return null;
    }
    return `${url.pathname}${url.search}`;
  } catch {
    return null;
  }
}

export function shouldStartWorkspaceNavigation(
  click: WorkspaceNavigationClick,
  href: string,
  origin = DEFAULT_WORKSPACE_ORIGIN,
): boolean {
  return (
    !click.defaultPrevented &&
    click.button === 0 &&
    !click.metaKey &&
    !click.ctrlKey &&
    !click.shiftKey &&
    !click.altKey &&
    !click.download &&
    (!click.target || click.target === "_self") &&
    workspaceRouteKey(href, origin) !== null
  );
}
