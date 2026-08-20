export * from './sectionHelpers.tsx';
export * from './NavSection.tsx';
export * from './HeroSection.tsx';
export * from './OpenLetterSection.tsx';
export * from './RouteMapSection.tsx';
export * from './ItineraryDividerSection.tsx';
export * from './ItinerarySection.tsx';
export * from './HotelsSection.tsx';
export * from './StaysDividerSection.tsx';
export * from './PricingSection.tsx';
export * from './InclusionsExclusionsSection.tsx';
export * from './PaymentTermsSection.tsx';
export * from './DesignerSection.tsx';
export * from './FooterSection.tsx';

import { NavSection } from './NavSection.tsx';
import { HeroSection } from './HeroSection.tsx';
import { OpenLetterSection } from './OpenLetterSection.tsx';
import { RouteMapSection } from './RouteMapSection.tsx';
import { ItineraryDividerSection } from './ItineraryDividerSection.tsx';
import { ItinerarySection } from './ItinerarySection.tsx';
import { HotelsSection } from './HotelsSection.tsx';
import { StaysDividerSection } from './StaysDividerSection.tsx';
import { PricingSection } from './PricingSection.tsx';
import { InclusionsExclusionsSection } from './InclusionsExclusionsSection.tsx';
import { PaymentTermsSection } from './PaymentTermsSection.tsx';
import { DesignerSection } from './DesignerSection.tsx';
import { FooterSection } from './FooterSection.tsx';

export const sectionRegistry = {
  nav: NavSection,
  hero: HeroSection,
  letter: OpenLetterSection,
  routeMap: RouteMapSection,
  itineraryDivider: ItineraryDividerSection,
  itinerary: ItinerarySection,
  hotels: HotelsSection,
  staysDivider: StaysDividerSection,
  pricing: PricingSection,
  inclusionsExclusions: InclusionsExclusionsSection,
  paymentTerms: PaymentTermsSection,
  designer: DesignerSection,
  footer: FooterSection,
};
