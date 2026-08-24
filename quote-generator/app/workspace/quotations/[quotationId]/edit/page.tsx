import { notFound, redirect } from "next/navigation";
import QuotationWorkspaceClient from "../../../../../components/quotation-workspace/QuotationWorkspaceClient";
import { resolveWorkspaceWorkflow } from "../../../../../lib/publicQuotationApi";

const WORKSPACE_STAGES = new Set(["impact", "facts", "content", "design", "review"]);

export const dynamic = "force-dynamic";

export default async function WorkspaceQuotationEditPage({
  params,
  searchParams,
}: {
  params: Promise<{ quotationId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { quotationId } = await params;
  const query = await searchParams;
  const workflow = await resolveWorkspaceWorkflow(quotationId);
  if (!workflow) notFound();
  const stage = typeof query.stage === "string" && WORKSPACE_STAGES.has(query.stage)
    ? query.stage
    : "facts";
  const requestedLocale = typeof query.lang === "string" ? query.lang : null;
  if (requestedLocale !== workflow.locale) {
    const canonicalQuery = new URLSearchParams({ stage, lang: workflow.locale });
    for (const key of ["section", "focus", "factsSection", "impactTarget"]) {
      if (typeof query[key] === "string") canonicalQuery.set(key, query[key]);
    }
    redirect(`/workspace/quotations/${encodeURIComponent(quotationId)}/edit?${canonicalQuery}`);
  }
  return <QuotationWorkspaceClient quotationId={quotationId} lang={workflow.locale} />;
}
