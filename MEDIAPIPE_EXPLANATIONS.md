# MediaPipe Explanations (Technical + Non-Technical)

## Technical Explanation: How MediaPipe Face Landmarker Works

MediaPipe Face Landmarker is a multi-stage ML pipeline:

1. **Face detection**
- A lightweight detector model finds the face region in the full image.

2. **Landmark inference**
- A face mesh model runs on the cropped face and predicts dense 3D face landmarks (including iris landmarks in the full output set).
- In this codebase, landmark outputs are used to compute:
  - Face bounding box
  - Left/right eye centers

3. **Optional extra heads**
- The model can also output blendshape/expression scores and face transformation matrices.
- In this implementation, those are disabled because we only need geometry points for region masking.

4. **Post-processing for analysis**
- Landmark coordinates are converted from normalized model space into image pixel space.
- Those coordinates are then used to build masks for regions like cheeks, forehead, iris, sclera, and hair.

At runtime in this project:
- The `.task` model is downloaded once and cached locally.
- A singleton landmarker instance is reused for subsequent images.
- If initialization/inference cannot run, landmark detection returns `None` and the pipeline handles that path safely.

## Non-Technical Explanation (TikTok Audience)

Think of MediaPipe like a super-fast face map engine:

1. It finds your face.
2. It drops hundreds of tiny points on important features (eyes, nose, lips, jawline).
3. That creates a 3D-ish face map.
4. We use that map to sample color from the right places, not random background pixels.

So it works like an invisible AR filter that measures your face structure first, then reads color in a more reliable way.

## How Colors Become "Seasons"

After we have face-aligned color samples, the pipeline converts them into four style signals:

1. **Warmth**: warm/golden vs cool/pink-blue
2. **Value**: light vs deep
3. **Chroma**: bright/clear vs muted/soft
4. **Contrast**: low vs high difference between features (for example skin vs hair)

Then:

1. It compares your 4-signal profile to season prototypes (Spring, Summer, Autumn, Winter).
2. The closest match is the primary season.
3. The second closest is runner-up.
4. Reliability is scored from photo quality + cross-photo consistency + classification margin.

In short:

**Face map -> region color sampling -> 4 color signals -> nearest season profile.**
