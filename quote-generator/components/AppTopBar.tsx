'use client';

import Image from 'next/image';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { NavViewModel, TypographySlotMap } from '../display/types';
import { textValue } from '../display/types';
import { getTypographyClassName } from '../config/typography';
import { requireTypographySlot } from '../display/typographySlots';
import { ActionButton, DisplayTitle, TextLink } from './display/atoms';

/** Public brochure navigation. Tooling actions deliberately do not belong here. */
export default function AppTopBar({
  viewModel,
  typography,
}: {
  viewModel: NavViewModel;
  typography: TypographySlotMap;
}) {
  const [isScrolled, setIsScrolled] = useState(false);
  const searchParams = useSearchParams();
  const currentLang = searchParams?.get('lang') ?? 'en';
  const languageOptions = viewModel.languageOptions ?? [];
  const activeOption = languageOptions.find((option) => option.code === currentLang) ?? languageOptions[0];

  useEffect(() => {
    const syncScrolled = () => setIsScrolled(window.scrollY > 32);
    syncScrolled();
    window.addEventListener('scroll', syncScrolled, { passive: true });
    return () => window.removeEventListener('scroll', syncScrolled);
  }, []);

  return (
    <header className={`display-nav-shell${isScrolled ? ' is-scrolled' : ''}`}>
      <div className="display-nav__inner">
        <a href="#hero" className="display-nav__brand">
          {viewModel.brandLogoSrc ? (
            <Image
              src={viewModel.brandLogoSrc}
              alt={textValue(viewModel.brandLogoAlt ?? viewModel.brandName)}
              width={44}
              height={44}
              className="display-nav__logo-image"
            />
          ) : (
            <span className="display-nav__logo-fallback">{textValue(viewModel.brandLogo)}</span>
          )}
          <DisplayTitle as="span" variant={requireTypographySlot(typography, 'title')} className="display-nav__brand-title">
            {viewModel.brandName}
          </DisplayTitle>
        </a>

        <nav className="display-nav__links" aria-label={textValue(viewModel.sectionAriaLabel)} data-editable={typeof viewModel.sectionAriaLabel === 'string' ? undefined : viewModel.sectionAriaLabel?.path} data-edit-owner={typeof viewModel.sectionAriaLabel === 'string' ? undefined : viewModel.sectionAriaLabel?.owner} data-edit-mode="ariaLabel">
          {viewModel.links.map((link) => (
            <TextLink
              key={link.href}
              href={link.href}
              typographyVariant={requireTypographySlot(typography, 'link')}
              className={`display-nav__link${isScrolled ? ' is-scrolled' : ''}`}
            >
              {link.label}
            </TextLink>
          ))}
        </nav>

        <div className="display-nav__actions">
          <details className="display-nav__language">
            <summary className={getTypographyClassName('topbarSelectValue')}>
              <span className="display-nav__language-label">{textValue(activeOption?.label).toUpperCase()}</span> <span aria-hidden="true">▾</span>
            </summary>
            <ul className="display-nav__language-menu">
              {languageOptions.map((option) => (
                <li key={option.code}>
                  <a href={`?lang=${option.code}`} className={getTypographyClassName('topbarSelectValue')}>
                    <span data-editable={typeof option.label === 'string' ? undefined : option.label.path} data-edit-owner={typeof option.label === 'string' ? undefined : option.label.owner} data-edit-mode="actionLabel">{textValue(option.label)}</span>
                  </a>
                </li>
              ))}
            </ul>
          </details>
          {viewModel.actions.map((action) => (
            <ActionButton
              key={textValue(action.label)}
              href={action.href}
              colorRole={action.emphasis ?? 'primary'}
              typographyVariant={requireTypographySlot(typography, 'action')}
              className="display-nav__primary-action"
            >{action.label}</ActionButton>
          ))}
        </div>
      </div>
    </header>
  );
}
