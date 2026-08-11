'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getTypographyClassName } from '../../config/typography';
import { cn } from '../../utils/cn';
import {
  createTravelDesigner,
  listTravelDesigners,
  setTravelDesignerDefault,
  updateTravelDesigner,
  updateTravelDesignerStatus,
  uploadTravelDesignerPortrait,
  type TravelDesignerInput,
  type TravelDesignerProfile,
} from '../../lib/quotationApi';

type Props = {
  value: string | null;
  brandId: string | null;
  disabled?: boolean;
  onChange: (profileId: string | null, profile?: TravelDesignerProfile) => void;
};

type DrawerMode = 'create' | 'edit' | 'manage' | null;

const blankDraft = (): TravelDesignerInput => ({ name: '', email: '', phone: '', imageAssetId: null, imageUrl: null, imageR2Key: null });

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'TD';
}

function ProfileAvatar({ profile }: { profile: Pick<TravelDesignerProfile, 'name' | 'imageUrl'> }) {
  return profile.imageUrl ? (
    // The image URL is a previously validated media asset or migration fallback.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={profile.imageUrl} alt="" className="h-10 w-10 rounded-full border border-[var(--color-border)] object-cover" />
  ) : (
    <span aria-hidden="true" className={cn(getTypographyClassName('caption'), 'inline-flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-on-surface)]')}>{initials(profile.name)}</span>
  );
}

