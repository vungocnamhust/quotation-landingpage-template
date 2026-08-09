/**
 * Production display boundary.
 *
 * Static brochure fixtures deliberately live in `pageBuilderFixtures.ts` and
 * must never be imported by V2 editor, SSR, or PDF code.
 */
export {
  buildDisplayDocumentFromQuoteDocument,
  type DisplayDocument,
} from './runtimePageBuilder';
