export type ApiErrorKind = 'authentication' | 'authorization' | 'notFound' | 'conflict' | 'validation' | 'network' | 'server';

export class QuotationApiError extends Error {
  constructor(
    public readonly kind: ApiErrorKind,
    public readonly status: number,
    message: string,
    public readonly detail: unknown = null,
  ) {
    super(message);
    this.name = 'QuotationApiError';
  }
}

function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail && typeof detail.message === 'string') return detail.message;
  return fallback;
}

export async function readApiResponse<T>(response: Response, fallback = 'The request could not be completed.'): Promise<T> {
  const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
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
  throw new QuotationApiError(kind, response.status, detailMessage(detail, fallback), detail);
}

export async function quotationFetch<T>(url: string, init?: RequestInit, fallback?: string): Promise<T> {
  try {
    return await readApiResponse<T>(await fetch(url, init), fallback);
  } catch (error) {
    if (error instanceof QuotationApiError) throw error;
    if (error instanceof TypeError) {
      throw new QuotationApiError('network', 0, 'The quotation API is unavailable. Your changes were not saved; retry when the connection is restored.', error);
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
