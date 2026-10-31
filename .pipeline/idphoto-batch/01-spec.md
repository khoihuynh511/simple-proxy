# Spec — idphoto-batch

## Problem
The owner makes Vietnamese ID/passport photos (ảnh thẻ) with Gemini by pasting one
portrait into the Gemini chat, typing a prompt, downloading one result, and repeating
for each person. With many photos this is slow and repetitive, and the output still
has to be cropped to the right print size by hand. He wants to upload many portraits
at once, get 4 candidate ảnh thẻ per portrait with no further input, pick the best
ones, and download them at the exact print size.

## Users & primary flow
Single user: the owner, on his own device, with his own Gemini API key. UI copy is
Vietnamese.

1. Opens the app. On first use he pastes his Gemini API key into Settings ("Cài đặt");
   the app checks it and remembers it on this device.
2. Drags 1–20 portrait photos onto the upload zone (or uses the file picker).
3. Picks output options: size preset (default 3x4), background (default trắng),
   attire (default giữ nguyên), optional extra instruction.
4. Reads the button label, e.g. "Tạo ảnh (40 lượt gọi API)", and clicks it.
5. Each photo shows a row of 4 variant slots. Each slot moves Đang chờ → Đang tạo →
   Xong, or → Lỗi with a reason. He clicks "Thử lại" on any failed slot, which
   re-runs only that slot.
6. He stars the variants he likes and clicks "Tải ZIP (n)". He can also download any
   single variant. Every file is a JPEG at the preset's exact pixel size, 300 DPI.

## Scope
- **In:**
  - Batch upload (drag-drop + picker) of JPEG/PNG/WebP, with limits and per-file
    rejection reasons.
  - Global output options: size preset, background colour, attire, free-text extra
    instruction, variants per photo (1–4, default 4), model, concurrency.
  - One Gemini `generateContent` request per variant. Requests go through a shared
    queue with a concurrency cap, automatic backoff on 429/503, and a key-error stop.
  - Status for each variant, manual retry or regenerate of a single variant, and a
    "Dừng" (stop) control for the batch.
  - API call count shown before running and a running counter of calls made.
  - Local crop and resize to the exact preset pixel size at 300 DPI. The model is
    never trusted for final dimensions.
  - Favourites, single-image download, and ZIP of the selected images, with
    deterministic ASCII filenames.
  - Browser-only app: the API key and photos go from the browser straight to
    Gemini; nothing is persisted except the key (if opted in) and settings.
  - Vietnamese UI copy.
- **Out:**
  - Accounts, multi-user, sharing, payments, a hosted backend or proxy (see Q2).
  - Print layout sheets (e.g. 10x15 cm paper tiled with 3x4 photos). Flagged as
    Q4. Not in v1 because it is additive and the stated pain is generation, not
    printing.
  - Face detection or automated compliance checks: head size/position, eyes open,
    glasses, background uniformity, identity similarity scoring.
  - Local background replacement or segmentation. Background colour comes only from
    the prompt.
  - Manual crop or position adjustment of a result. v1 uses a centred crop; the user
    chooses among 4 variants instead.
  - Per-photo option overrides. Options are global and are snapshotted when a photo
    is queued (see FR-07). Different options mean another run.
  - HEIC/HEIF, RAW, and TIFF input. iOS Safari's picker already converts HEIC to
    JPEG; desktop HEIC files are rejected with a "convert to JPG" message.
  - Persisting photos/results across reloads (no IndexedDB history), and batch
    history.
  - USD cost estimates. Prices change, so v1 shows call counts only.
  - Gemini Interactions API, Batch API (async, 24h), and streaming. Only synchronous
    `generateContent`.
  - Editing the prompt template in the UI, beyond the extra-instruction field.
  - English or other UI languages.

