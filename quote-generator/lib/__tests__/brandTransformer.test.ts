import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import {
  resolveBrand,
  transformPdfHtmlWithBrand,
} from '../brandTransformer.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('brandTransformer module', () => {
  describe('resolveBrand', () => {
    it('resolves brand from query param aliases', () => {
      assert.equal(resolveBrand('capella_travel').id, 'capella_travel');
      assert.equal(resolveBrand('capella-travel').id, 'capella_travel');
      assert.equal(resolveBrand('capella').id, 'capella_travel');
      assert.equal(resolveBrand('vietnam_safar').id, 'vietnam_safar');
      assert.equal(resolveBrand('vietnam-safar').id, 'vietnam_safar');
      assert.equal(resolveBrand('selvara').id, 'selvara');
      assert.equal(resolveBrand('selvara-journeys').id, 'selvara');
    });

    it('resolves brand from hostname header', () => {
      assert.equal(resolveBrand(null, 'journeys.capellatravel.com').id, 'capella_travel');
      assert.equal(resolveBrand(null, 'quote.capellatravel.com:8115').id, 'capella_travel');
      assert.equal(resolveBrand(null, 'my.selvarajourneys.com').id, 'selvara');
      assert.equal(resolveBrand(null, 'journeys.vietnamsafar.vn').id, 'vietnam_safar');
    });

    it('resolves brand from ctxData', () => {
      const ctxCapella = { seller_email: 'sales@capellatravel.com', contact_web: 'journeys.capellatravel.com' };
      assert.equal(resolveBrand(null, null, ctxCapella).id, 'capella_travel');

      const ctxSelvara = { seller_email: 'concierge@selvara.com' };
      assert.equal(resolveBrand(null, null, ctxSelvara).id, 'selvara');
    });

    it('falls back to default brand when no params provided', () => {
      assert.equal(resolveBrand().id, 'vietnam_safar');
    });
  });

  describe('transformPdfHtmlWithBrand on quo_f7175e110605ab/pdf.html', () => {
    const pdfPath = path.resolve(
      __dirname,
      '..',
      '..',
      'public',
      'published',
      'quo_f7175e110605ab',
      'pdf.html'
    );

    it('transforms Vietnam Safar PDF into Capella Travel with 100% parity', () => {
      assert.ok(fs.existsSync(pdfPath), 'pdf.html must exist for quo_f7175e110605ab');
      const originalHtml = fs.readFileSync(pdfPath, 'utf-8');

      // Original has Vietnam Safar elements
      assert.ok(originalHtml.includes('--primary: #17412e;'));
      assert.ok(originalHtml.includes('/assets/brands/vietnam_safar.png'));
      assert.ok(originalHtml.includes('Vietnam Safar — Travel Proposal'));

      // Transform to Capella Travel
      const transformed = transformPdfHtmlWithBrand(originalHtml, 'capella_travel');

      // Check CSS Variables
      assert.ok(transformed.includes('--primary: #CBA135;'), 'Must contain Capella primary color');
      assert.ok(transformed.includes('--primary-dark: #B7894B;'), 'Must contain Capella primary dark color');
      assert.ok(transformed.includes('--accent: #333333;'), 'Must contain Capella accent color');
      assert.ok(transformed.includes('--accent-light: #4F4F4F;'), 'Must contain Capella accent light color');

      // Check Logo
      assert.ok(transformed.includes('/assets/brands/capella_travel.png'), 'Must contain Capella logo');
      assert.ok(!transformed.includes('/assets/brands/vietnam_safar.png'), 'Must NOT contain old Vietnam Safar logo');

      // Check Headers, Footers and Watermarks
      assert.ok(transformed.includes('Capella Travel — Travel Proposal'), 'Must contain Capella header text');
      assert.ok(transformed.includes('Capella Travel · VN-2027-LUX'), 'Must contain Capella watermark');
      assert.ok(!transformed.includes('Vietnam Safar — Travel Proposal'), 'Must NOT contain old Vietnam Safar header');
      assert.ok(!transformed.includes('Vietnam Safar · VN-2027-LUX'), 'Must NOT contain old Vietnam Safar watermark');
    });

    it('transforms Vietnam Safar PDF into Selvara Journeys', () => {
      const originalHtml = fs.readFileSync(pdfPath, 'utf-8');
      const transformed = transformPdfHtmlWithBrand(originalHtml, 'selvara');

      assert.ok(transformed.includes('--primary: #A98338;'));
      assert.ok(transformed.includes('/assets/brands/selvara.svg'));
      assert.ok(transformed.includes('Selvara Journeys — Travel Proposal'));
      assert.ok(!transformed.includes('/assets/brands/vietnam_safar.png'));
    });
  });
});
