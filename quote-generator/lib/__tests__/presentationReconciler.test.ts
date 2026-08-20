import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  presentationReconciler,
  resolveEffectivePresentationValue,
  setOverride,
  removeOverride,
  resolveAllPresentationValues,
} from '../rules/presentationReconciler.ts';
import { presentationAdapter } from '../rules/presentationAdapter.ts';

describe('presentationReconciler 3-tier precedence rules', () => {
  it('exposes facade object with all expected domain functions', () => {
    assert.equal(typeof presentationReconciler.resolveEffectivePresentationValue, 'function');
    assert.equal(typeof presentationReconciler.setOverride, 'function');
    assert.equal(typeof presentationReconciler.removeOverride, 'function');
    assert.equal(typeof presentationReconciler.resolveAllPresentationValues, 'function');
  });

  it('prioritizes Design Override above Content and Fact values', () => {
    const result = resolveEffectivePresentationValue(
      'hero.title',
      'Fact Baseline Title',
      'Content Studio AI Title',
      'Designer Custom Override Title',
      'Default Strategy Title'
    );

    assert.equal(result.value, 'Designer Custom Override Title');
    assert.equal(result.isOverridden, true);
    assert.equal(result.source, 'override');
  });

  it('prioritizes Applied Content when Design Override is absent', () => {
    const result = resolveEffectivePresentationValue(
      'hero.title',
      'Fact Baseline Title',
      'Content Studio AI Title',
      null,
      'Default Strategy Title'
    );

    assert.equal(result.value, 'Content Studio AI Title');
    assert.equal(result.isOverridden, false);
    assert.equal(result.source, 'content');
  });

  it('falls back to Fact Baseline when Design Override and Content are absent', () => {
    const result = resolveEffectivePresentationValue(
      'customer.greetingName',
      'Dear Mr. Wayne',
      null,
      undefined,
      'Dear Guest'
    );

    assert.equal(result.value, 'Dear Mr. Wayne');
    assert.equal(result.isOverridden, false);
    assert.equal(result.source, 'fact');
  });

  it('falls back to Default Strategy when all other values are absent or empty', () => {
    const result = resolveEffectivePresentationValue(
      'nav.routeMap',
      '',
      null,
      undefined,
      'Route Map'
    );

    assert.equal(result.value, 'Route Map');
    assert.equal(result.isOverridden, false);
    assert.equal(result.source, 'default');
  });

  it('treats whitespace-only overrides as non-overridden and cascades down', () => {
    const result = resolveEffectivePresentationValue(
      'hero.title',
      'Fact Baseline Title',
      'Content Studio AI Title',
      '   ',
      'Default Strategy Title'
    );

    assert.equal(result.value, 'Content Studio AI Title');
    assert.equal(result.isOverridden, false);
    assert.equal(result.source, 'content');
  });

  describe('Immutable override management', () => {
    it('setOverride adds or updates key without mutating original dictionary', () => {
      const initial = { 'hero.primaryCta': 'Book Journey' };
      const updated = setOverride(initial, 'nav.routeMap', 'Our Route');

      assert.equal(updated['nav.routeMap'], 'Our Route');
      assert.equal(updated['hero.primaryCta'], 'Book Journey');
      assert.equal(initial['nav.routeMap'], undefined); // Original immutable!
    });

    it('setOverride with empty or null string automatically removes override', () => {
      const initial = { 'hero.primaryCta': 'Book Journey', 'nav.routeMap': 'Our Route' };
      const cleaned = setOverride(initial, 'nav.routeMap', '');

      assert.equal(cleaned['nav.routeMap'], undefined);
      assert.equal(cleaned['hero.primaryCta'], 'Book Journey');
    });

    it('removeOverride removes target key without mutating original dictionary', () => {
      const initial = { 'hero.primaryCta': 'Book Journey', 'nav.routeMap': 'Our Route' };
      const result = removeOverride(initial, 'hero.primaryCta');

      assert.equal(result['hero.primaryCta'], undefined);
      assert.equal(result['nav.routeMap'], 'Our Route');
      assert.equal(initial['hero.primaryCta'], 'Book Journey'); // Immutable
    });

    it('resolveAllPresentationValues processes batch of fields in single pass', () => {
      const batch = [
        { fieldId: 'field_1', designOverride: 'Overridden Value' },
        { fieldId: 'field_2', contentValue: 'Content Value' },
        { fieldId: 'field_3', factValue: 'Fact Value' },
        { fieldId: 'field_4', defaultValue: 'Default Value' },
      ];

      const resolved = resolveAllPresentationValues(batch);
      assert.equal(resolved.field_1.source, 'override');
      assert.equal(resolved.field_2.source, 'content');
      assert.equal(resolved.field_3.source, 'fact');
      assert.equal(resolved.field_4.source, 'default');
    });
  });
});

describe('presentationAdapter bidirectional mapping', () => {
  it('extracts CanonicalPresentationState from document', () => {
    const doc = {
      presentation: {
        themeId: 'brochure',
        layoutVersion: 1,
        renderer: 'v2',
        copyOverrides: { 'nav.routeMap': 'Custom Route' },
        identityOverrides: { seller_subtitle: 'Luxury Specialist' },
      },
    };

    const state = presentationAdapter.fromDocument(doc);
    assert.equal(state.themeId, 'brochure');
    assert.equal(state.copyOverrides['nav.routeMap'], 'Custom Route');
    assert.equal(state.identityOverrides.seller_subtitle, 'Luxury Specialist');
  });

  it('syncs CanonicalPresentationState back to document without losing other sections', () => {
    const prevDoc = {
      trip: { title: 'Vietnam Journey' },
      presentation: { themeId: 'brochure', layoutVersion: 1 },
    };

    const state = {
      themeId: 'brochure',
      layoutVersion: 1,
      renderer: 'v2',
      copyOverrides: { 'hero.primaryCta': 'Explore' },
      identityOverrides: {},
    };

    const synced = presentationAdapter.syncToDocument(state, prevDoc);
    assert.equal((synced.trip as Record<string, unknown>).title, 'Vietnam Journey');
    assert.deepEqual(
      (synced.presentation as Record<string, unknown>).copyOverrides,
      { 'hero.primaryCta': 'Explore' }
    );
  });

  it('creates override payload with baseRevision', () => {
    const payload = presentationAdapter.createOverridePayload(5, { 'nav.title': 'Nav' });
    assert.equal(payload.baseRevision, 5);
    assert.deepEqual(payload.copyOverrides, { 'nav.title': 'Nav' });
  });

  it('separates overrides into copyOverrides vs identityOverrides', () => {
    const overrides = {
      'nav.routeMap': 'Our Route',
      'identity.seller_subtitle': 'Indochina Curator',
    };

    const separated = presentationAdapter.separateOverrides(overrides);
    assert.deepEqual(separated.copyOverrides, { 'nav.routeMap': 'Our Route' });
    assert.deepEqual(separated.identityOverrides, { seller_subtitle: 'Indochina Curator' });
  });
});
