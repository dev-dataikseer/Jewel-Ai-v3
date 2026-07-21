import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  fallback?: ReactNode;
  /** Zone label shown in the default fallback (e.g. "Workflows", "Inspector"). */
  label?: string;
};
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`UI error${this.props.label ? ` [${this.props.label}]` : ""}:`, error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <div className="mx-auto max-w-lg p-6 text-center rounded-xl border border-rose-200 bg-rose-50/80">
            <h2 className="text-sm font-semibold text-slate-800">
              {this.props.label ? `${this.props.label} failed to load` : "Something went wrong"}
            </h2>
            <p className="mt-2 text-xs text-slate-500">
              {typeof this.state.error.message === "string"
                ? this.state.error.message
                : "An unexpected UI error occurred."}
            </p>
            <button
              type="button"
              className="mt-3 rounded-lg ui-btn-primary px-3 py-1.5 text-xs font-semibold"
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
