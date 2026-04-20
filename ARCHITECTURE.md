# Seasonal Color Analysis — Architecture Memo (v0)

**Status:** design proposal. No code yet. Choices are opinionated but marked **Recommended / Alternative / Deferred** where non-obvious. Assumptions and uncertainty are called out inline.

---

## 1. Executive summary

**Recommended architecture.** A thin Next.js web app (mobile-first PWA) talks to a small stateless API, which enqueues jobs onto a Python worker pool. All heavy CV lives in the Python workers. Inputs land in S3-compatible object storage; structured results and audit artifacts land in Postgres. Photos are ephemeral; derived features are retained.

```
[Browser / PWA]  ──HTTPS──▶  [API: Next.js route handlers or FastAPI]
                                        │
                                        ├── signed upload URLs ──▶ [Object storage: R2/S3]
                                        │
                                        └── enqueue ──▶ [Redis] ──▶ [Python worker (RQ)]
                                                                       │
                                                                       ├── reads photos from R2
                                                                       ├── runs CV pipeline
                                                                       └── writes features/results to [Postgres]
```

**Key design principles.**
1. **Deterministic, inspectable CV.** Every number that contributes to a season has a traceable provenance: image → region → Lab sample → normalized → aggregated → scored.
2. **LLMs do prose, not measurement.** LLMs may later draft the user-facing explanation from numeric features. They never see the raw image for classification.
3. **Explainability over accuracy theatre.** We'd rather return "insufficient quality — retake with window light" than a confident wrong answer.
4. **Privacy by default.** Anonymous sessions, short photo retention, explicit consent for anything longer-lived.
5. **Labeled data from day 1.** Every session produces a feature vector and (optionally) a user-reported self-label. This is the training set for the Phase-2 learned classifier.

