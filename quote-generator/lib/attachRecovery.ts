export const ATTACH_RECOVERY_PARAMS = {
  sheetId: "attachSheet",
  idempotencyKey: "attachKey",
} as const;

export type AttachRecovery = {
  sheetId: string;
  idempotencyKey: string;
};

/**
 * Recovery is intentionally opt-in: a partial URL must never issue an attach
 * request with a replacement idempotency key.
 */
export function readAttachRecovery(params: URLSearchParams): AttachRecovery | null {
  const sheetId = params.get(ATTACH_RECOVERY_PARAMS.sheetId);
  const idempotencyKey = params.get(ATTACH_RECOVERY_PARAMS.idempotencyKey);
  return sheetId && idempotencyKey ? { sheetId, idempotencyKey } : null;
}

export function clearAttachRecovery(params: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(params.toString());
  next.delete(ATTACH_RECOVERY_PARAMS.sheetId);
  next.delete(ATTACH_RECOVERY_PARAMS.idempotencyKey);
  return next;
}