function FormField({
  label,
  value,
  type = 'text',
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  type?: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return <label className="flex flex-col gap-2"><span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>{label}</span><input type={type} value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} className={cn(getTypographyClassName('bodyMd'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:opacity-60')} /></label>;
}

export default function TravelDesignerPicker({ value, brandId, disabled = false, onChange }: Props) {
  const [profiles, setProfiles] = useState<TravelDesignerProfile[]>([]);
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<DrawerMode>(null);
  const [editing, setEditing] = useState<TravelDesignerProfile | null>(null);
  const [draft, setDraft] = useState<TravelDesignerInput>(blankDraft);
  const [portraitFile, setPortraitFile] = useState<File | null>(null);
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);

  const loadProfiles = useCallback(async (query = search) => {
    setPending(true);
    try {
      const response = await listTravelDesigners({ active: drawerMode === 'manage' ? 'all' : 'true', search: query });
      setProfiles(response.items);
      setMessage('');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Travel Designers could not be loaded.');
    } finally {
      setPending(false);
    }
  }, [drawerMode, search]);

  useEffect(() => {
    // A persisted quotation supplies only the profile id. Load that profile
    // even while the drawer is closed so the selector can render its current
    // identity instead of a misleading "Select Travel Designer" placeholder.
    if (!open && drawerMode !== 'manage' && !value) return;
    const timer = window.setTimeout(() => { void loadProfiles(search); }, search ? 180 : 0);
    return () => window.clearTimeout(timer);
  }, [drawerMode, loadProfiles, open, search, value]);

  const selected = useMemo(() => profiles.find((profile) => profile.id === value) ?? null, [profiles, value]);
  const setDraftField = <K extends keyof TravelDesignerInput>(key: K, next: TravelDesignerInput[K]) => setDraft((current) => ({ ...current, [key]: next }));

  function openCreate() {
    setEditing(null);
    setDraft(blankDraft());
    setPortraitFile(null);
    setDrawerMode('create');
    setMessage('');
  }

  function openEdit(profile: TravelDesignerProfile) {
    setEditing(profile);
    setDraft({ name: profile.name, email: profile.email, phone: profile.phone, imageAssetId: profile.imageAssetId ?? null, imageUrl: profile.imageUrl ?? null, imageR2Key: profile.imageR2Key ?? null });
    setPortraitFile(null);
    setDrawerMode('edit');
    setMessage('');
  }

  async function saveProfile() {
    if (!draft.name.trim() || !draft.email.trim()) {
      setMessage('Name and email are required.');
      return;
    }
    setPending(true);
    try {
      let saved = editing ? await updateTravelDesigner(editing.id, draft) : await createTravelDesigner(draft);
      if (portraitFile) {
        const uploaded = await uploadTravelDesignerPortrait(portraitFile, saved.id);
        saved = await updateTravelDesigner(saved.id, { ...draft, imageR2Key: uploaded.r2Key });
      }
      setProfiles((current) => [saved, ...current.filter((profile) => profile.id !== saved.id)]);
      onChange(saved.id);
      setDrawerMode(null);
      setOpen(false);
      setMessage('');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Travel Designer could not be saved.');
    } finally {
      setPending(false);
    }
  }

  async function toggleStatus(profile: TravelDesignerProfile) {
    setPending(true);
    try {
      const saved = await updateTravelDesignerStatus(profile.id, !profile.isActive);
      setProfiles((current) => current.map((item) => item.id === saved.id ? saved : item));
      if (!saved.isActive && value === saved.id) onChange(null);
      setMessage('');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Travel Designer status could not be changed.');
    } finally {
      setPending(false);
    }
  }

  async function makeDefault(profile: TravelDesignerProfile) {
    if (!brandId) {
      setMessage('Choose a brand before setting its default designer.');
      return;
    }
    setPending(true);
    try {
      await setTravelDesignerDefault(brandId, profile.id);
      setMessage(`${profile.name} is now the default for this brand.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Brand default could not be saved.');
    } finally {
      setPending(false);
    }
  }

  return <div className="flex flex-col gap-2">
    <span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>Travel designer</span>
    <div className="flex flex-wrap gap-2">
      <button type="button" disabled={disabled} onClick={() => setOpen((current) => !current)} aria-expanded={open} className={cn(getTypographyClassName('bodyMd'), 'flex min-h-11 min-w-[16rem] flex-1 items-center gap-3 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-left text-[var(--color-on-surface)] disabled:opacity-60')}>
        {selected ? <><ProfileAvatar profile={selected} /><span className="min-w-0"><span className="block truncate">{selected.name}</span><span className={cn(getTypographyClassName('caption'), 'block truncate text-[var(--color-muted)]')}>{selected.email}</span></span></> : <span className="text-[var(--color-muted)]">Select Travel Designer</span>}
      </button>
      {!disabled ? <button type="button" onClick={openCreate} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all')}>Add new</button> : null}
    </div>
    {open ? <div role="presentation" className="fixed inset-0 z-50 flex justify-end bg-[color-mix(in_srgb,var(--color-contrast)_35%,transparent)]"><section role="dialog" aria-modal="true" aria-label="Select Travel Designer" className="h-full w-full max-w-xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6"><div className="mb-5 flex items-start justify-between gap-4"><div><h2 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>Select Travel Designer</h2><p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>Selecting a profile fills the quotation identity, phone, email and portrait.</p></div><button type="button" onClick={() => setOpen(false)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3.5 transition-all')}>Close</button></div>
      <div className="flex gap-2"><input value={search} onChange={(event) => setSearch(event.target.value)} autoFocus placeholder="Search name or email" className={cn(getTypographyClassName('bodyMd'), 'min-h-11 min-w-0 flex-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]')} /><button type="button" onClick={() => setDrawerMode('manage')} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3.5 transition-all')}>Manage</button></div>
      <div role="listbox" aria-label="Travel Designers" className="mt-3 flex max-h-64 flex-col gap-1 overflow-y-auto">{profiles.filter((profile) => profile.isActive).map((profile) => <button key={profile.id} type="button" role="option" aria-selected={profile.id === value} onClick={() => { onChange(profile.id, profile); setOpen(false); }} className="flex min-h-14 items-center gap-3 rounded-[var(--radius-button)] px-2 text-left hover:bg-[var(--color-surface-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"><ProfileAvatar profile={profile} /><span className="min-w-0"><span className={cn(getTypographyClassName('bodyMd'), 'block truncate text-[var(--color-on-surface)]')}>{profile.name}</span><span className={cn(getTypographyClassName('caption'), 'block truncate text-[var(--color-muted)]')}>{profile.email}{profile.phone ? ` · ${profile.phone}` : ''}</span></span></button>)}{!pending && !profiles.filter((profile) => profile.isActive).length ? <p className={cn(getTypographyClassName('bodySm'), 'p-2 text-[var(--color-muted)]')}>No Travel Designer matches this search.</p> : null}</div>
      <div className="mt-3 flex gap-2"><button type="button" onClick={() => onChange(null)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3.5 transition-all')}>Clear selection</button><button type="button" onClick={openCreate} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 shadow-xs border border-transparent transition-all')}>Add designer</button></div>
    </section></div> : null}
    {message && drawerMode === null ? <p aria-live="polite" className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>{message}</p> : null}
    {drawerMode ? <div role="dialog" aria-modal="true" aria-label={drawerMode === 'manage' ? 'Manage Travel Designers' : 'Travel Designer profile'} className="fixed inset-0 z-50 flex justify-end bg-[color-mix(in_srgb,var(--color-contrast)_35%,transparent)]"><div className="h-full w-full max-w-xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6"><div className="flex items-start justify-between gap-4"><div><h2 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>{drawerMode === 'manage' ? 'Manage Travel Designers' : editing ? 'Edit Travel Designer' : 'Add Travel Designer'}</h2><p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>{drawerMode === 'manage' ? 'Profiles are deactivated instead of deleted.' : 'This profile can be selected for future quotations.'}</p></div><button type="button" onClick={() => setDrawerMode(null)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3.5 transition-all')}>Close</button></div>
      {drawerMode === 'manage' ? <div className="mt-6 flex flex-col gap-3">{profiles.map((profile) => <article key={profile.id} className="flex flex-wrap items-center gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-3 shadow-2xs"><ProfileAvatar profile={profile} /><div className="min-w-0 flex-1"><p className={cn(getTypographyClassName('bodyMd'), 'truncate text-[var(--color-on-surface)]')}>{profile.name}</p><p className={cn(getTypographyClassName('caption'), 'truncate text-[var(--color-muted)]')}>{profile.email} · {profile.isActive ? 'Active' : 'Inactive'}</p></div><button type="button" disabled={pending} onClick={() => openEdit(profile)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all')}>Edit</button><button type="button" disabled={pending} onClick={() => void toggleStatus(profile)} className={cn(getTypographyClassName('buttonSecondary'), profile.isActive ? 'min-h-10 rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3 shadow-2xs border border-transparent transition-all' : 'min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3 shadow-2xs border border-transparent transition-all')}>{profile.isActive ? 'Deactivate' : 'Reactivate'}</button>{profile.isActive ? <button type="button" disabled={pending || !brandId} onClick={() => void makeDefault(profile)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all')}>Set default</button> : null}</article>)}</div> : <div className="mt-6 grid gap-4"><FormField label="Name" value={draft.name} onChange={(next) => setDraftField('name', next)} disabled={pending} /><FormField label="Email" type="email" value={draft.email} onChange={(next) => setDraftField('email', next)} disabled={pending} /><FormField label="Phone" value={draft.phone} onChange={(next) => setDraftField('phone', next)} disabled={pending} /><label className="flex flex-col gap-2"><span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>Portrait</span><input type="file" accept="image/*" disabled={pending} onChange={(event) => setPortraitFile(event.target.files?.[0] ?? null)} className={cn(getTypographyClassName('bodySm'), 'min-h-11 text-[var(--color-on-surface)]')} /><span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>{portraitFile?.name || (draft.imageUrl ? 'Current portrait kept until replaced.' : 'Optional shared media portrait.')}</span></label><div className="flex flex-wrap gap-3"><button type="button" disabled={pending} onClick={() => void saveProfile()} className={cn(getTypographyClassName('buttonPrimary'), 'min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50')}>{pending ? 'Saving…' : 'Save designer'}</button><button type="button" disabled={pending} onClick={() => setDrawerMode(null)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all')}>Cancel</button></div></div>}
      {message ? <p aria-live="polite" className={cn(getTypographyClassName('bodySm'), 'mt-4 text-[var(--color-muted)]')}>{message}</p> : null}
    </div></div> : null}
  </div>;
}
