import { NextResponse } from 'next/server';
import { BRAND_PREFERENCE_KEY, DEFAULT_BRAND_KEY, isBrandKey } from '../../../data/brandsData';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const value = url.searchParams.get('value');
  const redirect = url.searchParams.get('redirect') || `/?theme=brochure&brand=${DEFAULT_BRAND_KEY}&lang=en`;
  const brandKey = isBrandKey(value) ? value : DEFAULT_BRAND_KEY;
  const response = NextResponse.redirect(new URL(redirect, request.url));

  response.cookies.set(BRAND_PREFERENCE_KEY, brandKey, {
    path: '/',
    maxAge: 60 * 60 * 24 * 365,
    sameSite: 'lax',
  });

  return response;
}
