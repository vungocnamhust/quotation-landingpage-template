import { Amiri, Cairo, Cormorant_Garamond, Montserrat, Noto_Sans_Arabic } from 'next/font/google';

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

export const typographyFontVariables = [
  cormorant.variable,
  montserrat.variable,
  notoSansArabic.variable,
  cairo.variable,
  amiri.variable,
].join(' ');

