import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode; fallback?: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("UI error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <div className="mx-auto max-w-lg p-8 text-center">
            <h2 className="text-lg font-semibold text-slate-800">Something went wrong</h2>
            <p className="mt-2 text-sm text-slate-500">
              {typeof this.state.error.message === "string"
                ? this.state.error.message
                : "An unexpected UI error occurred."}
            </p>
            <button
              type="button"
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white"
              onClick={() => this.setState({ error: null })}
            >
              Try again
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
