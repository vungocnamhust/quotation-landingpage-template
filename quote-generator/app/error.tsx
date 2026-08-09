'use client';

import { useEffect } from 'react';
import DisplayStateScreen from '../components/DisplayStateScreen';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('App Router Error:', error);
  }, [error]);

  return <DisplayStateScreen state="error" onAction={reset} />;
}
