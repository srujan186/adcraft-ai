import Link from "next/link";

export default function NotFound() {
  return (
    <div className="state-page">
      <div>
        <p className="state-code">404</p>
        <h1 className="h2" style={{ marginBottom: "0.75rem" }}>Page not found</h1>
        <p className="lead" style={{ maxWidth: 420, margin: "0 auto" }}>
          That link doesn&apos;t point anywhere. It may have moved, or never existed.
        </p>
        <div className="state-actions">
          <Link href="/" className="btn btn-primary">Back to home</Link>
          <Link href="/generate" className="btn btn-secondary">Create an ad</Link>
          <Link href="/resources/help" className="btn btn-secondary">Help centre</Link>
        </div>
      </div>
    </div>
  );
}
