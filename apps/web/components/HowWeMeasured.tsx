export function HowWeMeasured({ traces }: { traces: string[] }) {
  return (
    <details className="card">
      <summary>How We Measured This</summary>
      <ul>
        {traces.map((trace, index) => (
          <li key={`${trace}-${index}`}>{trace}</li>
        ))}
      </ul>
    </details>
  );
}
