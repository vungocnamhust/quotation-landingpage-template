import type { Metadata } from 'next';
import 'leaflet/dist/leaflet.css';
import './globals.css';
import { typographyFontVariables } from './fonts';
import { buildTypographyStyleSheet } from '../config/typography';

export const metadata: Metadata = {
  title: 'Quote Generator Display System',
  description:
    'Theme-driven brochure display system with shared section view models, typography config, and desktop/mobile/pdf view modes.',
};

const typographyStyleSheet = buildTypographyStyleSheet();
const initialViewModeScript = `
(() => {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get('view');
  const requestedTheme = params.get('theme');
  const requestedLang = params.get('lang');
  const pathname = window.location.pathname;
  const mode =
    requested === 'desktop' || requested === 'mobile' || requested === 'pdf'
      ? requested
      : pathname === '/pdf'
        ? 'pdf'
        : window.matchMedia('(max-width: 767px)').matches
          ? 'mobile'
          : 'desktop';
  document.documentElement.setAttribute('data-view-mode', mode);
  document.documentElement.setAttribute('data-theme', requestedTheme === 'brochure' ? requestedTheme : 'brochure');
  document.documentElement.setAttribute('data-brand', document.documentElement.getAttribute('data-brand') || 'runtime');
  document.documentElement.lang =
    requestedLang === 'vi' || requestedLang === 'ar' || requestedLang === 'en' ? requestedLang : 'en';
})();
`;

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-brand="runtime"
      data-theme="brochure"
      data-view-mode="desktop"
      className={typographyFontVariables}
      suppressHydrationWarning
    >
      <head>
        <script
          id="initial-view-mode"
          dangerouslySetInnerHTML={{ __html: initialViewModeScript }}
        />
        <style
          id="brand-typography"
          dangerouslySetInnerHTML={{ __html: typographyStyleSheet }}
        />
      </head>
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
