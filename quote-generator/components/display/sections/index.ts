export * from './sectionHelpers';
export * from './NavSection';
export * from './HeroSection';
export * from './OpenLetterSection';
export * from './RouteMapSection';
export * from './ItineraryDividerSection';
export * from './ItinerarySection';
export * from './HotelsSection';
export * from './StaysDividerSection';
export * from './PricingSection';
export * from './InclusionsExclusionsSection';
export * from './PaymentTermsSection';
export * from './DesignerSection';
export * from './FooterSection';

import { NavSection } from './NavSection';
import { HeroSection } from './HeroSection';
import { OpenLetterSection } from './OpenLetterSection';
import { RouteMapSection } from './RouteMapSection';
import { ItineraryDividerSection } from './ItineraryDividerSection';
import { ItinerarySection } from './ItinerarySection';
import { HotelsSection } from './HotelsSection';
import { StaysDividerSection } from './StaysDividerSection';
import { PricingSection } from './PricingSection';
import { InclusionsExclusionsSection } from './InclusionsExclusionsSection';
import { PaymentTermsSection } from './PaymentTermsSection';
import { DesignerSection } from './DesignerSection';
import { FooterSection } from './FooterSection';

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
