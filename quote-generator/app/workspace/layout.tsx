import type { CSSProperties } from "react";
import { getThemeDefinition } from "../../display/themeRegistry";
import { resolveColorSlotsFromProfile } from "../../config/runtimeThemeTokens";
import { resolveEditorBrandBootstrap } from "../../lib/publicQuotationApi";
import WorkspaceShell from "../../components/staff-workspace/WorkspaceShell";

// This layout resolves mutable editor brand state through the internal service
// boundary. It must run at request time, never during the image build.
export const dynamic = "force-dynamic";

export default async function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const bootstrap = await resolveEditorBrandBootstrap();
  if (!bootstrap) return children;
  const colors = resolveColorSlotsFromProfile({ profile: bootstrap.brandProfile, theme: getThemeDefinition(bootstrap.brandProfile.themeId ?? "brochure"), viewMode: "desktop" });
  return <div className="app-color-scope" style={colors.appChrome.style as CSSProperties}><WorkspaceShell>{children}</WorkspaceShell></div>;
}
