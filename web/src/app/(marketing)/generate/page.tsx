import { Suspense } from "react";
import GenerateForm from "./GenerateForm";

function FormFallback() {
  return (
    <div className="card card-pad-lg" style={{ textAlign: "center", padding: "4rem 2rem" }}>
      <span className="spinner spinner-dark" style={{ margin: "0 auto" }} />
    </div>
  );
}

export default function GeneratePage() {
  return (
    <>
      <section className="page-hero">
        <div className="container container-narrow">
          <div className="section-head" style={{ marginBottom: 0 }}>
            <span className="eyebrow">AI ad generator</span>
            <h1 className="h1" style={{ fontSize: "clamp(2rem, 4.4vw, 3.4rem)" }}>
              Create your video ad
            </h1>
            <p className="lead" style={{ marginTop: "1rem" }}>
              Paste your business URL below. We&apos;ll handle everything else.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container container-narrow">
          <Suspense fallback={<FormFallback />}>
            <GenerateForm />
          </Suspense>
        </div>
      </section>
    </>
  );
}