## Functional requirements
- **FR-01 Upload.** Drag-drop zone plus file picker (`multiple`). Accepted:
  JPEG/PNG/WebP, judged by decoded content and not by extension alone. Each file is at
  most 15 MB, with a short edge of at least 300 px. At most 20 photos are in the
  workspace at once. Rejected files are listed with a Vietnamese reason; accepted
  files are still added. A photo that has not been generated yet can be removed
  ("Xoá").
- **FR-02 Pre-processing.** Before sending, each source is decoded, EXIF-orientation
  corrected, downscaled so its long edge is at most 2048 px (never upscaled), and
  re-encoded as JPEG. This drops EXIF/GPS metadata.
- **FR-03 Options.** The options are:
  - Size preset: 2x3, 3x4, 4x6, 35x45 (mm). Default 3x4.
  - Background: trắng (#FFFFFF) or xanh (#4A90E2). Default trắng.
  - Attire: giữ nguyên / vest công sở / áo sơ mi trắng. Default giữ nguyên.
  - Extra instruction: 0–300 chars, default empty.
  - Variants per photo: 1–4, default 4.
  - Model: `gemini-3.1-flash-image` (default), `gemini-3-pro-image`,
    `gemini-nano-banana-2.1`, `gemini-2.5-flash-image`.
  - Concurrency: 1–8, default 4.

  All options except the extra instruction persist across reloads.
- **FR-04 Prompt.** Each request is built from the fixed template in *Interfaces*.
  It always includes the identity-preservation clause verbatim and the selected
  preset, background, and attire. The extra instruction is appended verbatim when
  it is not empty.
- **FR-05 Request.** One `generateContent` call per variant, carrying the
  pre-processed source image inline and the prompt. It requests image output and the
  preset's mapped aspect ratio (table in *Interfaces*).
- **FR-06 Queue & concurrency.** All variant jobs go into one FIFO queue, ordered by
  photo upload order and then variant index. At most `concurrency` requests are in
  flight. With the default settings, one photo's 4 variants run concurrently.
- **FR-07 Run.** "Tạo ảnh" enqueues every photo that has no variants yet, using a
  snapshot of the current options. Photos that already have variants are not
  re-queued. Changing options later does not affect already-queued or finished
  jobs. Retries use the original snapshot.
- **FR-08 Status.** Each variant has exactly one of these states: `queued` (Đang chờ),
  `running` (Đang tạo), `done` (Xong), `failed` (Lỗi). A failed variant shows a
  short Vietnamese reason. While a variant waits on automatic backoff it stays
  `running` and shows "Đang chờ do giới hạn API…".
- **FR-09 Automatic retry.** On HTTP 429 or 503 the job is retried up to 3 times.
  The delay is the server's retry hint (`Retry-After` header or `RetryInfo.retryDelay`)
  if present, otherwise 2 s, 4 s, then 8 s. While a 429 backoff is pending, the queue
  starts no new jobs. Once all retries are spent the variant is `failed`. Other
  errors (400, 500, network, timeout of 120 s) fail at once with no auto retry.
- **FR-10 Key errors stop the batch.** HTTP 401/403, or a 400 whose error reason is
  `API_KEY_INVALID`, marks that variant failed and moves all `queued` variants to
  `failed` with reason "API key không hợp lệ". It also shows a banner linking to
  Settings. No further requests are sent until the user starts something again.
- **FR-11 No-image response.** A 200 response with no inline image part (for
  example, a safety block) marks the variant `failed`, with the finish reason in the
  message. There is no auto retry.
- **FR-12 Manual retry/regenerate.** A `failed` variant has "Thử lại"; a `done`
  variant has "Tạo lại". Either one re-enqueues only that variant, with its original
  snapshot. The sibling variants' images and states stay untouched. A regenerated
  variant drops its favourite mark.
- **FR-13 Stop.** "Dừng" moves all `queued` variants to `failed` with reason
  "Đã dừng" (retryable). It aborts in-flight requests, which also become `failed`
  "Đã dừng".
- **FR-14 Cost visibility.** Before running, the button label shows the number of
  calls the run will make: (number of photos to run) × (variants per photo). A
  header counter "Đã gọi API: N" counts every `generateContent` HTTP request sent
  this session, including automatic and manual retries.
- **FR-15 Local finishing.** Each returned image is cropped to the preset's exact
  aspect ratio (centred), resized to the preset's pixel size at 300 DPI (table in
  *Interfaces*), and encoded as JPEG (quality 0.92) with 300×300 DPI density
  metadata. The finished JPEG is what gets shown and downloaded.
