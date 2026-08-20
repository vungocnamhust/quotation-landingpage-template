import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  partyReconciler,
  generatePartyLabel,
  inferGreetingName,
  normalizeKidAges,
  updateKidAgeVector,
  calculateMinEstimatedRooms,
  generateRoomSuggestions,
  createDefaultParty,
  type CanonicalParty,
} from '../rules/partyReconciler.ts';

describe('partyReconciler pure domain rules', () => {
  describe('Pax counts & kidAges vector invariants', () => {
    it('setAdults clamps adults >= 1 and updates party label & room suggestions', () => {
      const party = createDefaultParty('John Doe');
      const updated = partyReconciler.setAdults(party, 4);

      assert.equal(updated.adults, 4);
      assert.equal(updated.partyLabel, 'John Doe & Party (4 Adults)');
      assert.equal(updated.minEstimatedRooms, 2);
      assert.ok(updated.roomSuggestions?.some((s) => s.includes('Double Rooms')));

      // Test clamp
      const clamped = partyReconciler.setAdults(party, 0);
      assert.equal(clamped.adults, 1);
    });

    it('setChildren resizes kidAges vector deterministically with default age 6', () => {
      let party = createDefaultParty('The Smiths');
      assert.equal(party.children, 0);
      assert.deepEqual(party.kidAges, []);

      // Increase to 2 children -> pads with default age 6
      party = partyReconciler.setChildren(party, 2);
      assert.equal(party.children, 2);
      assert.deepEqual(party.kidAges, [6, 6]);
      assert.equal(party.partyLabel, 'The Smiths & Party (2 Adults, 2 Children)');

      // Set age of child 1 to 14, child 2 to 9
      party = partyReconciler.setKidAge(party, 0, 14);
      party = partyReconciler.setKidAge(party, 1, 9);
      assert.deepEqual(party.kidAges, [14, 9]);

      // Increase to 3 children -> preserves existing ages, appends 6 for child 3
      party = partyReconciler.setChildren(party, 3);
      assert.equal(party.children, 3);
      assert.deepEqual(party.kidAges, [14, 9, 6]);

      // Shrink to 1 child -> truncates to [14]
      party = partyReconciler.setChildren(party, 1);
      assert.equal(party.children, 1);
      assert.deepEqual(party.kidAges, [14]);
    });

    it('setKidAge clamps age between 0 and 17', () => {
      let party = createDefaultParty('Family');
      party = partyReconciler.setChildren(party, 2);

      party = partyReconciler.setKidAge(party, 0, 25); // Over 17 -> clamped to 17
      party = partyReconciler.setKidAge(party, 1, -5); // Under 0 -> clamped to 0

      assert.deepEqual(party.kidAges, [17, 0]);
    });

    it('normalizeKidAges and updateKidAgeVector handle padding, clamping, and out-of-bound inputs', () => {
      // 1. Padding with default age 6
      const padded = normalizeKidAges([], 3);
      assert.deepEqual(padded, [6, 6, 6]);

      // 2. Truncation and age clamping
      const clamped = normalizeKidAges([4, 25, -2], 2);
      assert.deepEqual(clamped, [4, 17]);

      // 3. Updating specific index
      const updated = updateKidAgeVector([6, 6], 2, 1, '12');
      assert.deepEqual(updated, [6, 12]);

      // 4. Updating out-of-bound index is safely ignored
      const ignored = updateKidAgeVector([6, 6], 2, 5, '10');
      assert.deepEqual(ignored, [6, 6]);
    });
  });

  describe('Party label & greeting name multilingual generation', () => {
    it('generates English party labels correctly', () => {
      assert.equal(generatePartyLabel(1, 0, 'Alice', 'en'), 'Alice & Party (1 Adult)');
      assert.equal(generatePartyLabel(2, 0, 'Mr. Smith', 'en'), 'Mr. Smith & Party (2 Adults)');
      assert.equal(generatePartyLabel(2, 1, 'The Vance Family', 'en'), 'The Vance Family & Party (2 Adults, 1 Child)');
      assert.equal(generatePartyLabel(2, 3, 'Johnson', 'en'), 'Johnson & Party (2 Adults, 3 Children)');
      assert.equal(generatePartyLabel(2, 0, '', 'en'), '2 Adults');
    });

    it('generates Vietnamese party labels correctly', () => {
      assert.equal(generatePartyLabel(2, 0, 'Gia đình Bác An', 'vi'), 'Gia đình Bác An & Đoàn (2 Người lớn)');
      assert.equal(generatePartyLabel(2, 2, 'Anh Hùng', 'vi'), 'Anh Hùng & Đoàn (2 Người lớn, 2 Trẻ em)');
    });

    it('generates Arabic party labels correctly', () => {
      const label = generatePartyLabel(2, 1, 'عائلة السالم', 'ar');
      assert.ok(label.includes('2 بالغين'));
      assert.ok(label.includes('1 طفل'));
    });

    it('infers greeting name with language-aware prefixes', () => {
      // English
      assert.equal(inferGreetingName('John Smith', 'en'), 'Dear John Smith');
      assert.equal(inferGreetingName('Dear John Smith', 'en'), 'Dear John Smith'); // No double Dear

      // Vietnamese
      assert.equal(inferGreetingName('Nguyễn Văn A', 'vi'), 'Kính gửi Nguyễn Văn A');
      assert.equal(inferGreetingName('Kính gửi Chú Ba', 'vi'), 'Kính gửi Chú Ba');

      // Arabic
      assert.equal(inferGreetingName('محمد', 'ar'), 'عزيزي محمد');
    });

    it('preserves user custom party label and greeting name during customerName updates', () => {
      let party = createDefaultParty('John');
      assert.equal(party.partyLabel, 'John & Party (2 Adults)');

      // User sets custom label
      party = partyReconciler.setPartyLabel(party, 'VIP Delegations Only');
      assert.equal(party.isPartyLabelCustom, true);

      // Change name -> custom label is preserved!
      party = partyReconciler.setCustomerName(party, 'Jonathan Doe');
      assert.equal(party.partyLabel, 'VIP Delegations Only');
    });
  });

  describe('Dynamic room suggestions & capacity heuristics', () => {
    it('suggests single rooms for solo traveler', () => {
      const evalSolo = generateRoomSuggestions(1, 0, [], 'en');
      assert.equal(evalSolo.matchedRuleId, 'rule_solo_traveler');
      assert.equal(evalSolo.minEstimatedRooms, 1);
      assert.ok(evalSolo.suggestions.includes('1 Single Room'));
    });

    it('suggests double/twin for couple without kids', () => {
      const evalCouple = generateRoomSuggestions(2, 0, [], 'en');
      assert.equal(evalCouple.matchedRuleId, 'rule_couple_no_kids');
      assert.equal(evalCouple.minEstimatedRooms, 1);
      assert.ok(evalCouple.suggestions.includes('1 Double (King Bed)'));
    });

    it('suggests extra bed / family suite for young kids (< 12)', () => {
      const evalYoung = generateRoomSuggestions(2, 2, [6, 8], 'en');
      assert.equal(evalYoung.matchedRuleId, 'rule_family_young_kids');
      assert.ok(evalYoung.suggestions.includes('1 Double Room + Extra Bed'));
    });

    it('suggests connecting / interconnecting rooms for teen kids (>= 12)', () => {
      const evalTeen = generateRoomSuggestions(2, 2, [14, 10], 'en');
      assert.equal(evalTeen.matchedRuleId, 'rule_family_teen_kids');
      assert.equal(evalTeen.minEstimatedRooms, 2);
      assert.ok(evalTeen.suggestions.includes('2 Interconnecting Rooms'));
    });

    it('scales room suggestions for large groups (6 adults)', () => {
      const evalGroup = generateRoomSuggestions(6, 0, [], 'en');
      assert.equal(evalGroup.matchedRuleId, 'rule_quad_adults');
      assert.equal(evalGroup.minEstimatedRooms, 3);
      assert.ok(evalGroup.suggestions.includes('3 Double Rooms'));
      assert.ok(evalGroup.suggestions.includes('3 Twin Rooms'));
    });

    it('calculateMinEstimatedRooms evaluates formula and default capacities', () => {
      assert.equal(calculateMinEstimatedRooms(1, 0, '1'), 1);
      assert.equal(calculateMinEstimatedRooms(4, 0, 'ceil(adults / 2)'), 2);
      assert.equal(calculateMinEstimatedRooms(2, 2), 2);
    });
  });

  describe('reconcileParty invariant healing', () => {
    it('normalizes invalid or missing fields in one pass', () => {
      const broken: Partial<CanonicalParty> = {
        customerName: ' Dr. Robert ',
        adults: -1, // invalid
        children: 3,
        kidAges: [8], // mismatched length
      };

      const healed = partyReconciler.reconcileParty(broken);
      assert.equal(healed.customerName, 'Dr. Robert');
      assert.equal(healed.adults, 1); // clamped
      assert.equal(healed.children, 3);
      assert.deepEqual(healed.kidAges, [8, 6, 6]); // resized & padded with 6
      assert.equal(healed.partyLabel, 'Dr. Robert & Party (1 Adult, 3 Children)');
      assert.equal(healed.greetingName, 'Dear Dr. Robert');
    });
  });
});
