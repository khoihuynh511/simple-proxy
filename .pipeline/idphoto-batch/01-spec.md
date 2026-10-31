# Spec — idphoto-batch (v2, lean)

## Problem
The owner makes Vietnamese ID photos (ảnh thẻ) with Gemini one at a time:
paste a portrait into the chat, prompt, download, repeat. He wants to drop many
portraits at once, get 4 candidates per portrait, keep each result in two
forms — the full-quality original and a light submission copy that public
service portals accept — and download what he picks in bulk.

## Users & primary flow
Single user (the owner) with his own Gemini API key. Vietnamese UI.

1. First use: paste the API key in *Cài đặt*; it is checked and remembered.
2. Drop 1–20 portraits. Pick size preset, background, attire, prompt preset,
   optional extra instruction.
3. Button reads "Tạo ảnh (40 lượt gọi API)" → click.
4. Each portrait gets 4 slots: Đang chờ → Đang tạo → Xong / Lỗi. Retry or
   regenerate any single slot.
5. Star favourites → download a ZIP of the *hồ sơ* copies, the *gốc* originals,
   or both. Any single file can be downloaded too.

## Scope
- **In:** batch upload; global options; prompt presets loaded from a file in
  the repo; 4 concurrent variants per photo via Gemini `generateContent`;
  queue with concurrency cap, backoff, stop; per-variant retry/regenerate;
  call counter; two outputs per variant (gốc + hồ sơ); favourites; single and
  ZIP download; browser-only, nothing stored except key and settings.
- **Out (v1):**
  - Print sheets. **v2 candidate:** portrait sheets **15x21 cm** and
    **21x30 cm** tiled with one photo, built from the *gốc* file at 300 DPI.
  - Accounts, server/proxy, hosting with shared key.
  - Face detection / compliance checks, manual crop, local background
    replacement, per-photo options, HEIC input, history across reloads,
    USD estimates, editing prompt presets in the UI.

## Functional requirements
- **FR-01 Upload.** Drag-drop + picker. JPEG/PNG/WebP (by content), ≤15 MB,
  short edge ≥300 px, ≤20 photos in the workspace. Rejected files listed with
  a Vietnamese reason. Before sending: EXIF-orient, downscale to long edge
  ≤2048 px (never upscale), re-encode JPEG (drops GPS).
- **FR-02 Options** (persist across reloads, except extra instruction):
  - Size preset: 2x3, 3x4, **4x6** (default), 35x45 mm.
  - Background: trắng `#FFFFFF` / xanh **`#54A3FF`** (default xanh).
  - Attire: giữ nguyên (default) / vest công sở / áo sơ mi trắng.
  - Prompt preset: from the prompt library (FR-04). Default: first entry.
  - Extra instruction: 0–300 chars.
  - Model: **`gemini-3-pro-image`** (default), `gemini-nano-banana-2.1`,
    `gemini-3.1-flash-image`.
  - Thinking: **Cao** (default) / Thấp — sent as the model's thinking level.
  - Output resolution: **2K** (default) / 4K.
  - Variants per photo: 1–4 (default 4). Concurrency: 1–8 (default 4).
  - Hồ sơ copy: width **750 px** (allowed 700–800), max size **700 KB**
    (or 1 MB).
- **FR-03 Request.** One `generateContent` per variant: source image inline +
  prompt text; image output; preset's aspect ratio; selected resolution and
  thinking level. Key only in header `x-goog-api-key`, only to
  `generativelanguage.googleapis.com`.
- **FR-04 Prompt library.** Presets live in one file in the repo
  (`prompts/` — exact format in plan), each with id, Vietnamese name and a
  template with placeholders `{{size}}`, `{{background}}`, `{{attire}}`,
  `{{extra}}`. Placeholders are filled from the options; an empty extra
  removes its whole line. Ships with one default preset (template in
  *Interfaces*) until the owner supplies his "Ultimate" set.
- **FR-05 Queue.** One FIFO queue (photo order, then variant). ≤`concurrency`
  in flight. "Tạo ảnh" queues photos with no variants yet, snapshotting the
  options; retries reuse the snapshot.
- **FR-06 Errors.** 429/503 → up to 3 retries (server hint, else 2/4/8 s; no
  new jobs start during a 429 wait). Invalid key (401/403/`API_KEY_INVALID`)
  → stop the batch, banner to *Cài đặt*. 200 without an image (e.g. safety)
  → failed with the finish reason. Other errors and 120 s timeout → failed.
- **FR-07 Controls.** "Thử lại" on a failed variant, "Tạo lại" on a done one:
  re-runs only that variant. "Dừng" aborts in-flight and fails the queued ones
  ("Đã dừng", retryable). Header shows "Đã gọi API: N" (every request).
