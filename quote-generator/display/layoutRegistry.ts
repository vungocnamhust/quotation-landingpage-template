import type {
  LayoutVariantDefinition,
  LayoutVariantId,
  ShellVariantDefinition,
  ShellVariantId,
} from './types.ts';
import type { ViewMode } from './contracts.ts';
import { cn } from '../utils/cn.ts';

export const shellRegistry: Record<ShellVariantId, ShellVariantDefinition> = {
  'shell-none': {
    id: 'shell-none',
    className: 'display-shell display-shell--none',
  },
  'shell-indochine-soft': {
    id: 'shell-indochine-soft',
    className: 'display-shell display-shell--soft',
  },
  'shell-indochine-frame': {
    id: 'shell-indochine-frame',
    className: 'display-shell display-shell--frame',
  },
  'shell-editorial-strip': {
    id: 'shell-editorial-strip',
    className: 'display-shell display-shell--editorial-strip',
  },
  'shell-full-bleed': {
    id: 'shell-full-bleed',
    className: 'display-shell display-shell--full-bleed',
  },
  'shell-pdf-page': {
    id: 'shell-pdf-page',
    className: 'display-shell display-shell--pdf-page',
  },
  'shell-pdf-page-framed': {
    id: 'shell-pdf-page-framed',
    className: 'display-shell display-shell--pdf-page-framed',
  },
};

