import test from 'node:test';
import assert from 'node:assert/strict';

import { BRANDS_DATA } from '../../data/brandsData.ts';
import { buildDisplayDocumentFromQuoteDocument } from '../../display/runtimePageBuilder.ts';
import { textValue } from '../../display/types.ts';

const brand = BRANDS_DATA['vietnam-safar'];

function build(document: Record<string, unknown>) {
  return buildDisplayDocumentFromQuoteDocument({
    document,
    brandProfile: {
      id: 'vietnam_safar',
      displayName: brand.name,
      hostname: 'quotation.test',
      logoUrl: '/assets/brands/vietnam_safar.png',
      themeId: 'brochure',
      layoutVersion: 1,
      palette: brand.themeTokens.palette,
      radii: brand.themeTokens.radii,
    },
    lang: 'en',
    viewMode: 'desktop',
  });
}

test('applied overview copy remains Content-owned even when customer facts disagree', () => {
  const model = build({
    customer: { greetingName: 'Dear Facts', partyLabel: 'Facts party' },
    narrative: {
      letterHighlight: 'Applied AI highlight',
      letterGreeting: 'Dear Applied Guest,',
      letterIntro: 'Applied introduction.',
      letterBody2: 'Applied body.',
      letterOutro: 'Applied outro.',
      letterSignOff: 'Warm regards,',
      letterSender: 'Applied Journey Team',
    },
  });

  assert.equal(textValue(model.page.letter.highlight), 'Applied AI highlight');
  assert.equal(textValue(model.page.letter.greeting), 'Dear Applied Guest,');
  assert.equal(textValue(model.page.letter.signOff), 'Warm regards,');
  assert.equal(textValue(model.page.letter.sender), 'Applied Journey Team');
});

test('route map consumes the applied canonical stay segment description', () => {
  const model = build({
    itinerary: {
      days: [{ dayNumber: 1, segmentCity: 'Hanoi', overnight: 'Hanoi', title: 'Derived title' }],
    },
    route: {
      staySegments: [{
        id: 'stay-1',
        dayStart: 1,
        dayEnd: 1,
        mapSegmentDesc: 'Applied route copy',
      }],
    },
  });

  assert.equal(model.page.routeMap.segments.length, 1);
  assert.equal(textValue(model.page.routeMap.segments[0].description), 'Applied route copy');
});

test('itinerary highlights label respects display i18n without leaking legacy fact strings', () => {
  const doc = {
    itinerary: {
      days: [{
        dayNumber: 1,
        segmentCity: 'Hanoi',
        overnight: 'Hanoi',
        title: 'Arrival in Hanoi',
        activities: ['Old Quarter Walk', 'Street Food Tour'],
        labelHighlights: 'Highlights:',
      }],
    },
  };

  const modelEn = buildDisplayDocumentFromQuoteDocument({
    document: doc,
    brandProfile: {
      id: 'vietnam_safar',
      displayName: brand.name,
      hostname: 'quotation.test',
      logoUrl: '/assets/brands/vietnam_safar.png',
      themeId: 'brochure',
      layoutVersion: 1,
      palette: brand.themeTokens.palette,
      radii: brand.themeTokens.radii,
    },
    lang: 'en',
    viewMode: 'desktop',
  });

  const modelVi = buildDisplayDocumentFromQuoteDocument({
    document: doc,
    brandProfile: {
      id: 'vietnam_safar',
      displayName: brand.name,
      hostname: 'quotation.test',
      logoUrl: '/assets/brands/vietnam_safar.png',
      themeId: 'brochure',
      layoutVersion: 1,
      palette: brand.themeTokens.palette,
      radii: brand.themeTokens.radii,
    },
    lang: 'vi',
    viewMode: 'desktop',
  });

  const dayEn = modelEn.page.itinerary.days[0];
  const dayVi = modelVi.page.itinerary.days[0];

  assert.equal(textValue(dayEn.detailRows[0].label), 'Highlights');
  assert.equal(textValue(dayVi.detailRows[0].label), 'Điểm nhấn');
});