**Biggest technical risks (ranked).**
1. **White balance on phone selfies.** Modern phone pipelines apply HDR, beauty filters, auto-tone, and per-region exposure. Without a known-neutral reference, "warmth" measurements are noise. **Primary mitigation: sclera-based neutral reference.** Backup: gray-world / shades-of-gray.
2. **Consumer photo variance.** Harsh overhead lighting, screen glare, mirrors, sunglasses, heavy makeup, filters. Quality screening must be strict.
3. **Season "ground truth" is subjective.** Even professional analysts disagree. We need inter-rater agreement (Fleiss' κ) on our gold set; if κ is low, our ceiling is low.
4. **Monetization pressure vs trust.** Affiliate recommendations can erode the "science-informed, no gimmicks" promise if surfaced before the analysis proves itself.

**MVP scope (Phase 1).** 4-season classification, top-2 result + reliability score, 10–15 uploaded photos, anonymous sessions, ephemeral storage, English only, web-only PWA, no accounts, no recommendations, no 12-season.

**Deferred.** 12-season refinement, native apps, live-capture, garment recommendations, LLM-authored written reports, account system, sharing, social features.

---

## 2. Product assumptions

### 2.1 User journey (V1)

1. **Landing** — value prop, 20-second explainer, "Start free analysis" CTA. No signup.
2. **Guidance screen** — 4-tile checklist: natural daylight, no makeup or minimal, hair pulled back, no filters. "Why this matters" expander.
3. **Upload** — drag/drop + picker; 10–15 photos required (min 8 to enable Analyze). Client-side thumbnails shown with per-photo quality preflight (blurry / too dark / filter detected / face not found). User can drop bad ones and re-add.
4. **Analyze** — spinner with honest progress ("detecting faces… 6/12", "normalizing color… 12/12", "scoring…"). Typical wall time target: 20–40 s.
5. **Result screen** — top season (large), secondary season (smaller, labeled "also likely"), reliability score (High / Medium / Low) with a one-sentence reason. Four axis dials (Warm↔Cool, Light↔Deep, Soft↔Bright, Low↔High Contrast) showing where they sit. Collapsible "How we measured this" revealing per-photo thumbnails with region masks.
6. **Actions** — save a shareable read-only link (24 h), or delete now. No default save.

### 2.2 Constraints / assumptions about users

- Mobile-first. Assume iPhone Safari majority.
- Will upload from camera roll, not shoot in-app (V1).
- Patience budget ~60 s end to end.
- Will absolutely upload filtered/edited photos unless actively discouraged. We must detect and reject.
- Comes from TikTok expecting a cute result; we have to reconcile "cute" with "honest uncertainty."

### 2.3 What "good" means

- Returns a season in ≥85 % of sessions that pass photo-quality screening.
- Top-2 includes the human-consensus season in ≥80 % of labeled gold-set cases (north-star, not launch-blocking).
- ≥90 % of users report the result "sounds like me" in a post-result 1-question survey.
- Median session wall time ≤45 s.
- Zero photos retained past the documented TTL.

### 2.4 Non-goals (V1)

- 12-season classification, garment/shade recommendations, LLM-authored rich reports, native apps, live camera capture, user accounts, saved history across devices, social sharing beyond a single read-only link, B2B / pro-analyst tooling, video input.

---

## 3. System architecture

| Layer | Recommended | Why | Alternative | Deferred |
|---|---|---|---|---|
| Frontend | **Next.js 15 (App Router), React 19, TypeScript, Tailwind** as a mobile-first PWA | SSR for the marketing landing, client islands for upload flow, low-cost Vercel hosting, easy SEO for TikTok search traffic | Remix; SvelteKit | Native iOS/Android (Phase 3) |
| API | **FastAPI (Python 3.12)** as a single service, colocated with CV workers | The API mostly brokers uploads + reads results; keeping it in the same language as CV avoids a second deploy target and shared-types duplication. Pydantic gives us request/response schemas the OpenAPI generator can emit to TS. | Next.js route handlers fronting a Python worker (2-language stack); Hono on Bun | GraphQL (unnecessary for this shape) |
| Async jobs | **RQ** on Redis | Simpler than Celery, sufficient for our throughput, good observability, trivial local setup | Celery (more features, more ops burden); Temporal (overkill); Cloud Tasks | Temporal if we add multi-step human-in-loop |
| Object storage | **Cloudflare R2** with S3-compatible API | No egress fees matter when we're shipping image thumbnails back to browsers; same API as S3 so we can swap | AWS S3; Supabase Storage | — |
| Database | **Postgres 16** (managed: Neon or Supabase) | JSONB for feature vectors and debug artifacts; relational for sessions/photos; trivial backups | SQLite (too limiting for job queue coordination); Mongo (no reason) | pgvector if we add similarity search on feature vectors |
| Cache / queue broker | **Redis** (Upstash for serverless; self-hosted on Fly for workers) | Dual-duty: RQ broker + short-lived result cache | — | — |
| Auth | **Anonymous session tokens** (opaque, HttpOnly cookie, 30-day rotation); **optional email magic link** post-result for "save my result" | Accountless is a conversion unlock for TikTok traffic. Email only if user opts in. | Clerk / Auth.js if we ever need real accounts | OAuth providers |
| Analytics | **PostHog (self-host or cloud)** for product analytics + session replay (with image blurring); **Sentry** for errors | Funnel analysis is the #1 thing we need. PostHog's privacy controls beat GA. Session replay with all images masked is critical — never replay a user's face. | Amplitude; Mixpanel | Server-side BI (dbt + Metabase) Phase 3 |
| Observability | **OpenTelemetry** traces from API + workers to **Grafana Cloud** (free tier); structured JSON logs via **Loki** | OTel future-proofs vendor swap; one pane of glass for traces/logs/metrics | Datadog (expensive for MVP); Honeycomb | — |
| Deployment | **Frontend on Vercel; API + workers on Fly.io** (shared Postgres on Neon, R2 on Cloudflare) | Fly runs containers near users with persistent volumes for model weights; Vercel handles the Next.js edge. Both have generous free/cheap tiers. | Render; AWS ECS Fargate; GCP Cloud Run (cold-start unfriendly for 300 MB mediapipe containers) | Kubernetes when we outgrow this (years) |
| CI/CD | **GitHub Actions**; **Turborepo** for monorepo caching; **Docker** for worker images | Standard, free for open source + cheap otherwise | CircleCI | — |

**Why split frontend (Node) from API+workers (Python).** The CV libraries we depend on — MediaPipe, OpenCV, scikit-image, NumPy — are Python-native. Porting or bridging to Node is a false economy. The cost of a second runtime is one more Dockerfile; the savings are every hour we'd otherwise spend fighting CV in JS.

---

## 4. Computer vision / analysis pipeline

Design goal: every decision the classifier makes must trace back to a Lab-space measurement from a specific region of a specific photo, with a specific normalization applied, at a specific quality grade.

### 4.1 Pipeline stages

```
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 0  upload & decode                                                 │
│   HEIC→sRGB PNG, strip EXIF rotation, enforce max 2048 px long edge,     │
│   persist original hash for dedup.                                       │
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 1  quality screen (cheap, per-photo, runs before Stage 2)          │
│   • blur  — variance of Laplacian < T_blur → reject                      │
│   • exposure  — luminance histogram clipping > 3 % either tail → reject  │
│   • filter / edit detection — heuristics (see 4.3) → flag, not auto-rej  │
│   • face count — 0 → reject, ≥2 → ask user to re-upload                  │
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 2  face detection & landmarking                                    │
│   MediaPipe FaceMesh (468 pts) + MediaPipe Iris (separate model, 5 pts   │
│   per eye). If face yaw>25° or pitch>20° → reject as "not a front photo".│
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 3  region masks                                                    │
│   skin   = cheek patches (left+right) ∪ forehead patch, shrunk from      │
│            landmarks by 6 px, with specular-highlight exclusion (V>0.95) │
│   iris   = iris disk minus catchlight (top-bright 5 %) minus pupil (     │
│            inner 40 % radius)                                            │
│   sclera = eye polygon minus iris disk, minus eyelash pixels (dark-edge  │
│            morphological opening)                                        │
│   hair   = forehead-up region, sampled above browline within face bbox,  │
│            constrained to high-saturation-matching-dominant-cluster pix  │
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 4  white balance / color normalization                             │
│   PRIMARY: sclera-neutral correction.                                    │
│     sclera median RGB → compute gain per channel so sclera → (G,G,G)     │
│     where G = mean(R,G,B). Apply Bradford chromatic adaptation in XYZ.   │
│   FALLBACK (if sclera area < 200 px or SD too high): shades-of-gray      │
│     (Minkowski p=6) illuminant estimate.                                 │
│   LAST-RESORT: gray-world. Tag the photo's normalization method for      │
│     later confidence weighting.                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 5  feature extraction (per region, per photo)                      │
│   Convert region pixels to CIELAB (D65). Report, per region:             │
│     L* (median, IQR), a* (median), b* (median), C* = √(a*²+b*²),         │
│     h°_ab = atan2(b*, a*) in degrees,                                    │
│     ITA = atan2(L*−50, b*) in degrees  (dermatology-standard for skin). │
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 6  multi-image aggregation                                         │
│   For each region-feature pair: quality-weighted median across photos;   │
│   weight = photo_quality_score × normalization_confidence.               │
│   Report robust SD (MAD) per feature — this is our within-user signal    │
│   consistency.                                                           │
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 7  scorecard (4 dimensions; see §5 for formulas)                   │
│   warmth, value, chroma, contrast  → point in 4-D [−1, +1] space.        │
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 8  season classification                                           │
│   Prototype distance to each of the 4 seasons in 4-D space;              │
│   return top-2 with pseudo-probabilities; separately compute a           │
│   reliability score (quality × consistency × margin).                    │
├──────────────────────────────────────────────────────────────────────────┤
│ STAGE 9  persist                                                         │
│   Features, per-photo quality, region-mask thumbnails (low-res, for      │
│   the "how we measured" UI), classification result, reliability, and    │
│   a trace of which normalization branch ran.                             │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Thresholds (initial; tuned on gold set)

| Gate | Metric | V1 threshold |
|---|---|---|
| Blur | VarLaplacian | ≥ 100 |
| Over/underexposure | % pixels in top/bottom 1 % | ≤ 3 % each |
| Face yaw | absolute degrees | ≤ 25° |
| Face pitch | absolute degrees | ≤ 20° |
| Min skin pixels | after masking | ≥ 4 000 |
| Min sclera pixels | for WB primary | ≥ 200 |

Sessions require ≥ 6 passing photos to produce a result; otherwise "insufficient quality."

### 4.3 Filter / edit detection (heuristic, V1)

Filters are the silent killer of color analysis. Red flags — any two → downweight photo by 0.5, any three → reject:
- Sclera chroma — true sclera is near-neutral (C* < 5). C* > 15 suggests tint.
- Skin b* uniformity — unnaturally low SD across cheek patches suggests smoothing.
- Iris saturation outliers (e.g., C* > 40 with L* > 60 — common with "enhance eyes").
- EXIF signals (software tag mentions known filter apps).
- Edge-sharpness mismatch — face edges much sharper than background.

**Deferred:** a small classifier trained on filter-vs-raw pairs. Easy to add once we have labeled data.

### 4.4 Failure / "insufficient quality" outcomes

Explicit states, returned in the API:

- `ok` — normal top-2 result.
- `ok_low_reliability` — result returned with prominent "low confidence, consider retaking" UI.
- `insufficient_photos` — fewer than 6 passed quality.
- `no_face_detected` — across all uploads.
- `multiple_subjects` — ≥2 faces in ≥2 photos.
- `filter_suspected` — more than half the set flagged as edited.

Each state has a specific retry-guidance copy string; never a generic error.

---

## 5. Scoring framework

### 5.1 Dimensions

| Axis | Signal | Source regions | Raw metric | Normalized to [−1, +1] |
|---|---|---|---|---|
| **Warmth** | warm ↔ cool undertone | skin, hair, iris | weighted mean of `cos(h°_ab − 70°)` across regions (warm hue ≈ 70°, cool ≈ 340°/−20°); ITA for skin used as a second source | clipped linear mapping against gold-set percentiles |
| **Value** | light ↔ deep | skin, hair | skin L* and hair L* z-scored and averaged | — |
| **Chroma** | soft (muted) ↔ bright (saturated) | skin, iris | max(C*_iris, C*_skin) and their product | — |
| **Contrast** | low ↔ high internal contrast | skin vs hair, skin vs iris | ΔL*(skin, hair) + 0.5·ΔL*(skin, iris) | — |

Why hue-angle instead of a* alone for warmth: in Lab, a* is red↔green and b* is yellow↔blue. Skin "warmth" in color-analysis vocabulary means gold/yellow-leaning vs pink/blue-leaning — that's a hue-angle question, not a red-vs-green one. ITA = `atan2(L*−50, b*)` is the dermatology-standard and acts as a sanity check on the skin-specific reading.

### 5.2 Pseudocode

```python
# per-photo, per-region features already computed and aggregated
# into region-level robust means + MADs.

def scorecard(regions):
    # regions: {'skin': F, 'hair': F, 'iris': F, 'sclera': F}
    # F has: L, a, b, C, h_deg, ITA (all robust aggregates)

    # warmth ∈ [−1, +1]   (+1 = warm, −1 = cool)
    hue_warm = lambda h: math.cos(math.radians(h - 70))  # peak at 70°
    warmth_raw = (
        0.55 * hue_warm(regions['skin'].h_deg)
      + 0.25 * hue_warm(regions['hair'].h_deg)
      + 0.20 * hue_warm(regions['iris'].h_deg)
    )
    # ITA sanity: very high ITA (>40°) leans cool; very low (<10°) leans warm
    ita_adj = clamp((25 - regions['skin'].ITA) / 40, -0.3, 0.3)
    warmth = clamp(warmth_raw + ita_adj, -1, 1)

    # value ∈ [−1, +1]   (+1 = light, −1 = deep)
    L_skin = z_to_unit(regions['skin'].L, mu=60, sd=12)
    L_hair = z_to_unit(regions['hair'].L, mu=35, sd=15)
    value  = clamp(0.6 * L_skin + 0.4 * L_hair, -1, 1)

    # chroma ∈ [−1, +1]   (+1 = bright, −1 = soft)
    chroma_raw = max(regions['iris'].C, regions['skin'].C * 1.3)
    chroma     = z_to_unit(chroma_raw, mu=15, sd=10)

    # contrast ∈ [−1, +1]  (+1 = high, −1 = low)
    dL_hair = abs(regions['skin'].L - regions['hair'].L)
    dL_iris = abs(regions['skin'].L - regions['iris'].L)
    contrast = z_to_unit(dL_hair + 0.5 * dL_iris, mu=35, sd=15)

    return (warmth, value, chroma, contrast)
```

`z_to_unit(x, mu, sd)` = `clamp((x−mu)/(2·sd), −1, 1)`. Mu/sd seeded from literature, refit on our gold set.

### 5.3 Season prototypes (4-D, in [−1, +1]^4)

| Season | Warmth | Value | Chroma | Contrast | Prose gloss |
|---|---:|---:|---:|---:|---|
| Spring | +0.7 | +0.5 | +0.7 | +0.1 | warm, light, bright |
| Summer | −0.6 | +0.4 | −0.5 | −0.3 | cool, light, soft |
| Autumn | +0.6 | −0.3 | −0.3 | 0.0 | warm, deep, soft |
| Winter | −0.6 | −0.3 | +0.7 | +0.6 | cool, deep, bright, high-contrast |

### 5.4 Classification

```python
def classify(user_point, prototypes, cov_inv):
    # Mahalanobis distance per season
    dists = {s: mahalanobis(user_point, p, cov_inv) for s, p in prototypes.items()}
    # top-2
    ranked = sorted(dists.items(), key=lambda kv: kv[1])
    top1, top2 = ranked[0], ranked[1]
    # pseudo-probabilities for display only
    temp = 0.8
    exps = {s: math.exp(-d / temp) for s, d in dists.items()}
    Z    = sum(exps.values())
    probs = {s: v / Z for s, v in exps.items()}
    return {'top1': top1, 'top2': top2, 'probs': probs,
            'margin': top2[1] - top1[1]}
```

`cov_inv` starts as identity (weighted Euclidean); moves to a fitted inverse-covariance once we have ≥200 gold-labeled points.

### 5.5 Reliability score (separate from classification probability)

Users will read `probs` as certainty; we separate "how likely is this season given the numbers" from "how much should you trust those numbers."

```python
reliability =  0.4 * mean_photo_quality            # [0, 1]
            +  0.3 * (1 - within_user_feature_MAD_normalized)
            +  0.2 * clamp(margin / 0.8, 0, 1)     # classifier margin
            +  0.1 * normalization_confidence       # sclera-WB > gray-world

# Bucketed for UX
reliability_bucket = 'High' if r >= 0.75 else 'Medium' if r >= 0.5 else 'Low'
```

### 5.6 From 4 seasons to 12 (deferred but scaffolded)

Each season expands into three sub-types along its **dominant axis**:

| Parent | Sub-types | Dominant axis | Sub-type rule (within-season) |
|---|---|---|---|
| Spring | Light / True / Bright | value or chroma | Light = value strongest, Bright = chroma strongest, True = warmth strongest |
| Summer | Light / True / Soft | value or chroma | Light = value, Soft = low chroma, True = coolness |
| Autumn | Soft / True / Deep | chroma or value | Soft = low chroma, Deep = low value, True = warmth |
| Winter | Bright / True / Deep | chroma or value | Bright = chroma, Deep = value, True = coolness |

The 4-D scorecard is exactly the input the 12-season expansion needs — we reuse the axes, we just add an intra-season argmax. No rework.

### 5.7 Heuristics vs learned

- **Heuristic now, measured later:** axis formulas, prototype points, normalization ranges, weights within warmth (0.55/0.25/0.20).
- **Learned once we have data:** inverse covariance for Mahalanobis; possibly a small logistic regression or XGBoost on the 4 features; filter detector; per-axis mu/sd recentering.

We do **not** jump straight to a deep classifier on raw pixels. It would destroy explainability and the "science-informed" promise, and we wouldn't have enough data for years.

---

## 6. Privacy / safety / trust

### 6.1 Data handling

| Artifact | Stored? | Where | TTL | Notes |
|---|---|---|---|---|
| Original photo | yes, encrypted at rest | R2 | **24 h after result is computed** | Only re-analyzable within that window |
| Thumbnail (region-mask overlay, 256 px) | yes | R2 | 7 d | Powers the "how we measured" UI |
| Derived features (Lab stats per region) | yes | Postgres | indefinite (anonymized) | No identity attached |
| Classification result | yes | Postgres | indefinite | Anonymous session ID only |
| Audit trace (pipeline stage outputs) | yes | Postgres JSONB | 30 d | For debug; then purged |
| IP address, UA | logged for 7 d then truncated | Loki | 7 d | No long-term linkage |
| Email (if user opts in to "save my result") | hashed on write | Postgres | until user deletes | Used only for magic-link retrieval |

**Right-to-delete.** One-click `DELETE /sessions/:id` purges photos, thumbnails, features, results, and audit trace. We commit to a ≤ 24 h deletion SLA across all stores.

### 6.2 Anonymous usage

Default. V1 has no signup. Session is a HttpOnly cookie holding an opaque ID; nothing else links the session to a person.

### 6.3 Messaging uncertainty honestly

- **Language audit.** Never "you are a Winter." Always "your measurements are most consistent with Winter, and also overlap Summer." Microcopy reviewed pre-launch for this.
- **Reliability badge** is prominent, not buried in a tooltip.
- **"How we measured this"** is always one tap away, showing the actual regions sampled.

### 6.4 Disclaimers / guidance

A single expandable "Getting an accurate reading" block, shown pre-upload and again if reliability is Low:

- Shoot near a window, mid-day, indirect light.
- Remove makeup, or use only base coverage.
- No filters (including the subtle auto-beauty iOS applies — turn off "Photographic Styles" if possible).
- Take photos with different angles and hair positions.
- Don't use mirror selfies — the mirror tints.
- We analyze your natural coloring, not your current hair dye or tan — we'll infer both but the deeper "palette" reading reflects today's coloring.

### 6.5 Avoiding overclaiming

- Don't cite studies we can't link. The memo-level phrase "science-informed" means we use peer-reviewed color science (CIELAB, ITA, chromatic adaptation) — not that seasonal analysis itself is a peer-reviewed system. Marketing copy must stay on that line.
- No health/dermatology claims, ever.

---

## 7. Data model

### 7.1 Entities (conceptual)

```
User (optional; only if email opt-in)
  └─< AnalysisSession >─┐
                        ├─< Photo >─< PhotoQuality
                        │           └─< ExtractedFeature (per region)
                        ├─ AggregatedFeature
                        ├─ Classification
                        ├─ Recommendations (empty V1)
                        └─ AuditTrace
```

### 7.2 Tables (Postgres; `snake_case`, UUIDv7 PKs)

```
users (
  id uuid pk,
  email_hash text unique null,              -- null for anonymous
  created_at timestamptz,
  deleted_at timestamptz null
)

analysis_sessions (
  id uuid pk,
  user_id uuid null references users,
  session_token_hash text,                  -- anonymous cookie
  status text,                              -- pending|running|complete|failed|deleted
  result_state text,                        -- ok|ok_low_reliability|insufficient_photos|...
  reliability numeric(4,3) null,
  reliability_bucket text null,             -- High|Medium|Low
  created_at timestamptz,
  completed_at timestamptz null,
  expires_at timestamptz                    -- auto-delete trigger
)

photos (
  id uuid pk,
  session_id uuid references analysis_sessions on delete cascade,
  storage_key text,                         -- R2 path
  sha256 text,                              -- dedup within session
  width int, height int,
  uploaded_at timestamptz,
  purged_at timestamptz null
)

photo_quality (
  photo_id uuid pk references photos on delete cascade,
  blur_score numeric, exposure_low numeric, exposure_high numeric,
  face_found bool, faces_count int,
  yaw_deg numeric, pitch_deg numeric,
  filter_flags jsonb,                       -- { sclera_chroma: 12.1, ... }
  quality_score numeric,                    -- [0,1]
  passed bool, reject_reason text null
)

extracted_features (
  id uuid pk,
  photo_id uuid references photos on delete cascade,
  region text,                              -- skin|hair|iris|sclera
  L numeric, a numeric, b numeric, C numeric, h_deg numeric, ita numeric,
  L_mad numeric, C_mad numeric,
  n_pixels int,
  normalization_method text                 -- sclera|shades_of_gray|gray_world
)

aggregated_features (
  session_id uuid pk references analysis_sessions on delete cascade,
  warmth numeric, value numeric, chroma numeric, contrast numeric,
  warmth_ci jsonb, value_ci jsonb, chroma_ci jsonb, contrast_ci jsonb,
  normalization_confidence numeric
)

classifications (
  session_id uuid pk references analysis_sessions on delete cascade,
  top1_season text, top1_prob numeric,
  top2_season text, top2_prob numeric,
  all_probs jsonb,
  margin numeric
)

recommendations (                           -- empty in V1, reserved
  id uuid pk,
  session_id uuid references analysis_sessions,
  kind text, payload jsonb, created_at timestamptz
)

audit_traces (
  session_id uuid pk references analysis_sessions on delete cascade,
  pipeline_version text,
  per_stage jsonb,                          -- timings, branches taken, fallbacks
  created_at timestamptz,
  purge_after timestamptz
)
```

### 7.3 Persisted vs ephemeral

| Ephemeral (≤ 24 h) | Short (≤ 30 d) | Long-lived |
|---|---|---|
| Original photos | Thumbnails (7 d), audit traces (30 d) | Anonymous features, classifications, aggregated results (training data) |

---

## 8. API design

Versioned under `/v1`. JSON, `application/json`. Anonymous sessions via HttpOnly cookie `cas_sid`. All endpoints rate-limited per session.

```
POST   /v1/sessions
   → 201 { session_id, upload_policy: { url, headers, fields, expires_at } }
   Creates an anonymous session, returns a presigned-upload policy for R2.

POST   /v1/sessions/:id/photos
   body: { storage_key, sha256, width, height }
   → 201 { photo_id, quality: { passed, reject_reason?, quality_score, ... } }
   Server fetches thumbnail, runs Stage 1 quality screen synchronously, returns verdict.

POST   /v1/sessions/:id/analyze
   → 202 { job_id, status: "queued", eta_seconds }
   Requires ≥ 6 passed photos. Enqueues worker job.

GET    /v1/sessions/:id/status
   → 200 { status, stage, progress, eta_seconds }
   Polled by client; websockets deferred.

GET    /v1/sessions/:id/result
   → 200 {
       result_state,
       reliability: { score, bucket, reasons: [...] },
       scorecard: { warmth, value, chroma, contrast },
       classification: { top1: {season, prob}, top2: {season, prob}, all_probs },
       per_photo: [ { photo_id, thumbnail_url, regions_overlay_url, quality } ],
       disclaimers: [...]
     }
   404 while pending.

DELETE /v1/sessions/:id
   → 204. Purges photos, thumbnails, features, result, audit trace.

--- admin, gated by signed internal token ---

GET    /v1/admin/sessions/:id/trace
   → 200 { audit_trace, features, intermediate_thumbnails_urls }
   For debugging only. Never exposed to end users.
```

**Errors** follow RFC 7807 (`application/problem+json`) with a stable `type` URI so the frontend can route on it.

---

## 9. Repo / codebase plan

### 9.1 Monorepo, yes

Turborepo + pnpm workspaces. Two languages (TS + Python) — we use Turborepo to orchestrate builds/tests, not to pretend Python is a JS package. OpenAPI-generated TS types are the single source of truth for request/response shapes.

```
color-analysis/
├── apps/
│   ├── web/                        # Next.js PWA
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/api/                # thin fetch client, generated types
│   │   └── public/
│   └── api/                        # FastAPI app + RQ worker entrypoints
│       ├── pyproject.toml
│       ├── src/color_analysis/
│       │   ├── api/                # FastAPI routers (transport only)
│       │   │   ├── sessions.py
│       │   │   ├── photos.py
│       │   │   ├── analysis.py
│       │   │   └── admin.py
│       │   ├── core/               # pure business logic, no I/O
│       │   │   ├── session_service.py
│       │   │   ├── analysis_service.py
│       │   │   └── result_formatter.py
│       │   ├── cv/                 # ← the whole CV pipeline lives here
│       │   │   ├── decode.py
│       │   │   ├── quality.py
│       │   │   ├── landmarks.py    # mediapipe wrappers
│       │   │   ├── regions.py
│       │   │   ├── white_balance.py
│       │   │   ├── features.py
│       │   │   ├── aggregate.py
│       │   │   ├── scorecard.py
│       │   │   ├── classifier.py
│       │   │   └── pipeline.py     # orchestrator; calls the above in order
│       │   ├── storage/            # R2, Postgres, Redis adapters
│       │   ├── workers/            # RQ job functions
│       │   ├── schemas/            # Pydantic models
│       │   └── config.py           # env-var loader, typed
│       └── tests/
├── packages/
│   ├── shared-types/               # TS types generated from OpenAPI
│   └── ui/                         # shared React components
├── infra/
│   ├── docker/
│   ├── fly/
│   └── terraform/                  # later
├── eval/
│   ├── gold_set/                   # fixtures + manifest (no raw faces committed)
│   ├── cases/                      # synthetic and edge-case images
│   └── scripts/
├── docs/
│   └── ARCHITECTURE.md             # this file
├── package.json
├── pnpm-workspace.yaml
└── turbo.json
```

### 9.2 Separation of concerns

- **`api/`** modules only parse requests, call `core/`, shape responses. No CV, no SQL.
- **`core/`** orchestrates services. Depends on interfaces, not concrete adapters.
- **`cv/`** is pure functions on NumPy arrays → dataclasses. No I/O, no DB. This is what makes it testable with fixtures.
- **`storage/`** implements the interfaces `core/` depends on. Swappable (local fs vs R2 in tests).

### 9.3 Config / secrets

- `.env.local` for dev (gitignored). Pydantic `Settings` class is the only thing that reads env.
- Production: Fly secrets + Vercel env. Never in Docker images, never in git.
- A single `config.py` exports a typed `settings` object; nothing else reads `os.environ`.

---

## 10. Third-party libraries

| Need | Recommended | Why it fits | Maturity / risk | Better than the obvious alternative because… |
|---|---|---|---|---|
| Face landmarks | **MediaPipe Tasks (FaceLandmarker)** + **MediaPipe Iris** | 468-pt mesh, robust on selfies, Apache-2.0, runs CPU-only fast enough for background workers | Very mature; Google-maintained | dlib (68 pts) is too sparse for reliable iris/lip edges; MediaPipe Iris gives us eye center + sclera polygon, which dlib does not |
| Face detection (fallback) | **MediaPipe FaceDetector** | Same ecosystem | Mature | — |
| Image I/O + ops | **Pillow + OpenCV-Python (headless) + scikit-image** | Pillow for decode/HEIC, OpenCV for masks/morphology, scikit-image for color-space conversions | Mature | Pure OpenCV color conversions are clunky; scikit-image's `rgb2lab` is the clearer API. Headless OpenCV avoids pulling in GUI deps. |
| HEIC support | **pillow-heif** | Many iPhone uploads are HEIC | Mature | — |
| Background jobs | **RQ** + **Redis** | Simple, debuggable, Python-native | Mature | Celery is heavier, requires more ops. Temporal is overkill pre-product-market-fit. |
| API framework | **FastAPI** (Uvicorn, Pydantic v2) | Async, typed, auto OpenAPI | Mature | Flask has no native OpenAPI; Django is too much framework for a small API |
| Object storage client | **boto3** against **R2** | R2 speaks S3; boto3 is the canonical client | Mature | — |
| ORM / SQL | **SQLAlchemy 2.0 + Alembic** | Typed core, migrations, JSONB support | Mature | SQLModel is a lighter wrapper but hides capability we need for JSONB; raw SQL plus Pydantic works but loses migration tooling |
| Frontend upload | **Uppy + Tus** OR **UploadThing**-style presigned-direct-to-R2 | Multi-file, retries, progress, pauseable; direct-to-R2 avoids our API being the upload bottleneck | Uppy: mature, large bundle. UploadThing: newer. | react-dropzone alone has no retry/resume; we will see large uploads on flaky mobile networks |
| Frontend state | **React Server Components + Zustand** for the upload/result client islands | Thin client state, server-driven where possible | Mature | Redux is too much for this scope |
| Errors | **Sentry** | Best-in-class; frontend + Python backend | Mature | — |
| Product analytics | **PostHog** (self-host or cloud) | Funnels, session replay with image masking | Mature | Amplitude lacks replay; GA4's privacy story is weaker |
| Metrics / traces / logs | **OpenTelemetry** → **Grafana Cloud** | Unified, portable | Mature | Vendor lock-in of Datadog for MVP is not worth the cost |
| Testing (Python) | **pytest + hypothesis + pytest-benchmark + syrupy** (snapshot) | Hypothesis for property tests on Lab conversions; snapshots for pipeline trace JSON | Mature | — |
| Testing (TS) | **Vitest + Playwright** | Unit + E2E | Mature | Cypress works too; Playwright has better parallel isolation |
| Image fixtures | **git-lfs** for `eval/cases/`, **DVC** later | Track binaries without bloating git | Moderate | Storing JPEGs in git directly rots the repo |

---

## 11. Infrastructure / deployment

### 11.1 Local dev

- `docker-compose.yml` with Postgres, Redis, a fake S3 (MinIO).
- `pnpm dev` runs Next.js; `uvicorn` + `rq worker` in separate terminals (or `honcho`/`overmind`).
- Seed script populates a few known-good photos from the gold set so the pipeline can run end-to-end offline.

### 11.2 Staging

- Separate Fly app + separate Neon branch DB + separate R2 bucket. Same domain, `staging.` subdomain. Protected by basic auth header.
- Auto-deploys from `main`.

### 11.3 Production

- Frontend on Vercel (edge + node runtime).
- API + worker on Fly.io, 2 machines per role, `auto_stop_machines = "off"` for workers (cold-starting a 300 MB MediaPipe container kills UX).
- Neon Postgres with point-in-time recovery.
- R2 with lifecycle rules enforcing the 24 h photo / 7 d thumbnail TTLs.
- Cloudflare in front of Vercel for WAF + bot management.

### 11.4 CI/CD

GitHub Actions workflows:
1. `lint-test` — ruff, mypy, pytest, eslint, tsc, vitest.
2. `eval` — runs the gold-set regression against the current branch; fails PR if top-2 accuracy regresses by > 2 pp or reliability calibration drifts.
3. `build-push` — on merge to `main`, builds Docker images for API/worker, pushes, deploys to staging.
4. `promote` — manual trigger from staging to prod.

### 11.5 Secrets

Fly secrets, Vercel env vars, 1Password for humans. No secrets in repo, no secrets in images, no secrets in logs (structured logger has a redaction pass).

### 11.6 Observability SLOs (initial targets)

| Metric | Target |
|---|---|
| API p95 latency (non-analyze) | < 300 ms |
| Analyze job p95 wall time (12 photos) | < 45 s |
| Error rate | < 1 % of sessions |
| Photo-retention TTL compliance | 100 % (nightly audit) |

### 11.7 Cost-conscious MVP

Target < $200/mo for first 1 000 sessions/mo:
- Neon free / $19 tier
- Fly: 2 shared-cpu-1x API + 2 shared-cpu-2x workers ≈ $40–70
- R2: egress-free, storage ~$0.015/GB
- Vercel Hobby → Pro ($20)
- Sentry free tier, PostHog free tier, Grafana Cloud free tier

### 11.8 Scaling if we go viral

- API is stateless — horizontal scale on Fly.
- Workers scale on RQ queue depth (simple autoscaler: 1 worker per 5 queued jobs, cap 20).
- DB is the pinch point: Neon autoscales read replicas; we add connection pooling via PgBouncer.
- R2 handles viral load without egress surprises (main reason we picked it over S3).
- Rate-limit anonymous sessions per IP/UA to resist abuse.

---

## 12. Testing / evaluation

### 12.1 Levels

| Level | What | Tool |
|---|---|---|
| Unit | pure CV functions (color conversions, z_to_unit, prototype distances, hue warmth) | pytest + hypothesis |
| Integration | pipeline stages end-to-end against fixture photos | pytest + image fixtures |
| API | request/response contracts | pytest + httpx |
| Regression | gold-set pipeline output snapshotted | syrupy |
| E2E | browser: upload → result | Playwright |
| Perf | worker wall time per photo count | pytest-benchmark |
| Load | 100 concurrent analyze jobs | k6 (pre-launch) |

### 12.2 CV-specific tests

- **Property tests.** `rgb → lab → rgb` round-trip within ΔE < 1; `cos(h°-70°)` monotone between 70° and 250°; classifier invariant to small Lab perturbations.
- **Fixture tests.** For each curated face (see gold set below), assert region masks land within known bounding boxes, feature values within tolerance, and the final season set equals the human-consensus label.
- **Lighting robustness tests.** Apply synthetic illuminant shifts (D50 → D65 → A) and a curated set of phone-camera CCT simulations to the same base image; assert warmth axis moves ≤ 0.15 after normalization.
- **Filter robustness tests.** Run a photo through an Instagram-filter-like LUT; assert detection triggers and photo is downweighted.

### 12.3 Gold-standard eval set

- **Size:** 50–100 subjects, 10–15 photos each. Mix of skin tones (Fitzpatrick I–VI represented roughly proportional to expected user base), hair colors, eye colors.
- **Labeling:** **3+ trained analysts label independently** from the same photo set; report **Fleiss' κ** for inter-rater agreement. Keep items where ≥ 2/3 agree; discard the rest.
- **Provenance:** participants sign a data-release for training use; no scraped photos ever.
- **Splits:** 70 % train/dev (for mu/sd recentering and later learned classifier), 30 % held-out test used only for CI regression checks.

### 12.4 Metrics

| Metric | Definition |
|---|---|
| **Top-1 accuracy** | share of cases where `top1` == consensus label |
| **Top-2 coverage** | share where consensus label ∈ {top1, top2} (north-star) |
| **Calibration** | reported `reliability` bucket vs observed accuracy within that bucket; expect High > Medium > Low |
| **Consistency** | same subject, two different photo sets, same `top1`? |
| **Failure rate** | share of sessions hitting `insufficient_photos` etc., among well-lit uploads |
| **Skin-tone fairness** | top-2 coverage per Fitzpatrick bucket; alert if any bucket > 10 pp below overall |

### 12.5 Manual QA workflow

Before every release:
1. Run `eval` on the held-out set — block release if top-2 coverage drops > 2 pp.
2. Run a mobile-Safari smoke test through the full happy path and two unhappy paths (blur-reject, no-face).
3. Spot-check 5 sessions' audit traces for unexpected branch distributions.

---

## 13. Roadmap

### Phase 0 — architecture / design (now)

- **Goals.** Lock the CV pipeline contract (regions, normalization, features, scorecard). Finalize this memo. Recruit ~8 test subjects for a pilot gold subset. Decide anonymous-vs-account for V1 (recommended: anonymous).
- **Deliverables.** This memo; pipeline ADR; 3–5 OpenAPI endpoints drafted; pilot gold subset (~20 subjects) labeled by author + 2 others.
- **Dependencies.** Access to ~3 willing human analysts.
- **Risks.** Analyst availability; κ too low to validate at all.
- **Do not build yet.** Anything in `apps/`.

### Phase 1 — MVP (weeks 1–8)

- **Goals.** Ship the happy path end-to-end on one domain, with a 4-season top-2 result and a reliability score, to ~100 beta users from TikTok.
- **Deliverables.**
  - Frontend: landing, guidance, upload (drag/drop + picker), progress, result screen (top-2 + dials + reliability + "how we measured"), delete.
  - API: the seven endpoints in §8.
  - Worker: stages 0–9 with sclera-WB primary, gray-world fallback.
  - Gold-set CI gate live.
  - Privacy: 24 h photo TTL, one-click delete, anonymous sessions.
  - Observability: Sentry, PostHog, OTel traces.
- **Dependencies.** Labeled pilot gold set (from Phase 0), R2 + Fly + Neon accounts provisioned.
- **Risks.** White balance flaky on low-sclera photos (mitigation: eye-closed detection forces re-upload). Reliability calibration off on launch (mitigation: reliability bucket thresholds tuned post-launch from real sessions).
- **Do not build yet.** 12-season, accounts, recommendations, native apps, video, LLM reports, payments.

### Phase 2 — improved scoring / UX (weeks 9–16)

- **Goals.** Improve accuracy via learned components, improve UX post-result.
- **Deliverables.**
  - Fit inverse-covariance on accumulated labeled sessions (opt-in).
  - Optional logistic or XGBoost classifier on 4-D features; A/B against heuristic.
  - Filter detector trained on curated filter/raw pairs.
  - 12-season sub-type output (gated by reliability = High).
  - Save-by-email (magic link); shareable result URL.
  - Post-result survey ("does this sound like you?") closing the training loop.
- **Risks.** Self-reported labels are noisy (mitigation: only use alongside expert-labeled gold for training; treat self-label as weak supervision).

### Phase 3 — recommendations / monetization / advanced (weeks 17+)

- **Goals.** Monetize without breaking trust.
- **Deliverables.**
  - Recommendation engine: curated palette + affiliate-linked brand items matched on Lab distance to palette.
  - LLM-authored personalized written report ("your palette, in plain English") — LLM receives numeric features + season, never the raw image.
  - Native iOS (Capacitor first, then Swift if retention justifies).
  - Live-capture flow with a reference-card overlay for deterministic WB.
  - Premium tier: seasonal wardrobe auditing via closet photo uploads.
- **Risks.** Affiliate relationships biasing recommendations (mitigation: publish our matching algorithm; keep brand-agnostic default view).

---

## 14. Open questions / decision log

### Top unanswered questions

1. **Can we source 3 trained color analysts?** Without them we have no defensible gold set, and the whole "rigorous" positioning collapses. This is the #1 blocker.
2. **How bad is iPhone's per-region tone-mapping in practice?** Determines whether sclera-WB is sufficient or whether we need to prompt for a reference (e.g., "hold a plain white sheet of paper next to your face in one photo"). A/B early.
3. **What's our target region mix?** Fitzpatrick IV–VI need disproportionate gold-set coverage because most public color-analysis literature skews I–III. We need to plan for this explicitly.
4. **Anonymous-only vs accounts?** Anonymous for V1 is recommended. But if we want any longitudinal story (re-analyze in 6 months), we'll need identity. Confirm before we commit data model to "no user_id required."
5. **LLM role boundary.** Confirmed: no LLM for measurement. Not yet decided: is the "how we measured" narrative template-based in V1, or a guarded LLM pass from numeric inputs? Recommend templates in V1 (cheaper, deterministic, testable).

### Decisions to make before coding

- Final axes + prototypes in §5 (this memo locks them pending one more analyst review).
- TTLs (24 h / 7 d / 30 d) — confirm with legal if there's an advisor.
- Opt-in copy for feature retention ("may we keep anonymized measurements to improve the model?") — needs legal/privacy review.
- Whether to require ≥ 1 "reference frame" photo (white paper next to face) — biggest lever on color accuracy, highest UX cost.

### Decisions we can defer

- Payment processor (Phase 3).
- Native app framework (Phase 3).
- 12-season exact sub-type thresholds (scaffolded but unused in V1).
- Whether to self-host PostHog (only matters at scale).

### Biggest failure modes

- **Technical.** White balance doesn't work well enough on unconstrained phone selfies and every axis reads as noise. *Early mitigation:* ship Phase 1 with the reference-frame prompt as a toggleable "boost accuracy" option and measure variance with vs without.
- **Scientific.** Our own gold set's κ is too low to validate anything. *Early mitigation:* pilot Fleiss' κ on 20 subjects before building anything; if κ < 0.4, the product thesis needs rework.
- **Product.** TikTok users want a fun confident answer; our honest uncertainty feels like a bug, not a feature. *Early mitigation:* A/B result-screen framings; the "top-2 with reliability" presentation is hypothesis, not gospel.
- **Trust.** A single viral screenshot of an obviously wrong classification on a Black or brown-skinned user undoes the positioning. *Early mitigation:* skin-tone fairness metric is a release gate, not a dashboard.
- **Regulatory.** Biometric / facial analysis regulations (BIPA in Illinois, GDPR everywhere) apply even if we think of it as "color." Need counsel review before launch.

---

*End of memo. Ready for review, then ADRs for (a) axis definitions, (b) white-balance strategy, (c) retention policy.*
