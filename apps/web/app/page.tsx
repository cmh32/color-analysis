import Link from "next/link";

const previewSwatches = [
  { name: "Blush", toneClass: "tone-blush" },
  { name: "Lilac", toneClass: "tone-lilac" },
  { name: "Butter", toneClass: "tone-butter" },
  { name: "Sage", toneClass: "tone-sage" },
  { name: "Powder", toneClass: "tone-powder" }
];

export default function HomePage() {
  return (
    <main className="page">
      <section className="hero">
        <h1>Find your colors.</h1>
        <p className="lede">
          Share 6 to 15 selfies and receive your seasonal palette.
        </p>
        <div className="actions">
          <Link href="/analyze" className="button button-primary">
            Start Analysis
          </Link>
        </div>
      </section>

      <section className="panel" id="prep">
        <h3 className="section-title">Before you begin</h3>
        <ul className="guidance-grid" style={{ marginTop: "0.75rem" }}>
          <li className="guidance-item">
            <p className="guidance-title">Natural window light</p>
            <p className="guidance-detail">Stand near daylight and avoid overhead yellow light.</p>
          </li>
          <li className="guidance-item">
            <p className="guidance-title">No filters</p>
            <p className="guidance-detail">Upload original photos without beauty effects.</p>
          </li>
          <li className="guidance-item">
            <p className="guidance-title">Face visible</p>
            <p className="guidance-detail">Hair pulled back helps skin undertone read more accurately.</p>
          </li>
          <li className="guidance-item">
            <p className="guidance-title">Light makeup</p>
            <p className="guidance-detail">Try minimal coverage so natural contrast remains clear.</p>
          </li>
        </ul>
      </section>
    </main>
  );
}
