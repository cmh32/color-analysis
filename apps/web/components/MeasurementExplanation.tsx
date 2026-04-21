"use client";

import { useEffect, useMemo, useState } from "react";
import type { ClassificationResult } from "../lib/types";

type Explanation = ClassificationResult["measurement_explanation"];

function pathFromPolygon(points: { x: number; y: number }[]): string {
  if (points.length === 0) return "";
  const [first, ...rest] = points;
  const commands = [`M ${first.x * 100} ${first.y * 100}`];
  for (const point of rest) {
    commands.push(`L ${point.x * 100} ${point.y * 100}`);
  }
  commands.push("Z");
  return commands.join(" ");
}

export function MeasurementExplanation({ explanation }: { explanation: Explanation }) {
  const photos = explanation?.photos ?? [];
  const readings = explanation?.readings ?? [];
  const defaultIndex = Math.max(0, photos.findIndex((photo) => photo.is_default));
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState(defaultIndex);
  const [selectedGroup, setSelectedGroup] = useState<"skin" | "hair" | "eyes">("skin");

  useEffect(() => {
    setSelectedPhotoIndex(defaultIndex);
  }, [defaultIndex]);

  const selectedPhoto = photos[selectedPhotoIndex] ?? null;

  useEffect(() => {
    if (!selectedPhoto) return;
    const nextGroup =
      selectedPhoto.overlays.find((overlay) => overlay.group === selectedGroup)?.group ??
      selectedPhoto.overlays[0]?.group ??
      "skin";
    setSelectedGroup(nextGroup);
  }, [selectedPhoto, selectedGroup]);

  const selectedReading = useMemo(
    () => readings.find((reading) => reading.key === selectedGroup) ?? readings[0] ?? null,
    [readings, selectedGroup]
  );

  if (!explanation || (!photos.length && !readings.length)) return null;

  return (
    <section className="panel measurement-panel">
      <h3 className="section-title">How We Read Your Coloring</h3>
      <p className="section-note">
        We highlight the parts of your face we measured, then summarize them in plain language.
      </p>
      <p className="measurement-note">{explanation.note}</p>

      <div className="measurement-layout">
        {photos.length > 0 ? (
          <div className="measurement-visual">
            <div className="measurement-frame">
              <img
                className="measurement-image"
                src={selectedPhoto?.preview_url}
                alt={selectedPhoto ? `Measured view of ${selectedPhoto.filename}` : "Measured photo"}
              />
              {selectedPhoto ? (
                <>
                  <svg className="measurement-overlay" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                    {selectedPhoto.overlays.map((overlay) =>
                      overlay.polygons.map((polygon, index) => (
                        <path
                          key={`${overlay.id}-${index}`}
                          d={pathFromPolygon(polygon)}
                          className={`measurement-shape measurement-${overlay.group}`}
                        />
                      ))
                    )}
                  </svg>
                  {selectedPhoto.overlays.map((overlay) => (
                    <button
                      key={overlay.id}
                      type="button"
                      className={`measurement-pin ${selectedGroup === overlay.group ? "is-active" : ""}`}
                      style={{ left: `${overlay.anchor_x * 100}%`, top: `${overlay.anchor_y * 100}%` }}
                      onClick={() => setSelectedGroup(overlay.group)}
                    >
                      {overlay.label}
                    </button>
                  ))}
                </>
              ) : null}
            </div>

            {photos.length > 1 ? (
              <div className="measurement-strip" aria-label="Accepted photos used for explanation">
                {photos.map((photo, index) => (
                  <button
                    type="button"
                    key={photo.photo_id}
                    className={`measurement-thumb ${index === selectedPhotoIndex ? "is-active" : ""}`}
                    onClick={() => setSelectedPhotoIndex(index)}
                  >
                    <img src={photo.preview_url} alt={`Photo ${index + 1}`} />
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="measurement-copy">
          {selectedReading ? (
            <article className="measurement-card">
              <div className="measurement-card-header">
                <div>
                  <strong>{selectedReading.label}</strong>
                  <p className="section-note">{selectedReading.summary}</p>
                </div>
                {selectedReading.swatch ? (
                  <span className="measurement-swatch" style={{ backgroundColor: selectedReading.swatch }} />
                ) : null}
              </div>
            </article>
          ) : null}

          <div className="measurement-axis-list">
            {explanation.axis_explanations.map((axis) => (
              <article key={axis.key} className="measurement-axis-card">
                <strong>{axis.label}</strong>
                <p className="section-note">{axis.summary}</p>
              </article>
            ))}
          </div>

          {selectedReading?.technical_details?.length ? (
            <details className="details-panel measurement-details">
              <summary>Technical details</summary>
              <ul className="details-list">
                {selectedReading.technical_details.map((detail) => (
                  <li key={detail.label}>
                    {detail.label}: <strong>{detail.value}</strong>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      </div>
    </section>
  );
}
