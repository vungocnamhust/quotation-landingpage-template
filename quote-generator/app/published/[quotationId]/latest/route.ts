import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

function getLatestVersionInfo(quotationId: string): { version: number; file: string } | null {
  const publishedDir = path.join(process.cwd(), 'public', 'published', quotationId);
  if (!fs.existsSync(publishedDir)) return null;

  const files = fs.readdirSync(publishedDir);
  const versions: Array<{ version: number; file: string }> = [];

  for (const file of files) {
    const match = file.match(/^v(\d+)(?:_[a-z]{2})?\.html$/i);
    if (match) {
      versions.push({
        version: parseInt(match[1], 10),
        file,
      });
    }
  }

  if (versions.length === 0) return null;
  versions.sort((a, b) => b.version - a.version);
  return versions[0];
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ quotationId: string }> }
) {
  const { quotationId } = await params;
  const latest = getLatestVersionInfo(quotationId);

  if (!latest) {
    return new Response('Published quotation not found', {
      status: 404,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    });
  }

  const redirectUrl = new URL(`/published/${encodeURIComponent(quotationId)}/${latest.file}`, request.url);
  return NextResponse.redirect(redirectUrl, {
    status: 307,
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
      'Pragma': 'no-cache',
      'Expires': '0',
    },
  });
}
