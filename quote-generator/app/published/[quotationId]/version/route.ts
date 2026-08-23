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
  _request: NextRequest,
  { params }: { params: Promise<{ quotationId: string }> }
) {
  const { quotationId } = await params;
  const latest = getLatestVersionInfo(quotationId);

  const noCacheHeaders = {
    'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0, s-maxage=0',
    'Pragma': 'no-cache',
    'Expires': '0',
  };

  if (!latest) {
    return NextResponse.json(
      { version: 1, latest_url: `/published/${encodeURIComponent(quotationId)}/v1.html` },
      { headers: noCacheHeaders }
    );
  }

  return NextResponse.json(
    {
      version: latest.version,
      latest_url: `/published/${encodeURIComponent(quotationId)}/${latest.file}`,
    },
    { headers: noCacheHeaders }
  );
}
