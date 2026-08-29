import { Component, type ReactNode } from 'react'

/** Last-resort catch so a render error shows a recovery path, not a blank page. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center px-5">
          <div className="panel w-full max-w-md p-6 text-center">
            <h1 className="font-display text-2xl text-ink-text">Something broke</h1>
            <p className="mt-2 text-sm leading-relaxed text-ink-muted">
              {this.state.error.message || 'An unexpected error interrupted the page.'}
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-5 inline-flex rounded-[3px] bg-ink-text px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-white"
            >
              Reload the app
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
