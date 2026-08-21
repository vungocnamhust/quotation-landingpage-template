import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  chunkItineraryDaysForPdf,
  chunkHotelsForPdf,
} from '../rules/pdfRules.ts';

describe('PDF A4 Pagination Chunking Algorithms', () => {
  describe('chunkItineraryDaysForPdf', () => {
    it('returns empty array when days array is empty', () => {
      assert.deepEqual(chunkItineraryDaysForPdf([]), []);
    });

    it('returns single page with 1 day when 1 day provided', () => {
      const days = ['Day 1'];
      assert.deepEqual(chunkItineraryDaysForPdf(days), [['Day 1']]);
    });

    it('returns single page with 2 days when 2 days provided', () => {
      const days = ['Day 1', 'Day 2'];
      assert.deepEqual(chunkItineraryDaysForPdf(days), [['Day 1', 'Day 2']]);
    });

    it('splits into chunks of 2 for multiple days', () => {
      const days = ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'];
      const chunks = chunkItineraryDaysForPdf(days);
      assert.equal(chunks.length, 3);
      assert.deepEqual(chunks[0], ['Day 1', 'Day 2']);
      assert.deepEqual(chunks[1], ['Day 3', 'Day 4']);
      assert.deepEqual(chunks[2], ['Day 5']);
    });
  });

  describe('chunkHotelsForPdf', () => {
    it('returns empty array for 0 hotels', () => {
      assert.deepEqual(chunkHotelsForPdf([]), [[]]);
    });

    it('keeps 1 to 4 hotels on a single page A4', () => {
      assert.deepEqual(chunkHotelsForPdf(['H1']), [['H1']]);
      assert.deepEqual(chunkHotelsForPdf(['H1', 'H2']), [['H1', 'H2']]);
      assert.deepEqual(chunkHotelsForPdf(['H1', 'H2', 'H3']), [['H1', 'H2', 'H3']]);
      assert.deepEqual(chunkHotelsForPdf(['H1', 'H2', 'H3', 'H4']), [['H1', 'H2', 'H3', 'H4']]);
    });

    it('splits 5 hotels into 3 on page 1 and 2 on page 2 (never 4+1)', () => {
      const hotels = ['H1', 'H2', 'H3', 'H4', 'H5'];
      const chunks = chunkHotelsForPdf(hotels);
      assert.equal(chunks.length, 2);
      assert.deepEqual(chunks[0], ['H1', 'H2', 'H3']);
      assert.deepEqual(chunks[1], ['H4', 'H5']);
    });

    it('splits 6 hotels into 3 on page 1 and 3 on page 2', () => {
      const hotels = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'];
      const chunks = chunkHotelsForPdf(hotels);
      assert.equal(chunks.length, 2);
      assert.deepEqual(chunks[0], ['H1', 'H2', 'H3']);
      assert.deepEqual(chunks[1], ['H4', 'H5', 'H6']);
    });

    it('splits 7 hotels into 4 and 3', () => {
      const hotels = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7'];
      const chunks = chunkHotelsForPdf(hotels);
      assert.equal(chunks.length, 2);
      assert.deepEqual(chunks[0], ['H1', 'H2', 'H3', 'H4']);
      assert.deepEqual(chunks[1], ['H5', 'H6', 'H7']);
    });

    it('splits 8 hotels into 4 and 4', () => {
      const hotels = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8'];
      const chunks = chunkHotelsForPdf(hotels);
      assert.equal(chunks.length, 2);
      assert.deepEqual(chunks[0], ['H1', 'H2', 'H3', 'H4']);
      assert.deepEqual(chunks[1], ['H5', 'H6', 'H7', 'H8']);
    });
  });
});
