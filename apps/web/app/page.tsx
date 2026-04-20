import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>Seasonal Color Analysis</h1>
      <p>
        Upload 6 to 15 selfies. We return a top-2 season estimate, reliability,
        and a transparent measurement trace.
      </p>
      <div className="card">
        <h2>Before You Start</h2>
        <ul>
          <li>Natural light near a window</li>
          <li>No beauty filters</li>
          <li>Hair pulled back when possible</li>
          <li>No heavy makeup</li>
        </ul>
      </div>
      <div className="row">
        <Link href="/analyze">
          <button style={{ background: "var(--accent)", color: "white" }}>
            Start Analysis
          </button>
        </Link>
      </div>
    </main>
  );
}
