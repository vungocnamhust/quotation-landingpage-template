export type ApiErrorKind = 'authentication' | 'authorization' | 'notFound' | 'conflict' | 'validation' | 'network' | 'server';

export type ApiFieldError = { path: string; message: string };
export type ApiRecovery = 'retry' | 'reload' | 'sign-in' | 'open-blockers' | null;
export type ApiErrorMetadata = {
  code?: string;
  category?: string;
  fieldErrors?: ApiFieldError[];
  missingInputs?: string[];
  currentRevision?: number;
  review?: unknown;
  retryable?: boolean;
  recovery?: ApiRecovery;
  requestId?: string;
  rateCandidates?: Array<{ rate_id: string; season?: string | null; validity?: { valid_from?: string; valid_to?: string } }>;
};

export class QuotationApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;
  readonly detail: unknown;
  readonly metadata: ApiErrorMetadata;

  constructor(
    kind: ApiErrorKind,
    status: number,
    message: string,
    detail: unknown = null,
    metadata: ApiErrorMetadata = {},
  ) {
    super(message);
    this.name = 'QuotationApiError';
    this.kind = kind;
    this.status = status;
    this.detail = detail;
    this.metadata = metadata;
  }
}

function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail && typeof detail.message === 'string') return detail.message;
  return fallback;
}

function fieldErrors(detail: unknown): ApiFieldError[] {
  const issues = Array.isArray(detail)
    ? detail
    : detail && typeof detail === 'object' && Array.isArray((detail as { errors?: unknown }).errors)
      ? (detail as { errors: unknown[] }).errors
      : [];
  return issues.flatMap((issue) => {
    if (!issue || typeof issue !== 'object') return [];
    const item = issue as { loc?: unknown; msg?: unknown };
    const path = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : '';
    return typeof item.msg === 'string' ? [{ path, message: item.msg }] : [];
  });
}

function metadataFrom(detail: unknown, envelope: unknown, requestId: string | null): ApiErrorMetadata {
  const source = envelope && typeof envelope === 'object' ? envelope as Record<string, unknown> : {};
  const detailRecord = detail && typeof detail === 'object' ? detail as Record<string, unknown> : {};
  const readStringArray = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : undefined;
  const rateCandidates = Array.isArray(detailRecord.candidates)
    ? detailRecord.candidates.filter((item): item is { rate_id: string; season?: string | null; validity?: { valid_from?: string; valid_to?: string } } =>
      Boolean(item) && typeof item === 'object' && typeof (item as { rate_id?: unknown }).rate_id === 'string')
    : undefined;
  const rawFields = Array.isArray(source.fieldErrors) ? source.fieldErrors : undefined;
  return {
    code: typeof source.code === 'string' ? source.code : undefined,
    category: typeof source.category === 'string' ? source.category : undefined,
    fieldErrors: rawFields
      ? rawFields.flatMap((item) => item && typeof item === 'object' && typeof (item as { message?: unknown }).message === 'string'
        ? [{ path: typeof (item as { path?: unknown }).path === 'string' ? (item as { path: string }).path : '', message: (item as { message: string }).message }]
        : [])
      : fieldErrors(detail),
    missingInputs: readStringArray(source.missingInputs) ?? readStringArray(detailRecord.missingInputs),
    currentRevision: typeof source.currentRevision === 'number' ? source.currentRevision : typeof detailRecord.currentRevision === 'number' ? detailRecord.currentRevision : undefined,
    review: source.review ?? detailRecord.review,
    retryable: typeof source.retryable === 'boolean' ? source.retryable : undefined,
    recovery: source.recovery === 'retry' || source.recovery === 'reload' || source.recovery === 'sign-in' || source.recovery === 'open-blockers' ? source.recovery : null,
    requestId: typeof source.requestId === 'string' ? source.requestId : requestId ?? undefined,
    rateCandidates,
  };
}

export async function readApiResponse<T>(response: Response, fallback = 'The request could not be completed.'): Promise<T> {
  const payload = await response.json().catch(() => null) as { detail?: unknown; error?: unknown } | null;
  if (response.ok) return payload as T;
  const detail = payload?.detail;
  const kind: ApiErrorKind = response.status === 401
    ? 'authentication'
    : response.status === 403
      ? 'authorization'
      : response.status === 404
        ? 'notFound'
        : response.status === 409
          ? 'conflict'
          : response.status === 422
            ? 'validation'
            : 'server';
  const metadata = metadataFrom(detail, payload?.error, response.headers.get('x-request-id'));
  const message = payload?.error && typeof payload.error === 'object' && typeof (payload.error as { message?: unknown }).message === 'string'
    ? (payload.error as { message: string }).message
    : detailMessage(detail, fallback);
  throw new QuotationApiError(kind, response.status, message, detail, metadata);
}

export async function quotationFetch<T>(url: string, init?: RequestInit, fallback?: string): Promise<T> {
  try {
    return await readApiResponse<T>(await fetch(url, init), fallback);
  } catch (error) {
    if (error instanceof QuotationApiError) throw error;
    if (error instanceof TypeError) {
      throw new QuotationApiError('network', 0, 'The quotation API is unavailable. Your changes were not saved; retry when the connection is restored.', error, { code: 'NETWORK_UNAVAILABLE', category: 'network', retryable: true, recovery: 'retry' });
    }
    throw error;
  }
}

export function apiErrorMessage(error: unknown): string {
  if (!(error instanceof QuotationApiError)) return error instanceof Error ? error.message : 'The request could not be completed.';
  if (error.kind === 'authentication') return 'Your editor session has expired. Sign in through Cloudflare Access, then retry.';
  if (error.kind === 'authorization') return 'Your account does not have permission for this quotation action.';
  if (error.kind === 'notFound') return 'API endpoint or resource not found (404). Check API URL configuration or route availability.';
  if (error.kind === 'conflict') return 'This quotation changed in another session. Reload the latest revision before retrying.';
  if (error.kind === 'validation') return error.message;
  if (error.kind === 'network') return error.message;
  return error.message;
}

export function apiErrorFieldErrors(error: unknown): ApiFieldError[] {
  return error instanceof QuotationApiError ? error.metadata.fieldErrors ?? [] : [];
}
