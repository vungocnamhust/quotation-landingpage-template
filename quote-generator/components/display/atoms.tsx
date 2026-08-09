import Image from 'next/image';
import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import type { TypographyVariant } from '../../config/typography';
import type { ComponentColorRole, TextValue } from '../../display/types';
import { textValue } from '../../display/types';
import { getTypographyClassName } from '../../config/typography';
import { cn } from '../../utils/cn';

function toneClassName(tone: 'default' | 'muted' | 'accent' | 'inverse' = 'default') {
  return tone === 'muted' ? 'text-[var(--color-muted)]' : tone === 'accent' ? 'text-[var(--color-accent)]' : 'text-[var(--color-on-surface)]';
}

export function editableProps(value: TextValue) {
  if (typeof value === 'string') return {};
  return { 'data-editable': value.path, 'data-edit-owner': value.owner, 'data-edit-mode': value.mode };
}

interface TypographyAtomProps { children: TextValue; variant: TypographyVariant; className?: string; tone?: 'default' | 'muted' | 'accent' | 'inverse'; }

export function Kicker({ children, variant = 'chapterKicker', className, tone = 'accent' }: TypographyAtomProps) {
  return <div className={cn(getTypographyClassName(variant), toneClassName(tone), 'inline-flex items-center gap-2', className)} {...editableProps(children)}>{textValue(children)}</div>;
}

interface DisplayTitleProps extends TypographyAtomProps { as?: 'h1' | 'h2' | 'h3' | 'h4' | 'span'; }
export function DisplayTitle({ as: Tag = 'h2', children, variant, className, tone = 'default' }: DisplayTitleProps) {
  return <Tag className={cn(getTypographyClassName(variant), toneClassName(tone), className)} {...editableProps(children)}>{textValue(children)}</Tag>;
}
export function BodyCopy({ children, variant, className, tone = 'muted' }: TypographyAtomProps) {
  return <p className={cn(getTypographyClassName(variant), toneClassName(tone), className)} {...editableProps(children)}>{textValue(children)}</p>;
}
export function MetaText({ children, variant, className, tone = 'muted' }: TypographyAtomProps) {
  return <div className={cn(getTypographyClassName(variant), toneClassName(tone), className)} {...editableProps(children)}>{textValue(children)}</div>;
}
export function PriceText({ children, variant = 'investmentValue', className, tone = 'accent' }: TypographyAtomProps) {
  return <div className={cn(getTypographyClassName(variant), toneClassName(tone), className)} {...editableProps(children)}>{textValue(children)}</div>;
}
export function LabelText({ children, variant = 'label', className, tone = 'accent' }: Omit<TypographyAtomProps, 'variant'> & { variant?: TypographyVariant }) {
  return <div className={cn(getTypographyClassName(variant), toneClassName(tone), className)} {...editableProps(children)}>{textValue(children)}</div>;
}
function isTextValue(value: unknown): value is TextValue {
  return typeof value === 'string' || (typeof value === 'object' && value !== null && 'value' in value && 'path' in value && 'owner' in value && 'mode' in value);
}

export function QuoteText({ children, variant = 'quote', className, tone = 'default' }: Omit<TypographyAtomProps, 'children'> & { children: TextValue | ReactNode }) {
  return <blockquote className={cn(getTypographyClassName(variant), toneClassName(tone), className)} {...(isTextValue(children) ? editableProps(children) : {})}>{isTextValue(children) ? textValue(children) : children}</blockquote>;
}

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn('inline-flex items-center gap-2 rounded-[var(--radius-pill)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1.5 text-[var(--color-accent)]', className)}>{children}</span>;
}
export function Tag({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn('inline-flex items-center rounded-[var(--radius-pill)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-[var(--color-muted)]', className)}>{children}</span>;
}
export function IconChip({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn('inline-flex min-h-11 min-w-11 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm', className)}>{children}</span>;
}

export function ActionButton({ children, className, colorRole = 'primary', typographyVariant = 'buttonPrimary', ...props }: Omit<ComponentPropsWithoutRef<'a'>, 'children'> & { children: TextValue; colorRole?: ComponentColorRole; typographyVariant?: TypographyVariant }) {
  return <a className={cn(getTypographyClassName(typographyVariant), 'inline-flex items-center justify-center gap-2 px-[1.188rem] py-[0.813rem] transition-all duration-200 hover:-translate-y-0.5', colorRole === 'primary' ? 'rounded-none border border-[var(--color-action-primary-border)] bg-[var(--color-action-primary-surface)] !text-[var(--color-action-primary-text)] shadow-[0_8px_24px_color-mix(in_srgb,var(--color-contrast)_15%,transparent)]' : 'rounded-none border border-[var(--color-action-secondary-border)] bg-[var(--color-action-secondary-surface)] !text-[var(--color-action-secondary-text)]', className)} {...editableProps(children)} {...props}>{textValue(children)}</a>;
}
export function TextLink({ children, className, typographyVariant, colorRole = 'secondary', ...props }: Omit<ComponentPropsWithoutRef<'a'>, 'children'> & { children: TextValue; typographyVariant: TypographyVariant; colorRole?: Extract<ComponentColorRole, 'primary' | 'secondary'> }) {
  return <a className={cn(getTypographyClassName(typographyVariant), colorRole === 'primary' ? 'text-[var(--color-action-primary-text)] underline-offset-4 transition-colors hover:underline' : 'text-[var(--color-action-secondary-text)] underline-offset-4 transition-colors hover:text-[var(--color-accent)] hover:underline', className)} {...editableProps(children)} {...props}>{textValue(children)}</a>;
}

interface ImageFrameProps { src: string; alt: TextValue; className?: string; sizes?: string; priority?: boolean; variant?: 'card' | 'editorial'; }
export function ImageFrame({ src, alt, className, sizes = '(min-width: 1024px) 50vw, 100vw', priority = false, variant = 'card' }: ImageFrameProps) {
  const hasValidSrc = typeof src === 'string' && src.trim() !== '';
  return <div className={cn('relative overflow-hidden bg-[var(--color-surface)]', variant === 'card' ? 'rounded-[var(--radius-frame)] border border-[var(--color-border)] shadow-[0_14px_32px_var(--color-shadow)]' : 'border-0 shadow-none', className)}>{hasValidSrc ? <Image src={src} alt={textValue(alt)} {...editableProps(alt)} fill sizes={sizes} priority={priority} className="object-cover" /> : null}</div>;
}
export function AvatarFrame({ src, alt, className, variant = 'card' }: { src: string; alt: TextValue; className?: string; variant?: 'card' | 'editorial' }) {
  const hasValidSrc = typeof src === 'string' && src.trim() !== '';
  return <div className={cn('relative aspect-[3/4] overflow-hidden bg-[var(--color-surface)]', variant === 'card' ? 'rounded-t-[8rem] rounded-b-[1.5rem] border-4 border-[var(--color-surface)] shadow-[0_14px_32px_var(--color-shadow)]' : 'rounded-t-[12.5rem] rounded-b-none border-4 border-[var(--color-surface)] shadow-[0_14px_32px_var(--color-shadow)]', className)}>{hasValidSrc ? <Image src={src} alt={textValue(alt)} {...editableProps(alt)} fill sizes="(min-width: 1024px) 24vw, 70vw" className="object-cover" /> : null}</div>;
}
export function DividerArt({ className }: { className?: string }) { return <div className={cn('display-divider-art', className)} aria-hidden="true" />; }
export function SectionShell({ className, children }: { className?: string; children: ReactNode }) { return <div className={className}>{children}</div>; }
