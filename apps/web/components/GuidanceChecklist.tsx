const RULES = [
  {
    title: "Window light first",
    detail: "Face a window and avoid dim rooms or strong overhead bulbs."
  },
  {
    title: "Clean, unfiltered photos",
    detail: "Disable beauty mode and skip color filters for accurate skin readings."
  },
  {
    title: "6 to 15 selfies",
    detail: "Upload enough variety for stable confidence and better aggregate scoring."
  },
  {
    title: "Simple framing",
    detail: "Keep one face centered with minimal occlusions from hats or glasses."
  }
];

export function GuidanceChecklist() {
  return (
    <section className="panel panel-soft">
      <h3 className="section-title">Photo quality guide</h3>
      <p className="section-note">
        These prep steps improve reliability before the analysis starts.
      </p>
      <ul className="guidance-grid" style={{ marginTop: "0.75rem" }}>
        {RULES.map((rule) => (
          <li className="guidance-item" key={rule.title}>
            <p className="guidance-title">{rule.title}</p>
            <p className="guidance-detail">{rule.detail}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
