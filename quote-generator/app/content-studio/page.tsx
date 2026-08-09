import { notFound, redirect } from 'next/navigation';

export const dynamic = 'force-dynamic';

export default async function ContentStudioPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const quotationId = typeof params.quotationId === 'string' ? params.quotationId : '';
  if (!quotationId) notFound();
  const query = new URLSearchParams({ stage: 'content' });
  if (typeof params.section === 'string') query.set('section', params.section);
  redirect(`/workspace/quotations/${encodeURIComponent(quotationId)}/edit?${query}`);
}
