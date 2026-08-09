import { Allura, Cormorant_Garamond, Jost, Montserrat } from 'next/font/google';

const cormorant = Cormorant_Garamond({
  subsets: ['latin', 'latin-ext', 'vietnamese'],
  style: ['normal', 'italic'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-cormorant',
});

const montserrat = Montserrat({
  subsets: ['latin', 'latin-ext', 'vietnamese'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-montserrat',
});

const jost = Jost({
  subsets: ['latin', 'latin-ext'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-jost',
});

const allura = Allura({
  subsets: ['latin', 'latin-ext', 'vietnamese'],
  weight: '400',
  display: 'swap',
  variable: '--font-allura',
});

export const typographyFontVariables = [
  cormorant.variable,
  montserrat.variable,
  jost.variable,
  allura.variable,
].join(' ');
