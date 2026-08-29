import { useEffect } from 'react'

const BASE = 'Proof'

/** Sets the document title for the current page, restoring the base on unmount. */
export function usePageTitle(title: string): void {
  useEffect(() => {
    document.title = title ? `${title} · Proof` : BASE
    return () => {
      document.title = BASE
    }
  }, [title])
}
