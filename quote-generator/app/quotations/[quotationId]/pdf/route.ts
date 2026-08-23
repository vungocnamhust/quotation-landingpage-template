import { NextRequest } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

function getPublishedDir(quotationId: string): string {
  return path.join(process.cwd(), 'public', 'published', quotationId);
}

function findPdfHtmlFile(publishedDir: string, lang: string): string | null {
  if (!fs.existsSync(publishedDir)) return null;

  const langPdf = path.join(publishedDir, `pdf_${lang.toLowerCase()}.html`);
  if (fs.existsSync(langPdf)) return langPdf;

  const defaultPdf = path.join(publishedDir, 'pdf.html');
  if (fs.existsSync(defaultPdf)) return defaultPdf;

  const fallbackEnPdf = path.join(publishedDir, 'pdf_en.html');
  if (fs.existsSync(fallbackEnPdf)) return fallbackEnPdf;

  return null;
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

  const publishedDir = getPublishedDir(quotationId);
  const pdfFilePath = findPdfHtmlFile(publishedDir, lang);

  if (pdfFilePath && fs.existsSync(pdfFilePath)) {
    try {
      const htmlContent = fs.readFileSync(pdfFilePath, 'utf-8');
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
      console.error(`[GET /quotations/${quotationId}/pdf] Error reading published PDF:`, err);
    }
  }

  return new Response('PDF for quotation not found', {
    status: 404,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
