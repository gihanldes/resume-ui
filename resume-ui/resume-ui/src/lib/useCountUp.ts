import { useEffect, useRef, useState } from 'react'

const prefersReduced = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Count from 0 to `target` with an ease-out curve, once per target change. */
export function useCountUp(target: number, duration = 900, delay = 0): number {
  const [value, setValue] = useState(() => (prefersReduced() ? target : 0))
  const frame = useRef(0)

  useEffect(() => {
    if (prefersReduced()) {
      setValue(target)
      return
    }
    let start: number | null = null
    const tick = (now: number) => {
      if (start === null) start = now
      const t = Math.min(1, Math.max(0, (now - start - delay) / duration))
      setValue(target * (1 - Math.pow(1 - t, 3)))
      if (t < 1) frame.current = requestAnimationFrame(tick)
    }
    frame.current = requestAnimationFrame(tick)
    // Hidden tabs pause rAF; make sure the final value always lands anyway.
    const failSafe = setTimeout(() => setValue(target), delay + duration + 800)
    return () => {
      cancelAnimationFrame(frame.current)
      clearTimeout(failSafe)
    }
  }, [target, duration, delay])

  return value
}
