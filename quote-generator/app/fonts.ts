import { Amiri, Cairo, Cormorant_Garamond, Montserrat, Noto_Sans_Arabic } from 'next/font/google';
import localFont from 'next/font/local';

const cormorant = Cormorant_Garamond({
  subsets: ['latin', 'latin-ext', 'vietnamese'],
  style: ['normal', 'italic'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-cormorant',
});

const montserrat = Montserrat({
  subsets: ['latin', 'latin-ext', 'vietnamese'],
  style: ['normal', 'italic'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-montserrat',
});

const notoSansArabic = Noto_Sans_Arabic({
  subsets: ['arabic'],
  weight: ['300', '400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-noto-sans-arabic',
});

const cairo = Cairo({
  subsets: ['latin', 'arabic'],
  weight: ['300', '400', '600', '700'],
  display: 'swap',
  variable: '--font-cairo',
});

const amiri = Amiri({
  subsets: ['latin', 'arabic'],
  style: ['normal', 'italic'],
  weight: ['400', '700'],
  display: 'swap',
  variable: '--font-amiri',
});

/**
 * Buongiorno Rastellino — handwriting / calligraphy font for the designer
 * signature glyph in the Open Letter section.
 *
 * ⚠️  FONT FILE REQUIRED:
 *   Place the purchased font file at:
 *     quote-generator/public/fonts/buongiorno-rastellino.woff2
 *   Purchase from: https://www.myfonts.com/collections/buongiorno-rastellino-font-faridul-type-foundry
 *
 * The font is loaded as a local file (not Google Fonts) and exposed via
 * CSS variable --font-buongiorno-rastellino consumed by typography.ts.
 */
const buongiornoRastellino = localFont({
  src: '../public/fonts/buongiorno-rastellino.woff2',
  display: 'swap',
  variable: '--font-buongiorno-rastellino',
  fallback: ['cursive'],
});

export const typographyFontVariables = [
  cormorant.variable,
  montserrat.variable,
  notoSansArabic.variable,
  cairo.variable,
  amiri.variable,
  buongiornoRastellino.variable,
].join(' ');