- **FR-16 Favourites & download.** Each `done` variant has a star toggle and a
  single-download button. "Tải ZIP (n)" downloads a flat ZIP with exactly the n
  starred images. It is disabled when n = 0. "Bỏ chọn" clears all stars.
- **FR-17 Filenames.** Each file is named
  `<base>_<preset>_<bg>_v<k>.jpg`.
  - `<base>`: the source filename without its extension. Vietnamese diacritics are
    removed (đ→d, Đ→D), runs of characters outside `[A-Za-z0-9_-]` become a single
    `-`, leading and trailing `-` are trimmed, and an empty result becomes `anh`.
    If two sources produce the same base, the later one gets `-2`, `-3`, and so on.
  - `<preset>` ∈ {2x3, 3x4, 4x6, 35x45}; `<bg>` ∈ {trang, xanh}; `k` ∈ 1–4 is the
    variant index. Preset and bg come from the photo's snapshot.
  - The ZIP is named `anh-the_YYYYMMDD-HHmm.zip` (local time).
- **FR-18 API key.** A masked input in Settings, with a "Ghi nhớ trên máy này"
  checkbox (default on: key in `localStorage`; off: memory only) and "Xoá key".
  On save, the key is checked with one model-metadata GET request; this is not
  counted in FR-14. The key is sent only in the `x-goog-api-key` header to
  `generativelanguage.googleapis.com`, never in a URL or to any other host.
  "Tạo ảnh" is disabled while no key is set.
- **FR-19 Privacy.** Photos and results live only in page memory. Nothing is written
  to localStorage, IndexedDB, cookies, or a server, except the key (FR-18) and the
  options (FR-03). The app makes no network requests except to its own origin (static
  assets) and `generativelanguage.googleapis.com`: no analytics, external fonts, or
  CDNs. A one-line notice under the upload zone says photos are sent only to Google
  Gemini and are not stored. If there are in-flight requests or `done` variants,
  leaving or reloading the page triggers the browser's leave-page confirmation.
- **FR-20 Vietnamese UI.** All user-visible labels, statuses, and errors are in
  Vietnamese, using at least the strings listed in *Interfaces*.

## Acceptance criteria
All ACs run against a mocked Gemini endpoint (request interception). No AC needs a
real key or network.

- **AC-01** (FR-01) — Given an empty workspace, when 3 files are dropped (`a.jpg`
  2 MB JPEG, `b.png` 1 MB PNG, `c.gif` GIF), then 2 photo cards appear (a, b). The
  rejection list shows `c.gif` with a reason containing "định dạng".
- **AC-02** (FR-01) — Given an empty workspace, when a 16 MB JPEG and a
  200×250 px JPEG are picked, then neither is added. Each gets a rejection reason,
  mentioning "15 MB" and "300 px" respectively.
- **AC-03** (FR-01) — Given 18 photos in the workspace, when 5 more valid files are
  dropped, then exactly 2 are added (total 20). The other 3 are listed as rejected
  with a reason containing "20".
- **AC-04** (FR-02) — Given a 4000×3000 JPEG with EXIF orientation 6 and GPS tags,
  when its variants are requested, then the inline image in each request body decodes
  to a 1536×2048 JPEG (portrait, long edge 2048) with no EXIF GPS block.
- **AC-05** (FR-02) — Given an 800×1000 PNG, when requested, then the inline image is
  an 800×1000 JPEG (not upscaled).