- **FR-08 Two outputs per variant.**
  - **Gốc:** the exact bytes Gemini returned, unmodified, with the extension
    from its MIME type (normally `.png`).
  - **Hồ sơ:** centre-crop of the gốc to the preset's exact ratio, resized to
    the configured width, JPEG, quality chosen as the highest that fits under
    the size cap.
- **FR-09 Download.** Star toggle per done variant. "Tải ZIP (n)" with a
  choice *Hồ sơ* (default) / *Gốc* / *Cả hai*; flat ZIP
  `anh-the_YYYYMMDD-HHmm.zip`. Per-variant buttons for each copy.
  Filenames: `<base>_<preset>_<bg>_v<k>_hoso.jpg` and `…_v<k>_goc.png`;
  `<base>` = source name without diacritics, non-`[A-Za-z0-9_-]` runs → `-`,
  empty → `anh`, duplicates → `-2`, `-3`.
- **FR-10 Privacy.** Photos/results only in page memory (as Blobs). Storage
  holds only `idphoto.apiKey` (if "Ghi nhớ" is on) and `idphoto.settings`.
  No network except own origin and Gemini. Leaving with results asks to
  confirm. Notice under upload zone: "Ảnh chỉ được gửi tới Google Gemini để
  tạo ảnh thẻ, ứng dụng không lưu ảnh."

## Acceptance criteria
<!-- 15 / cap 15. All run against a mocked Gemini endpoint. -->
- **AC-01** (FR-01) — Dropping `a.jpg`, `b.png`, `c.gif`, a 16 MB JPEG and a
  200×250 JPEG adds exactly a and b; the other three are listed with reasons
  mentioning format, "15 MB" and "300 px". A 21st valid photo is rejected
  with a reason mentioning "20".
- **AC-02** (FR-03, FR-05) — 3 photos × 4 variants, concurrency 4, responses
  held: button read "Tạo ảnh (12 lượt gọi API)"; exactly 4 requests in
  flight, all photo 1; completing one starts exactly photo 2 variant 1.
- **AC-03** (FR-03) — Each request targets `…/models/gemini-3-pro-image:generateContent`
  by default, has image output, aspect ratio 2:3 / 3:4 / 2:3 / 4:5 for
  2x3 / 3x4 / 4x6 / 35x45, the selected resolution and thinking level, and
  header `x-goog-api-key`; the key appears in no URL and in no request to
  another host.
- **AC-04** (FR-04) — With preset template containing all four placeholders
  and options 35x45 + xanh + sơ mi + extra "đeo kính", the request text has
  every placeholder replaced (`#54A3FF`, size text, attire text, "đeo kính")
  and no `{{`. With empty extra, the extra line is absent.
- **AC-05** (FR-06) — 429 with `Retry-After: 3` then 200: second request ≥3 s
  later, no other job starts meanwhile, variant done, counter +2. 503 always:
  4 requests at ~0/2/6/14 s then failed. 500 once: 1 request, failed.
- **AC-06** (FR-06) — `API_KEY_INVALID` on the first request (2 photos × 4,
  concurrency 1): exactly 1 request sent, all 8 failed with "API key không
  hợp lệ", banner linking to *Cài đặt* visible.
- **AC-07** (FR-06) — 200 with `finishReason: IMAGE_SAFETY` and no image:
  variant failed, reason contains "IMAGE_SAFETY", 1 request.
- **AC-08** (FR-07) — Variants 1, 2, 4 done and 3 failed: "Thử lại" on 3
  sends 1 request; 1, 2, 4 keep identical bytes. "Tạo lại" on a starred done
  variant sends 1 request, unstars it, and replaces its bytes.
- **AC-09** (FR-07) — 2 photos × 4, concurrency 4, held: "Dừng" aborts the 4
  in flight; all 8 failed "Đã dừng" with "Thử lại"; no further requests.
- **AC-10** (FR-08) — Mock returns a PNG: the *gốc* download is byte-identical
  to the mock's image and named `…_goc.png`.
- **AC-11** (FR-08) — Mock returns a 2048×2048 high-detail noise PNG
  (≈7 MB): for every preset, *hồ sơ* is a JPEG exactly 750 px wide, height =
  round(750 × preset H/W), ≤700 KB; with width 800 and cap 1 MB it is 800 px
  wide and ≤1 MB.
- **AC-12** (FR-08) — Mock image with red outer quarters left/right and green
  centre, preset 3x4: all four corner pixels of *hồ sơ* are green (ΔE<15) —
  centre crop, not squash.
