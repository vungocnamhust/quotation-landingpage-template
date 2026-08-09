import WorkspaceQuotationOverview from "../../../../components/staff-workspace/WorkspaceQuotationOverview";

export default async function WorkspaceQuotationPage({ params }: { params: Promise<{ quotationId: string }> }) {
  const { quotationId } = await params;
  return <WorkspaceQuotationOverview quotationId={quotationId} />;
}