- **AC-06** (FR-03) — Given a fresh profile, when the app loads, then the defaults are
  3x4, trắng, giữ nguyên, 4 variants, `gemini-3.1-flash-image`, concurrency 4. Given
  the user picks 4x6 + xanh + concurrency 2 and reloads, then those values are still
  selected and the extra-instruction field is empty.
- **AC-07** (FR-04) — Given options 35x45 + xanh + áo sơ mi trắng + extra "đeo kính",
  when a request is sent, then its text part contains the identity clause verbatim
  (from *Interfaces*), "35 x 45 mm", "#4A90E2", "white dress shirt", and the exact
  substring "đeo kính".
- **AC-08** (FR-04) — Given an empty extra instruction, when a request is sent, then
  the text part contains no "Additional instruction" line.
- **AC-09** (FR-05) — For each preset (2x3, 3x4, 4x6, 35x45), when a request is sent,
  then it targets `…/v1beta/models/<selected model>:generateContent` with
  `generationConfig.responseModalities` = `["IMAGE"]` and
  `generationConfig.imageConfig.aspectRatio` equal to `2:3`, `3:4`, `2:3`, and `4:5`
  respectively.
- **AC-10** (FR-06, FR-07) — Given 3 photos, 4 variants, concurrency 4, and a mock
  that holds every response open, when "Tạo ảnh" is clicked, then exactly 4 requests
  are in flight, all for photo 1, and 8 variants show "Đang chờ". When one request
  completes, then exactly one new request starts, for photo 2 variant 1.
- **AC-11** (FR-07) — Given photo A finished with 3x4 + trắng, when the user switches
  to 4x6 + xanh, adds photo B, and clicks "Tạo ảnh", then requests are sent only for
  B (4 requests) and use 4x6/xanh. A's files are still named `…_3x4_trang_v<k>.jpg`.
- **AC-12** (FR-08) — Given a running batch, then every variant slot shows exactly one
  of "Đang chờ", "Đang tạo", "Xong", "Lỗi", matching its state. A failed slot shows a
  non-empty reason.
- **AC-13** (FR-09) — Given a mock that returns 429 with `Retry-After: 3` once and then
  200, and fake timers, when one variant runs, then the second request is sent no
  sooner than 3 s after the first. No other queued job starts during those 3 s. The
  variant ends `done`. "Đã gọi API" increases by 2.
- **AC-14** (FR-09) — Given a mock that always returns 503 with no retry hint, when one
  variant runs, then exactly 4 requests are sent, at roughly t = 0, 2, 6, and 14 s
  (fake timers, ±100 ms), and the variant ends `failed`.
- **AC-15** (FR-09) — Given a mock returning 500 once, when one variant runs, then
  exactly 1 request is sent and the variant is `failed`.
- **AC-16** (FR-10) — Given 2 photos × 4 variants, concurrency 1, and a mock returning
  400 with `reason: "API_KEY_INVALID"`, when "Tạo ảnh" is clicked, then exactly 1
  request is sent. All 8 variants become `failed`, the 7 never-sent ones with reason
  "API key không hợp lệ", and a banner with a link to "Cài đặt" is visible.
- **AC-17** (FR-11) — Given a mock returning 200 with
  `candidates[0].finishReason = "IMAGE_SAFETY"` and no inline image part, when a
  variant runs, then it is `failed`, its reason contains "IMAGE_SAFETY", and exactly
  1 request was sent.
- **AC-18** (FR-12) — Given a photo with variants 1, 2, and 4 `done` and variant 3
  `failed`, when "Thử lại" is clicked on variant 3, then exactly 1 new request is
  sent. Variants 1, 2, and 4 keep their state, and their image bytes are identical to
  before. Variant 3 becomes `done` on mock success.