- **AC-13** (FR-09) — Sources `Ảnh Nguyễn Văn Đức.jpg`, `???.png`,
  `chan-dung.webp` ×2, 3 starred variants: ZIP *Hồ sơ* has exactly 3 `.jpg`
  entries; *Cả hai* has 6; names follow FR-09 (`Anh-Nguyen-Van-Duc_4x6_xanh_v2_hoso.jpg`,
  `anh_…`, `chan-dung_…`, `chan-dung-2_…`); ZIP name matches the clock.
  0 stars → ZIP disabled.
- **AC-14** (FR-02, FR-10) — Options persist across reload (extra resets);
  defaults on a fresh profile are 4x6, xanh, giữ nguyên, first prompt preset,
  `gemini-3-pro-image`, Cao, 2K, 4 variants, concurrency 4, 750 px, 700 KB.
  Key: kept after reload with "Ghi nhớ" on, gone with it off; "Xoá key"
  removes it.
- **AC-15** (FR-10) — Full flow with traffic recorded: every request host is
  the app origin or `generativelanguage.googleapis.com`; afterwards storage
  holds only the two allowed keys and no image data; with results present,
  `beforeunload` is prevented.

## Non-functional
- Static client-only app, own repo, runs with one dev command; deployable to
  any static host.
- Current Chrome/Edge/Safari desktop + iOS Safari; no horizontal scroll at
  375 px (checked via tester screenshots).
- Memory: 20 × 4 × ~7 MB gốc ≈ 560 MB worst case — keep results as Blobs,
  render thumbnails from the hồ sơ copy, revoke object URLs on removal.
- Hồ sơ encode ≤500 ms per variant on desktop (median).
- Tests use a mocked Gemini endpoint; CI makes zero real calls.

## Interfaces
**Request (one per variant):**
```
POST https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent
x-goog-api-key: <key>

{
  "contents": [{ "role": "user", "parts": [
    { "inlineData": { "mimeType": "image/jpeg", "data": "<base64>" } },
    { "text": "<filled prompt>" } ] }],
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "imageConfig": { "aspectRatio": "2:3", "imageSize": "2K" },
    "thinkingConfig": { "thinkingLevel": "high" }
  }
}
```
Plan must verify the exact field names for image size and thinking level
against the current Gemini docs for each listed model; if a model rejects a
field, omit it for that model only.

**Presets:** 2x3 → 2:3 "2 x 3 cm"; 3x4 → 3:4 "3 x 4 cm"; 4x6 → 2:3
"4 x 6 cm"; 35x45 → 4:5 (crop to 7:9) "35 x 45 mm".

**Fragments:** trắng → `plain uniform pure white background (#FFFFFF)`;
xanh → `plain uniform light blue background (#54A3FF)`. Attire: giữ nguyên →
`Keep the original clothing.`; vest → `Dress the person in a dark formal
business suit with a white shirt.`; sơ mi → `Dress the person in a plain white
dress shirt with a collar.`

**Default prompt preset** (placeholder until the owner's Ultimate set):
```
Create a formal ID photo of the person in the input image, size {{size}}, portrait orientation.
IDENTITY: Keep the person's face exactly identical to the input photo — same facial features, face shape, eyes, nose, mouth, skin tone, age and hairline. Do not beautify, slim, smooth, or alter the face in any way.
Framing: front-facing, head and top of shoulders, head centred, eyes level, face about 70% of image height from chin to top of hair, small even margin above the head.
Background: {{background}}, no shadows, no gradient, no objects.
Clothing: {{attire}}
Lighting: soft, even studio lighting, natural colours, sharp focus.
Output a single photo only, no borders, no text, no watermark.
Additional instruction: {{extra}}
```

**UI strings (Vietnamese):** Tải ảnh lên · Tạo ảnh (N lượt gọi API) · Cài đặt ·
Dừng · Đang chờ · Đang tạo · Xong · Lỗi · Thử lại · Tạo lại · Tải ZIP (n) ·
Hồ sơ / Gốc / Cả hai · Bỏ chọn · Xoá · Đã gọi API: N · API key không hợp lệ ·
Đã dừng · Đang chờ do giới hạn API… · Ghi nhớ trên máy này · Xoá key.

## Open questions
None blocking. Pending input: the owner's "Ultimate" prompt set (FR-04).

## Decisions
- 2026-10-31 Gate A (owner):
  - "4 hình" = 4 variants per photo.
  - Browser-only static app, key entered in the browser.
  - Own repo, not inside `simple-proxy`.
  - Print sheet → v2, portrait 15x21 cm and 21x30 cm.
  - Default model Pro with high thinking; blue `#54A3FF`.
  - Two outputs: untouched gốc (PNG, ~6–7 MB) + light hồ sơ (JPEG
    700–800 px wide, ≤700 KB–1 MB) for public-service portals.
  - AC set cut from 37 to 15.
