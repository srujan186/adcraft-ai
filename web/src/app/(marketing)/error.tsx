"use client";
import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface it for whatever error reporting gets wired up later.
    console.error("Route error:", error);
  }, [error]);

  return (
    <div className="state-page">
      <div>
        <p className="state-code">Oops</p>
        <h1 className="h2" style={{ marginBottom: "0.75rem" }}>Something broke</h1>
        <p className="lead" style={{ maxWidth: 440, margin: "0 auto" }}>
          This page hit an unexpected error. Trying again often clears it.
        </p>
        {error.digest && (
          <p className="hint" style={{ marginTop: "1rem" }}>
            Reference: <code className="code-inline">{error.digest}</code>
          </p>
        )}
        <div className="state-actions">
          <button className="btn btn-primary" onClick={reset}>Try again</button>
          <Link href="/" className="btn btn-secondary">Back to home</Link>
        </div>
      </div>
    </div>
  );
}