- **AC-19** (FR-12) — Given a `done` and starred variant 2, when "Tạo lại" is clicked,
  then exactly 1 request is sent, variant 2 is unstarred, and after success its image
  bytes differ from before (mock returns a different image).
- **AC-20** (FR-13) — Given 2 photos × 4 variants, concurrency 4, and responses held
  open, when "Dừng" is clicked, then the 4 in-flight requests are aborted. All 8
  variants are `failed` with reason "Đã dừng", no further requests are sent, and each
  shows "Thử lại".
- **AC-21** (FR-14) — Given 5 photos with no variants and variants per photo = 4, then
  the run button reads "Tạo ảnh (20 lượt gọi API)". With variants per photo = 2, it
  reads "Tạo ảnh (10 lượt gọi API)". Given 0 runnable photos or no key, the button is
  disabled.
- **AC-22** (FR-14) — Given a fresh session, when 1 photo × 4 variants runs, with one
  variant getting a 429 then 200, and then one manual "Tạo lại", then the header shows
  "Đã gọi API: 6". The key check from FR-18 is not counted.
- **AC-23** (FR-15) — Given a mock returning an 896×1152 PNG, when the variant
  finishes, then the downloaded file is a JPEG whose pixel size (W×H) is exactly
  236×354 for 2x3, 354×472 for 3x4, 472×709 for 4x6, and 413×531 for 35x45. Its JFIF
  density is 300×300 DPI.
- **AC-24** (FR-15) — Given a mock returning a 1024×1024 image whose left 25% and
  right 25% are pure red and whose centre 50% is pure green, with preset 3x4, then the
  output is 354×472 and all four corner pixels are within ΔE<10 of green (proving a
  centred crop, not a squash).
- **AC-25** (FR-16) — Given 2 photos with 4 `done` variants each, when variants 1 and
  3 of photo 1 and variant 2 of photo 2 are starred, then the button reads
  "Tải ZIP (3)". Clicking it downloads a ZIP with exactly those 3 JPEG entries, no
  directories. Given 0 stars, the button is disabled.
- **AC-26** (FR-16) — Given a `done` variant, when its single-download button is
  clicked, then one JPEG is downloaded with the FR-17 filename and the same bytes as
  the in-app image.
- **AC-27** (FR-17) — Given sources `Ảnh Nguyễn Văn Đức.jpg`, `???.png`, and
  `chan-dung.webp` twice (in that upload order), with preset 3x4 and bg trắng, then
  variant 2 filenames are `Anh-Nguyen-Van-Duc_3x4_trang_v2.jpg`,
  `anh_3x4_trang_v2.jpg`, `chan-dung_3x4_trang_v2.jpg`, and
  `chan-dung-2_3x4_trang_v2.jpg`.
- **AC-28** (FR-17) — Given the clock at 2026-11-02 09:05 local, when a ZIP is
  downloaded, then its name is `anh-the_20261102-0905.zip`.
- **AC-29** (FR-18) — Given a key is entered with "Ghi nhớ trên máy này" on and
  saved, when the page reloads, then the key is still set. Given the box is off, after
  reload no key is set and `localStorage` contains no key. "Xoá key" removes it from
  `localStorage` and memory.
- **AC-30** (FR-18) — Given a key `TESTKEY123`, when a batch runs, then every
  `generateContent` request carries header `x-goog-api-key: TESTKEY123`. No request
  URL to any host contains `TESTKEY123`, and no request to any host other than
  `generativelanguage.googleapis.com` contains it in headers or body.
- **AC-31** (FR-18) — Given the key check returns 400 `API_KEY_INVALID` on save, then
  Settings shows "API key không hợp lệ" and the key is not stored.
- **AC-32** (FR-19) — Given a full flow (load, set key, upload 2 photos, run, star,
  download ZIP) with all network traffic recorded, then every request host is either
  the app origin or `generativelanguage.googleapis.com`.
