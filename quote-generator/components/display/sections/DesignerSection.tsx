import type { DesignerViewModel } from '../../../display/types';
import { textValue } from '../../../display/types';
import { getLayoutSlots } from '../../../display/layoutRegistry';
import { requireTypographySlot } from '../../../display/typographySlots';
import { getTypographyClassName } from '../../../config/typography';
import { cn } from '../../../utils/cn';
import { BodyCopy, QuoteText } from '../atoms';
import { ActionGroup, DesignerPortraitRail, SectionHeader, SupportBlock } from '../molecules';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers';

export function DesignerSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
  workspaceCanvas = false,
}: BaseSectionProps<DesignerViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="designer" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <aside className={slots.aside}>
          <DesignerPortraitRail item={viewModel} typography={displayConfig.typographySlots} />
        </aside>

        <div className={cn(slots.content, 'display-designer__content')}>
          <div className="display-designer__divider" aria-hidden="true" />
          <SectionHeader
            kicker={viewModel.kicker}
            title={viewModel.title}
            typography={displayConfig.typographySlots}
          />
          <QuoteText variant={requireTypographySlot(displayConfig.typographySlots, 'quote')}>
            {viewModel.quote}
          </QuoteText>
          {viewModel.ctaBody && textValue(viewModel.ctaBody) ? (
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>
              {viewModel.ctaBody}
            </BodyCopy>
          ) : workspaceCanvas ? (
            <button
              type="button"
              data-editable="/designer/ctaBody"
              data-edit-owner="fact"
              data-edit-mode="richText"
              data-workspace-editor-value=""
              className={cn(
                getTypographyClassName(requireTypographySlot(displayConfig.typographySlots, 'body')),
                'w-fit rounded-[var(--radius-button)] border border-dashed border-[var(--color-border-strong)] px-3 py-2 text-[var(--color-muted)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-on-surface)]',
              )}
            >
              Add supporting CTA message
            </button>
          ) : null}
          <ActionGroup actions={viewModel.contactActions} typography={displayConfig.typographySlots} />
          {viewModel.supportBlocks.length > 0 ? (
            <div className={slots.footer}>
              {viewModel.supportBlocks.map((block) => (
                <SupportBlock key={textValue(block.title)} block={block} typography={displayConfig.typographySlots} />
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
