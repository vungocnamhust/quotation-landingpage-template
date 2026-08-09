import { redirect } from 'next/navigation';

export default async function QuotationWorkspacePage({
  params,
  searchParams,
}: {
  params: Promise<{ quotationId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { quotationId } = await params;
  const query = await searchParams;
  const target = new URLSearchParams();
  if (typeof query.stage === 'string') target.set('stage', query.stage);
  if (typeof query.section === 'string') target.set('section', query.section);
  if (typeof query.lang === 'string') target.set('lang', query.lang);
  const suffix = target.size ? `?${target}` : '';
  redirect(`/workspace/quotations/${encodeURIComponent(quotationId)}/edit${suffix}`);
}