- **AC-33** (FR-19) — After the AC-32 flow, `localStorage`, `sessionStorage`,
  IndexedDB, and cookies contain no image data (no value longer than 2 KB and no
  `data:image` / base64 JPEG/PNG signature). The only stored keys are those listed in
  *Interfaces*.
- **AC-34** (FR-19) — Given at least one `done` variant, when the page tries to unload,
  then a `beforeunload` handler calls `preventDefault()`. Given an empty workspace, it
  does not.
- **AC-35** (FR-20) — Given the main screen, then the strings "Tải ảnh lên",
  "Tạo ảnh", "Cài đặt", "Dừng", and "Bỏ chọn" are visible, plus a disabled
  "Tải ZIP (0)". The privacy notice contains "Gemini" and "không lưu".
- **AC-36** (NFR) — The repo-root `package.json` and `pnpm-lock.yaml` are
  byte-identical to `base_sha` (`44c0483`). Root `pnpm install --frozen-lockfile`,
  `pnpm lint`, and `pnpm build` succeed as they do on `base_sha`.
- **AC-37** (NFR) — At a 375 px wide viewport with 20 photos loaded, the document has
  no horizontal scroll (`scrollWidth <= clientWidth`).

## Non-functional
- **Runtime:** a static, client-only web app (HTML/JS/CSS) with no server component.
  It runs from a local dev/preview command and can be deployed to any static host.
- **Browsers:** current Chrome, Edge, and Safari (desktop), plus iOS Safari. Layout
  works at 375 px wide or more (AC-37).
- **Self-contained:** lives in its own folder (default `apps/idphoto-batch/`, see Q3)
  with its own package manifest and lockfile. Root CI, lint, and build are unaffected
  (AC-36).
- **Bundle:** production JS is 300 KB gzipped or less.
- **Local finishing time:** crop + resize + encode of one variant takes 300 ms or
  less, measured in the browser test as the median over 20 runs.
- **Tests:** all tests use a mocked Gemini endpoint. CI makes zero real API calls.
- **Timeouts:** each `generateContent` request is aborted after 120 s (FR-09).

## Interfaces

**Gemini request (one per variant):**
```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent
x-goog-api-key: <key>
Content-Type: application/json

{
  "contents": [{ "role": "user", "parts": [
    { "inlineData": { "mimeType": "image/jpeg", "data": "<base64 of FR-02 output>" } },
    { "text": "<prompt from template>" }
  ]}],
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "imageConfig": { "aspectRatio": "3:4" }
  }
}
```
The result image comes from the first `candidates[0].content.parts[*].inlineData`.

**Presets (300 DPI, px = round(mm / 25.4 × 300)):**

| Preset | mm (W×H) | Output px (W×H) | aspectRatio sent | Prompt size text |
|---|---|---|---|---|
| 2x3   | 20×30 | 236×354 | 2:3 | "2 x 3 cm" |
| 3x4   | 30×40 | 354×472 | 3:4 | "3 x 4 cm" |
| 4x6   | 40×60 | 472×709 | 2:3 | "4 x 6 cm" |
| 35x45 | 35×45 | 413×531 | 4:5 | "35 x 45 mm" |

**Option → prompt fragments:**
- bg trắng → `plain uniform pure white background (#FFFFFF)`; bg xanh →
  `plain uniform light blue background (#4A90E2)`.
- attire giữ nguyên → `Keep the original clothing.`; vest công sở →
  `Dress the person in a dark formal business suit with a white shirt.`; áo sơ mi
  trắng → `Dress the person in a plain white dress shirt with a collar.`

