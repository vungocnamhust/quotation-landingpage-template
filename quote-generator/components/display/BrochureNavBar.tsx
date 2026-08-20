'use client';

import Image from 'next/image';
import { useEffect, useState } from 'react';
import type { NavViewModel, TypographySlotMap } from '../../display/types.ts';
import { textValue } from '../../display/types.ts';
import { requireTypographySlot } from '../../display/typographySlots.ts';
import { cn } from '../../utils/cn.ts';
import { ActionButton, DisplayTitle, MetaText, TextLink, editableProps } from './atoms.tsx';

interface BrochureNavBarProps {
  viewModel: NavViewModel;
  typography: TypographySlotMap;
}

export default function BrochureNavBar({
  viewModel,
  typography,
}: BrochureNavBarProps) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [copiedType, setCopiedType] = useState<string | null>(null);

  useEffect(() => {
    const syncScrolled = () => {
      setIsScrolled(window.scrollY > 32);
    };

    syncScrolled();
    window.addEventListener('scroll', syncScrolled, { passive: true });
    return () => {
      window.removeEventListener('scroll', syncScrolled);
    };
  }, []);

  return (
    <div className={cn('display-nav-shell', isScrolled && 'is-scrolled')}>
      <div className="display-nav__inner">
        <div className="display-nav__brand">
          {viewModel.brandLogoSrc ? (
            <div className="display-nav__logo-mark">
              <Image
                src={viewModel.brandLogoSrc}
                alt={textValue(viewModel.brandLogoAlt ?? viewModel.brandName)}
                {...editableProps(viewModel.brandLogoAlt ?? viewModel.brandName)}
                width={44}
                height={44}
                className="display-nav__logo-image"
              />
            </div>
          ) : (
            <span className="display-nav__logo-fallback" aria-hidden="true">
              {textValue(viewModel.brandLogo)}
            </span>
          )}
          <DisplayTitle
            as="h1"
            variant={requireTypographySlot(typography, 'title')}
            className="display-nav__brand-title"
            tone={isScrolled ? 'default' : 'inverse'}
          >
            {viewModel.brandName}
          </DisplayTitle>
        </div>

        <nav className="display-nav__links" aria-label={textValue(viewModel.sectionAriaLabel)} {...(viewModel.sectionAriaLabel && typeof viewModel.sectionAriaLabel !== 'string' ? { 'data-editable': viewModel.sectionAriaLabel.path, 'data-edit-owner': viewModel.sectionAriaLabel.owner, 'data-edit-mode': viewModel.sectionAriaLabel.mode } : {})}>
          {viewModel.links.map((link) => (
            <TextLink
              key={link.href}
              href={link.href}
              typographyVariant={requireTypographySlot(typography, 'link')}
              className={cn('display-nav__link', isScrolled && 'is-scrolled')}
            >
              {link.label}
            </TextLink>
          ))}
        </nav>

        <div className="display-nav__actions">
          <div className="display-nav__secondary-actions">
            {viewModel.secondaryActions?.map((action) =>
              action.href ? (
                <a key={action.type} href={action.href} className="display-nav__secondary-action">
                  <span>{textValue(action.label)}</span>
                </a>
              ) : (
                <button
                  key={action.type}
                  type="button"
                  onClick={async () => {
                    if (typeof navigator !== 'undefined' && navigator.clipboard) {
                      try {
                        await navigator.clipboard.writeText(window.location.href);
                        setCopiedType(action.type);
                        setTimeout(() => setCopiedType(null), 2000);
                      } catch {
                        // clipboard unsupported or denied
                      }
                    }
                  }}
                  className="display-nav__secondary-action"
                  aria-label={textValue(action.label)}
                >
                  <span>{copiedType === action.type ? '✓ Link Copied' : textValue(action.label)}</span>
                </button>
              )
            )}
          </div>
          <div className="display-nav__primary-actions">
            {viewModel.actions.map((action) => (
              <ActionButton
                key={textValue(action.label)}
                href={action.href}
                colorRole={action.emphasis ?? 'primary'}
                typographyVariant={requireTypographySlot(typography, 'action')}
                className="display-nav__primary-action"
              >
                {action.label}
              </ActionButton>
            ))}
          </div>
        </div>
      </div>

      <MetaText
        variant={requireTypographySlot(typography, 'metaPrimary')}
        className={cn('display-nav__meta', isScrolled && 'is-scrolled')}
        tone={isScrolled ? 'muted' : 'inverse'}
      >
        {viewModel.themeLabel ?? ''}
      </MetaText>
    </div>
  );
}
