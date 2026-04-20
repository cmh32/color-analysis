export function GuidanceChecklist() {
  const rules = [
    "Face camera head-on",
    "Avoid sunglasses or strong shadows",
    "Use at least 6 photos",
    "Mix neutral expressions and angles"
  ];

  return (
    <section className="card">
      <h3>Guidance</h3>
      <ul>
        {rules.map((rule) => (
          <li key={rule}>{rule}</li>
        ))}
      </ul>
    </section>
  );
}