**Prompt template** (English for model reliability; `{…}` = fragments above):
```
Create a formal ID / passport photo of the person in the input image, size {sizeText}, portrait orientation.
IDENTITY: Keep the person's face exactly identical to the input photo — same facial features, face shape, eyes, nose, mouth, skin tone, age and hairline. Do not beautify, slim, smooth, or alter the face in any way.
Framing: front-facing, head and top of shoulders, head centred horizontally, eyes level, face occupying about 70% of the image height from chin to top of hair, small even margin above the head.
Background: {bgFragment}, no shadows, no gradient, no objects.
Clothing: {attireFragment}
Lighting: soft, even studio lighting on the face, natural colours, sharp focus.
Output a single photo only, no borders, no text, no watermark.
Additional instruction: {extra}
```
The last line is present only when the extra instruction is not empty. The
`IDENTITY:` line is the "identity clause" that AC-07 checks verbatim.

**Browser storage keys (the only ones allowed, AC-33):**
- `idphoto.apiKey` — string, present only when "Ghi nhớ" is on.
- `idphoto.settings` — JSON, for example
  `{"preset":"3x4","bg":"trang","attire":"keep","variants":4,"model":"gemini-3.1-flash-image","concurrency":4}`.

**Required Vietnamese UI strings:**
- Tải ảnh lên
- Tạo ảnh (N lượt gọi API)
- Cài đặt
- Dừng
- Đang chờ
- Đang tạo
- Xong
- Lỗi
- Thử lại
- Tạo lại
- Tải ZIP (n)
- Bỏ chọn
- Xoá
- Đã gọi API: N
- API key không hợp lệ
- Đã dừng
- Đang chờ do giới hạn API…
- Ghi nhớ trên máy này
- Xoá key
- Privacy notice: "Ảnh chỉ được gửi tới Google Gemini để tạo ảnh thẻ, ứng dụng không lưu ảnh."

**Filenames:** `<base>_<preset>_<bg>_v<k>.jpg`, for example
`Anh-Nguyen-Van-Duc_3x4_trang_v2.jpg`. ZIP: `anh-the_YYYYMMDD-HHmm.zip`.

## Open questions
1. **What does "ra 4 hình 1 lúc" mean: 4 candidate images per source photo, or 4
   source photos processed at a time (1 result each)?**
   - **Default if unanswered:** 4 variants per source photo. "Variants per photo"
     (1–4) and "concurrency" are settings anyway, so the other reading works by
     setting variants = 1 and concurrency = 4.
   - **Impact if wrong:** low. Only the defaults and the per-photo grid layout change.
2. **Key handling: browser-only static app (key entered in the browser, calls made
   from the browser) or a tiny local server holding the key in `.env`?**
   - **Default if unanswered:** browser-only.
   - **Why:**
     - There is no server to run or secure, and photos never touch a third machine,
       which makes FR-19 trivially true.
     - The app keeps working when deployed as a static site, for example on the
       owner's phone.
     - A hosted server holding the key would need auth, or anyone with the URL could
       spend the key. Auth is explicitly out of scope.
     - The key never leaves the owner's device and goes only to Google. The owner
       should restrict the key to the Generative Language API in Google Cloud.
   - **Impact if wrong:** moderate. If the owner wants to share the app with people
     who have no key, a server plus auth is needed. That replaces the API-calling
     module and adds hosting; the UI and finishing code are unaffected.
3. **Where does the code live: `apps/idphoto-batch/` in this repo (`simple-proxy`, an
   unrelated nitro proxy with its own CI/Docker/deploy workflows) or a new repo?**
   - **Default if unanswered:** `apps/idphoto-batch/`, fully self-contained, with the
     root untouched (AC-36).
   - **Impact if wrong:** low. Moving later is a `git mv` plus adding a CI file. One
     side effect: the root Docker build context will include the folder unless it is
     added to `.dockerignore`.
4. **Do you need a print sheet in v1, for example a 10x15 cm (4R) sheet tiled with
   several copies of one ảnh thẻ, ready for a photo shop?**
   - **Default if unanswered:** no, not in v1 (Scope Out).
   - **Impact if wrong:** low-moderate. It is an additive export (one layout function
     and one button) that reuses the FR-15 output, so nothing in v1 is reworked.

## Decisions
<!-- Filled by the conductor after Gate A. -->
