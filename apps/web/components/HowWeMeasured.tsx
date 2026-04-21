export function HowWeMeasured({ traces }: { traces: string[] }) {
  return (
    <details className="panel details-panel">
      <summary>How We Measured This</summary>
      <ul className="details-list">
        {traces.map((trace, index) => (
          <li key={`${trace}-${index}`}>{trace}</li>
        ))}
      </ul>
    </details>
  );
}
