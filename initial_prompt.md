You are helping me design a consumer app for personal seasonal color analysis (Spring / Summer / Autumn / Winter, with possible 12-season expansion).

Your task in this step is NOT to build the app yet. Your task is to produce a comprehensive, opinionated architecture plan for the app, with enough specificity that we could then implement it cleanly.

Important context:
- Target user: a style-curious consumer, likely a woman aged ~20–35 discovering color analysis via TikTok
- Product promise: easy to use, but rigorous and trustworthy
- Core UX: user uploads multiple photos (likely 10–15), app analyzes them, and returns likely season(s), confidence, and explanation
- Positioning: science-informed, analytics-based, no gimmicks
- Very important: do NOT rely on an LLM for the actual color measurement
- LLMs may be used later for explanation, report generation, or recommendations, but not for the raw measurement/classification pipeline
- The app should ideally be free to the user initially; monetization may come later via affiliate / brand partnerships or premium add-ons
- We want the architecture to support strong privacy, debuggability, and future iteration

What I want from you:
Create a detailed architecture plan covering product architecture, technical architecture, analysis pipeline, scoring framework, data model, APIs, infrastructure, privacy, testing, and implementation roadmap.

Please think carefully and make explicit decisions. Do not stay generic.

Deliverables:
1. Executive summary
   - summary of the recommended architecture
   - key design principles
   - biggest technical risks
   - recommended MVP scope vs later phases

2. Product assumptions
   - user journey from landing page through upload through result screen
   - constraints and assumptions about user behavior
   - what “good” means for the product
   - explicit non-goals for V1

3. System architecture
   - recommend a concrete stack for:
     - frontend
     - backend/API
     - async jobs
     - file storage
     - database
     - auth (if any)
     - analytics/observability
     - deployment
   - explain why each choice is recommended

4. Computer vision / analysis architecture
   Design the actual analysis pipeline in detail.
   It should include:
   - photo upload and preprocessing
   - photo quality screening
   - face detection
   - facial landmarking / segmentation
   - region selection for skin / hair / eye sampling
   - color normalization strategy
   - feature extraction
   - multi-image aggregation
   - season classification logic
   - confidence scoring
   - failure handling / “insufficient quality” outcomes

   Important constraints:
   - no LLM for raw measurement
   - prefer deterministic, inspectable CV / image-processing methods first
   - the system should be explainable and debuggable
   - the final classification should be based on measurable dimensions like:
     - warmth / coolness
     - value / depth
     - chroma / softness
     - contrast
   - classify to top 2 likely seasons, not only 1
   - include a reliability score for the analysis

5. Proposed scoring framework
   Since there is no single universal public “official scorecard,” I want you to propose one.
   Build an internal scorecard for the app, including:
   - measurable dimensions
   - how each dimension is computed
   - how scores are normalized across multiple images
   - how confidence is calculated
   - how dimensions map into 4-season and optionally 12-season outputs
   - proposed formulas / pseudocode for the scoring logic
   - which parts should be heuristics vs learned later from data

   Be concrete. I want an actual framework, not vague prose.

6. Privacy / safety / trust architecture
   - what user photos are stored, for how long, and why
   - recommended deletion / retention policy
   - whether to support anonymous usage initially
   - how to message uncertainty honestly
   - how to avoid overclaiming scientific certainty
   - what disclaimers or user guidance should exist around lighting, makeup, filters, and photo quality

7. Data model
   Propose a backend schema / entities for:
   - user
   - analysis session
   - uploaded photo(s)
   - photo quality result
   - extracted features
   - aggregated analysis result
   - season classification result
   - recommendations
   - audit / debug artifacts

   Include:
   - key fields
   - relationships
   - what should be persisted vs ephemeral

8. API design
   Propose initial API endpoints for the MVP, including:
   - upload photos
   - create analysis session
   - run analysis
   - check job status
   - fetch results
   - fetch debug / trace info for internal admin use
   - delete session / photos

   Include request/response shapes at a high level.

9. Repo / codebase plan
   Propose a clean repository structure for implementation.
   Include:
   - directory structure
   - major modules/services
   - where the CV pipeline should live
   - where shared types should live
   - how to separate business logic from transport/UI logic
   - recommended config and secrets handling
   - whether monorepo is preferred

10. Third-party library recommendations
   Recommend concrete libraries/tools for:
   - face detection / landmarks
   - image manipulation
   - background jobs
   - API framework
   - object storage
   - ORM
   - frontend upload flow
   - monitoring
   - testing

   For each, explain:
   - why it fits
   - maturity / risk
   - why it is better than obvious alternatives for this use case

11. Infrastructure / deployment plan
   - local development setup
   - staging environment
   - production environment
   - CI/CD
   - secrets management
   - logging / tracing / metrics
   - cost-conscious setup for an MVP
   - scaling considerations if the app suddenly goes viral

12. Testing / evaluation plan
   Propose a robust testing plan, including:
   - unit tests
   - integration tests
   - CV pipeline tests
   - image-fixture tests
   - regression tests for scoring
   - manual QA workflow
   - offline evaluation dataset strategy
   - how to measure accuracy, consistency, and failure rates

   I especially want to know:
   - how we should build a small gold-standard evaluation set
   - how we should compare model outputs vs human-labeled outcomes
   - how to test robustness across lighting and photo quality conditions

13. Roadmap
   Break implementation into phases:
   - Phase 0: architecture / design
   - Phase 1: MVP
   - Phase 2: improved scoring / UX
   - Phase 3: recommendations / monetization / advanced features

   For each phase include:
   - goals
   - deliverables
   - dependencies
   - risks
   - what should NOT be built yet

14. Open questions / decision log
   End with:
   - top unanswered questions
   - decisions we should make before coding
   - decisions we can defer
   - biggest ways this could fail technically or as a product

Output format requirements:
- Write the architecture plan as a serious internal technical memo
- Be concise but concrete
- Do not write production code yet
- Do not hand-wave the CV pipeline
- Do not propose “just use GPT vision to classify the season”
- Explicitly call out assumptions and uncertainty
- Where useful, include “recommended”, “alternative”, and “deferred” choices