export const layoutRegistry: Record<LayoutVariantId, LayoutVariantDefinition> = {
  'hero-cover': {
    id: 'hero-cover',
    slots: {
      section: 'relative overflow-hidden min-h-screen',
      container:
        'mx-auto flex min-h-screen w-full max-w-[1180px] flex-col justify-center px-5 pt-28 pb-16 sm:px-8 lg:px-12 lg:pt-32 lg:pb-20',
      content: 'relative z-10 flex max-w-[760px] flex-col gap-6 text-left',
      footer: 'relative z-10 mt-10',
      overlay: 'absolute inset-0',
    },
    responsive: {
      mobile: {
        container:
          'mx-auto flex min-h-[100svh] w-full flex-col justify-center px-5 pt-24 pb-16',
        content: 'relative z-10 flex max-w-none flex-col gap-5 text-left',
      },
      pdf: {
        container:
          'mx-auto flex min-h-[10.8in] w-full flex-col justify-end px-10 pb-10 pt-12',
      },
    },
  },
  'centered-stack': {
    id: 'centered-stack',
    slots: {
      section: 'relative',
      container: 'mx-auto flex w-full max-w-[1180px] flex-col px-5 py-16 sm:px-8 lg:px-12',
      header: 'mx-auto flex max-w-[42rem] flex-col items-center gap-4 text-center',
      content: 'mx-auto mt-8 w-full max-w-[56rem]',
    },
    responsive: {
      pdf: {
        container: 'mx-auto flex w-full px-8 py-8',
      },
    },
  },
  'editorial-split-55-45': {
    id: 'editorial-split-55-45',
    slots: {
      section: 'relative',
      container:
        'mx-auto grid w-full max-w-[1180px] grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[55%_1fr] lg:gap-[8%] lg:px-12',
      content: 'flex flex-col gap-6',
      media: 'flex flex-col gap-5',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-8 px-5 py-14',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-[55%_1fr] gap-8 px-8 py-8',
      },
    },
  },
  'editorial-split-50-50': {
    id: 'editorial-split-50-50',
    slots: {
      section: 'relative',
      container:
        'mx-auto grid w-full max-w-[1180px] grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-2 lg:gap-12 lg:px-12',
      content: 'flex flex-col gap-6',
      media: 'flex flex-col gap-5',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-8 px-5 py-14',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-2 gap-8 px-8 py-8',
      },
    },
  },
  'timeline-with-sidebar': {
    id: 'timeline-with-sidebar',
    slots: {
      section: 'relative',
      container:
        'mx-auto grid w-full max-w-[1180px] grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-start lg:gap-14 lg:px-12',
      aside: 'flex flex-col gap-5',
      content: 'flex flex-col gap-6',
      items: 'grid gap-5',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-8 px-5 py-14',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-[0.8fr_1.2fr] gap-8 px-8 py-8',
      },
    },
  },
  'day-story-grid': {
    id: 'day-story-grid',
    slots: {
      section: 'relative',
      container: 'mx-auto flex w-full max-w-[1180px] flex-col gap-10 px-5 pb-16 pt-[90px] sm:px-8 lg:px-12',
      header: 'flex max-w-[820px] flex-col gap-4',
      items: 'grid gap-16',
    },
    responsive: {
      mobile: {
        container: 'mx-auto flex w-full gap-8 px-5 py-14',
        items: 'grid gap-12',
      },
      pdf: {
        container: 'mx-auto flex w-full gap-8 px-8 py-8',
        items: 'grid gap-8',
      },
    },
  },
  'hotel-editorial-odd-even': {
    id: 'hotel-editorial-odd-even',
    slots: {
      section: 'relative',
      container: 'mx-auto flex w-full max-w-[1180px] flex-col gap-10 px-5 py-16 sm:px-8 lg:px-12',
      header: 'grid gap-4 lg:grid-cols-1',
      items: 'grid gap-14',
    },
    responsive: {
      mobile: {
        container: 'mx-auto flex w-full gap-8 px-5 py-14',
        items: 'grid gap-10',
      },
      pdf: {
        container: 'mx-auto flex w-full gap-8 px-8 py-8',
        items: 'grid gap-8',
      },
    },
  },
  'full-bleed-divider': {
    id: 'full-bleed-divider',
    slots: {
      section: 'relative overflow-hidden',
      container:
        'mx-auto flex min-h-[60vh] w-full max-w-[1180px] items-end px-5 py-16 sm:px-8 lg:px-12',
      content: 'relative z-10 flex max-w-[680px] flex-col gap-5',
      overlay: 'absolute inset-0',
    },
    responsive: {
      mobile: {
        container: 'mx-auto flex min-h-[26rem] w-full items-end px-5 py-12',
      },
      pdf: {
        container: 'mx-auto flex min-h-[10.8in] w-full items-end px-10 py-10',
      },
    },
  },
  'pricing-ledger': {
    id: 'pricing-ledger',
    slots: {
      section: 'relative',
      container:
        'mx-auto grid w-full max-w-[1180px] grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:gap-14 lg:px-12',
      aside: 'flex flex-col gap-5',
      content: 'grid gap-4',
      footer: 'mt-6',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-8 px-5 py-14',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-[0.75fr_1.25fr] gap-8 px-8 py-8',
      },
    },
  },
  'two-column-panel': {
    id: 'two-column-panel',
    slots: {
      section: 'relative',
      container:
        'mx-auto grid w-full max-w-[1180px] grid-cols-1 gap-8 px-5 py-16 sm:px-8 lg:grid-cols-2 lg:gap-10 lg:px-12',
      content: 'flex flex-col gap-5',
      aside: 'flex flex-col gap-5',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-6 px-5 py-14',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-2 gap-8 px-8 py-8',
      },
    },
  },
  'term-rows': {
    id: 'term-rows',
    slots: {
      section: 'relative',
      container:
        'mx-auto grid w-full max-w-[1180px] grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[1fr_1.5fr] lg:gap-[clamp(40px,6vw,80px)] lg:px-12',
      aside: 'flex flex-col gap-5',
      content: 'grid gap-0',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-8 px-5 py-14',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-[0.9fr_1.1fr] gap-8 px-8 py-8',
      },
    },
  },
  'profile-split': {
    id: 'profile-split',
    slots: {
      section: 'relative',
      container:
        'mx-auto grid w-full max-w-[1180px] grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.78fr_1.22fr] lg:gap-14 lg:px-12',
      aside: 'flex flex-col gap-5',
      content: 'flex flex-col gap-6',
      footer: 'grid gap-6 pt-6 lg:grid-cols-2',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-8 px-5 py-14',
        footer: 'grid gap-4 pt-4',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-[0.8fr_1.2fr] gap-8 px-8 py-8',
      },
    },
  },
  'footer-minimal': {
    id: 'footer-minimal',
    slots: {
      section: 'relative',
      container:
        'mx-auto flex w-full max-w-[1180px] flex-col gap-4 px-5 py-8 sm:px-8 lg:px-12',
      content: 'flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between',
    },
    responsive: {
      pdf: {
        container: 'mx-auto flex w-full gap-2 px-8 py-4',
      },
    },
  },
  'nav-overlay-fixed': {
    id: 'nav-overlay-fixed',
    slots: {
      section: 'relative',
      container:
        'mx-auto flex w-full max-w-[1180px] items-center justify-between gap-5 px-5 py-3.5 sm:px-8 lg:px-12',
      content: 'flex items-center gap-5',
      aside: 'flex items-center gap-3',
    },
    responsive: {
      mobile: {
        container: 'mx-auto flex w-full items-center justify-between gap-3 px-4 py-3',
      },
      pdf: {
        container: 'mx-auto flex w-full items-center justify-between gap-4 px-8 py-6',
      },
    },
  },
  'letter-sidebar-220': {
    id: 'letter-sidebar-220',
    slots: {
      section: 'relative',
      container: 'mx-auto flex w-full max-w-[1180px] flex-col px-5 py-16 sm:px-8 lg:px-12',
      header: 'mb-10 flex max-w-[800px] flex-col gap-4',
      content: 'grid grid-cols-1 gap-8 md:grid-cols-[220px_1fr] md:gap-10 md:items-start',
      aside: 'flex flex-col justify-between gap-8',
      media: 'flex flex-col gap-8',
    },
    responsive: {
      mobile: {
        container: 'mx-auto flex w-full px-5 py-14',
        content: 'grid grid-cols-1 gap-7',
        aside: 'flex flex-col gap-6',
      },
      pdf: {
        container: 'mx-auto flex w-full px-8 py-8',
      },
    },
  },
  'route-map-interactive': {
    id: 'route-map-interactive',
    slots: {
      section: 'relative',
      container: 'mx-auto flex w-full max-w-[1180px] flex-col gap-10 px-5 pb-16 pt-24 sm:px-8 sm:pt-28 lg:px-12 lg:pt-32',
      header: 'grid gap-6 lg:grid-cols-[0.6fr_0.4fr] lg:items-start lg:gap-14',
      content: 'w-full',
      media: 'relative min-h-[340px] lg:min-h-[clamp(500px,75vh,800px)]',
      aside: 'relative min-h-0 bg-[var(--color-surface)] lg:max-h-[clamp(500px,75vh,800px)] lg:overflow-y-auto',
      items: 'grid gap-0',
    },
    responsive: {
      mobile: {
        container: 'mx-auto flex w-full flex-col gap-8 px-5 pb-14 pt-20',
        header: 'grid gap-5',
        content: 'w-full',
        media: 'relative min-h-[340px]',
        aside: 'relative min-h-0 bg-[var(--color-surface)]',
        items: 'grid gap-0',
      },
      pdf: {
        container: 'mx-auto flex w-full flex-col gap-6 px-8 py-8',
        header: 'grid gap-4',
        content: 'w-full',
        media: 'relative min-h-[280px]',
        aside: 'relative min-h-0 bg-[var(--color-surface)]',
      },
    },
  },
  'itinerary-day-single': {
    id: 'itinerary-day-single',
    slots: {
      section: 'relative',
      container: 'grid gap-8 lg:grid-cols-[1fr_1.25fr] lg:items-center',
      media: 'order-1',
      content: 'order-2 flex flex-col gap-5 lg:py-10',
    },
    responsive: {
      mobile: {
        container: 'grid gap-6',
        media: 'order-1',
        content: 'order-2 flex flex-col gap-4',
      },
      pdf: {
        container: 'grid gap-6',
      },
    },
  },
  'itinerary-day-multi': {
    id: 'itinerary-day-multi',
    slots: {
      section: 'relative',
      container: 'grid gap-8 lg:grid-cols-[1.15fr_0.85fr]',
      content: 'order-1 flex flex-col gap-5',
      media: 'order-2 flex flex-col gap-6 lg:justify-end',
      items: 'grid gap-6 lg:grid-cols-[2fr_1fr]',
    },
    responsive: {
      mobile: {
        container: 'grid gap-6',
        content: 'order-1 flex flex-col gap-4',
        media: 'order-2 flex flex-col gap-4',
        items: 'grid gap-4',
      },
      pdf: {
        container: 'grid gap-6',
      },
    },
  },
  'stays-editorial-split': {
    id: 'stays-editorial-split',
    slots: {
      section: 'relative overflow-hidden',
      container:
        'mx-auto grid w-full max-w-[1400px] grid-cols-1 gap-12 px-[5%] py-0 lg:grid-cols-[55%_1fr] lg:gap-[8%] lg:pt-20 lg:pb-16',
      media: 'relative',
      content: 'relative z-10 flex flex-col justify-center gap-6 py-5',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-8 px-5 py-10',
        content: 'relative z-10 flex flex-col gap-5 py-0',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-[55%_1fr] gap-8 px-8 py-8',
      },
    },
  },
  'pricing-investment-ledger': {
    id: 'pricing-investment-ledger',
    slots: {
      section: 'relative',
      container: 'mx-auto flex w-full max-w-[1180px] flex-col gap-10 px-5 py-16 sm:px-8 lg:px-12',
      header: 'grid gap-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-end',
      content: 'grid gap-0',
      footer: 'mt-8',
    },
    responsive: {
      mobile: {
        container: 'mx-auto flex w-full gap-8 px-5 py-14',
        header: 'grid gap-4',
      },
      pdf: {
        container: 'mx-auto flex w-full gap-8 px-8 py-8',
      },
    },
  },
  'inclusions-panels': {
    id: 'inclusions-panels',
    slots: {
      section: 'relative',
      container: 'mx-auto flex w-full max-w-[1180px] flex-col gap-8 px-5 py-16 sm:px-8 lg:px-12',
      header: 'grid gap-4',
      content: 'grid gap-6 lg:grid-cols-2',
    },
    responsive: {
      mobile: {
        container: 'mx-auto flex w-full gap-6 px-5 py-14',
        content: 'grid gap-5',
      },
      pdf: {
        container: 'mx-auto flex w-full gap-6 px-8 py-8',
      },
    },
  },
  'designer-editorial-profile': {
    id: 'designer-editorial-profile',
    slots: {
      section: 'relative overflow-hidden',
      container:
        'mx-auto grid w-full max-w-[1100px] grid-cols-1 gap-14 px-5 py-20 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20 lg:px-12',
      aside: 'flex flex-col gap-6',
      content: 'relative flex flex-col gap-6',
      footer: 'grid gap-6 pt-8',
    },
    responsive: {
      mobile: {
        container: 'mx-auto grid w-full grid-cols-1 gap-10 px-5 py-14',
        footer: 'grid gap-5 pt-6',
      },
      pdf: {
        container: 'mx-auto grid w-full grid-cols-[0.8fr_1.2fr] gap-8 px-8 py-8',
      },
    },
  },
};

export function getShellClassName(shellVariant: ShellVariantId) {
  return shellRegistry[shellVariant].className;
}

export function getLayoutSlots(layoutVariant: LayoutVariantId, viewMode: ViewMode) {
  const definition = layoutRegistry[layoutVariant];
  const overrides =
    viewMode === 'mobile'
      ? definition.responsive.mobile
      : viewMode === 'pdf'
        ? definition.responsive.pdf
        : undefined;

  return {
    ...definition.slots,
    ...overrides,
  };
}

export function buildSectionFrameClassName(
  layoutVariant: LayoutVariantId,
  shellVariant: ShellVariantId,
  viewMode: ViewMode,
  extraClassName?: string
) {
  const slots = getLayoutSlots(layoutVariant, viewMode);

  return cn(slots.section, getShellClassName(shellVariant), extraClassName);
}
