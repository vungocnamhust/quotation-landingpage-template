import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { resolveWorkspaceWorkflow } from '../../../lib/publicQuotationApi';

export const dynamic = 'force-dynamic';

function getPublishedDir(quotationId: string): string {
  return path.join(process.cwd(), 'public', 'published', quotationId);
}

function findLatestHtmlFile(publishedDir: string, lang: string): string | null {
  if (!fs.existsSync(publishedDir)) return null;

  const files = fs.readdirSync(publishedDir);
  const versionCandidates: Array<{ file: string; version: number; lang?: string }> = [];

  for (const file of files) {
    const match = file.match(/^v(\d+)(?:_([a-z]{2}))?\.html$/i);
    if (match) {
      versionCandidates.push({
        file,
        version: parseInt(match[1], 10),
        lang: match[2]?.toLowerCase(),
      });
    }
  }

  if (versionCandidates.length === 0) return null;

  // Sort descending by version number
  versionCandidates.sort((a, b) => b.version - a.version);

  const highestVersion = versionCandidates[0].version;
  const highestCandidates = versionCandidates.filter((c) => c.version === highestVersion);

  // Try matching target lang first
  const langMatch = highestCandidates.find((c) => c.lang === lang.toLowerCase());
  if (langMatch) return path.join(publishedDir, langMatch.file);

  // Try matching without lang or default
  const defaultMatch = highestCandidates.find((c) => !c.lang || c.lang === 'en');
  if (defaultMatch) return path.join(publishedDir, defaultMatch.file);

  return path.join(publishedDir, highestCandidates[0].file);
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ quotationId: string }> }
) {
  const { quotationId } = await params;
  const lang =
    request.nextUrl.searchParams.get('lang') ||
    request.nextUrl.searchParams.get('language') ||
    'en';

  // 1. Check if legacy static quotation exists in public/published/
  const publishedDir = getPublishedDir(quotationId);
  const htmlFilePath = findLatestHtmlFile(publishedDir, lang);

  if (htmlFilePath && fs.existsSync(htmlFilePath)) {
    try {
      const htmlContent = fs.readFileSync(htmlFilePath, 'utf-8');
      return new Response(htmlContent, {
        status: 200,
        headers: {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
          'Pragma': 'no-cache',
          'Expires': '0',
        },
      });
    } catch (err) {
      console.error(`[GET /quotations/${quotationId}] Error reading published HTML:`, err);
    }
  }

  // 2. Check if this is a V2 quotation in backend
  try {
    const workflow = await resolveWorkspaceWorkflow(quotationId);
    if (workflow) {
      // If it exists in V2 workflow, redirect to workspace
      const redirectUrl = new URL(`/workspace/quotations/${encodeURIComponent(quotationId)}`, request.url);
      return NextResponse.redirect(redirectUrl, { status: 307 });
    }
  } catch {
    // Backend may not be reachable or not a V2 quote
  }

  // 3. Not found
  return new Response('Quotation not found', {
    status: 404,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
