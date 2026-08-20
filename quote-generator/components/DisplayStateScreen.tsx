import Link from 'next/link';
import type { StateSectionId } from '../display/types.ts';
import { BodyCopy, DisplayTitle, Kicker } from './display/atoms.tsx';

const STATE_COPY: Record<StateSectionId, { title: string; body: string; actionLabel?: string }> = {
  loading: { title: 'Loading quotation', body: 'The published quotation is being prepared.' },
  error: { title: 'Unable to load quotation', body: 'Please try again.' , actionLabel: 'Try Again' },
  notFound: { title: 'Quotation not found', body: 'The published quotation link is no longer available.', actionLabel: 'Return Home' },
};

export default function DisplayStateScreen({
  state,
  onAction,
}: {
  state: StateSectionId;
  onAction?: () => void;
}) {
  const viewModel = STATE_COPY[state];

  return (
    <div className="display-state-screen">
      <div className="display-state-screen__card">
        <Kicker variant="chapterKicker">Quotation</Kicker>
          <DisplayTitle as="h2" variant="stateTitle">
          {viewModel.title}
        </DisplayTitle>
        <BodyCopy variant="bodyMd">{viewModel.body}</BodyCopy>
        {state === 'notFound' ? (
          <Link
            href="/?theme=brochure&brand=vietnam-safar&lang=en"
            className="typo-button-primary inline-flex min-h-11 items-center justify-center rounded-[var(--radius-button)] border border-[var(--color-action-primary-border)] bg-[var(--color-action-primary-surface)] px-5 py-3 !text-[var(--color-action-primary-text)] shadow-[0_14px_32px_var(--color-shadow)]"
          >
          {viewModel.actionLabel}
          </Link>
        ) : viewModel.actionLabel ? (
          <button
            type="button"
            className="typo-button-primary inline-flex min-h-11 items-center justify-center rounded-[var(--radius-button)] border border-[var(--color-action-primary-border)] bg-[var(--color-action-primary-surface)] px-5 py-3 !text-[var(--color-action-primary-text)] shadow-[0_14px_32px_var(--color-shadow)]"
            onClick={onAction}
          >
              {viewModel.actionLabel}
          </button>
        ) : null}
      </div>
    </div>
  );
}
