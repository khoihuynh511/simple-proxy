# Brief (verbatim, Vietnamese)

> làm 1 website batch tạo hình ảnh thẻ, lấy api từ Gemini, mục đích là để anh có
> thể batch tạo ảnh thẻ 1 lúc và ra 4 hình 1 lúc, chứ không phải dán từ hình vào
> ô chat rồi prompt để lấy từng hình về.
>
> Website đó hoạt động như 1 app có UX/UI clean gọn và làm đúng việc là được.

# Context gathered by the conductor (not part of the brief)

- "ảnh thẻ" = ID/passport-style portrait photo (Vietnamese usage: 3x4, 4x6 cm,
  plain white or blue background, formal attire, front-facing, head centred).
- Pain today: paste one photo into the Gemini chat, type a prompt, download one
  result, repeat. Goal: upload many photos once, get results in bulk.
- Gemini image models available (Oct 2026): `gemini-nano-banana-2.1`,
  `gemini-3.1-flash-image`, `gemini-3-pro-image` (higher fidelity, 1K/2K/4K),
  `gemini-2.5-flash-image`. API: `generativelanguage.googleapis.com`,
  `generateContent` with `responseModalities: ["IMAGE"]` and
  `imageConfig.aspectRatio` / `imageSize`, or the newer Interactions API.
  One request returns one image → 4 variants = 4 parallel requests.
- Greenfield app. Code will live in `apps/idphoto-batch/` of the current repo
  for now (relocation is a Gate A question).
- Single user (the owner), personal tool. Owner has their own Gemini API key.
