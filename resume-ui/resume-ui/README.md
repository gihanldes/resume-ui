# Resume Reviewer — UI

React 19, Vite, TypeScript, Tailwind v4.

```bash
npm install
npm run dev     # http://localhost:5173, proxies /api to 127.0.0.1:8000
npm run build
```

## Design

"Green ink" — editorial-professional, settled after exploring four directions
on the project's design canvas (`design/` holds all artboards; earlier
directions are kept on its second page).

One warm surface (#fbfaf7): no card grid — structure comes from hairline rules
(#e7e4db) and a real type scale. Schibsted Grotesk carries UI and display;
Spline Sans Mono is reserved for data (scores, line numbers, terms). One brand
color, pine green #2a5d46 — Proof means approval — does actions, links and
"pass". Severity is colored glyphs and numerals (critical #b3372b, warning
#9c6b10, suggestions quiet gray), never pills or badges. The score is the
page's focal point: a 64px numeral colored by its band, over a strong rule,
with categories as one inline stat line.

The signature element is the source view: the resume as line-numbered plain
text in a warm well, with each finding's evidence highlighted in place —
selecting a finding lights the exact spans that triggered it.

Beyond the review itself: a public landing page, a score-over-time chart on the
dashboard (inline SVG, single series, hover tooltip, sr-only table), a
"since your last review" delta strip on every result, a print-ready report
route (`/analyses/:id/report` → browser print → PDF), app-wide toasts and a
promise-based confirm dialog (no `window.confirm`), an error boundary, a 404
page, per-route document titles, and account deletion in a danger zone.

## Structure

```
src/
  api/client.ts        fetch wrapper; token storage, single-flight refresh
  auth/AuthContext.tsx session state and server capabilities
  components/
    ProofSheet.tsx     the marked-up document
    Verdict.tsx        score and category meters
    Findings.tsx       filterable findings list
    Panels.tsx         job match, AI review, parser snapshot
    Layout.tsx  ui.tsx
  pages/               SignIn, SignUp, Resumes, RunReview, Result, History, Account
```
