# VIBE pipeline — hướng dẫn nhanh

Pipeline nhiều agent cho dự án vibe:
**brief → specify → plan → tasks → execute → test ∥ review → feedback → fix**, lặp theo round.

## Chạy

```bash
claude --agent conductor          # main thread = conductor (Opus, effort high)
> Tool CLI đổi tên hàng loạt file ảnh theo EXIF date, có dry-run
```

Hoặc trong session bất kỳ:

```
/vibe <brief> [--auto] [--rounds 5]
/vibe resume <slug>
/vibe status
```

`--auto` bỏ qua Gate A (duyệt spec). Mặc định **3 round** fix.

## Dự án đang có sẵn (brownfield)

```
/vibe adopt                  # 1 lần: trinh sát, dựng baseline, đo test coverage
/vibe fix bugs.md            # xử lý lô bug / yêu cầu sửa tồn đọng
/vibe roadmap ROADMAP.md     # cắt roadmap thành milestone, chạy lần lượt
```

Thứ tự khuyến nghị: **adopt → safety-net tests → fix → roadmap**.

## Đội hình

- **conductor** — Opus · high — điều phối, giữ gate, không tự code
- **scout** — Haiku · low — trinh sát repo, lấy lệnh build/test
- **analyst** — Opus · high — brief → spec + acceptance criteria
- **architect** — Opus · high — plan + task graph theo wave, re-plan khi kẹt
- **builder** — Sonnet · medium — code từng task, chạy song song trong wave
- **tester** — Sonnet · medium — test mù theo spec, không đọc log builder
- **reviewer** — Opus · high — review read-only, finding có bằng chứng
- **fixer** — Sonnet · high — root cause + regression test

Đổi model/effort: sửa `model:` / `effort:` trong `.claude/agents/<tên>.md`.

## Vòng lặp

```
brief ─▶ analyst ─▶ [Gate A: anh duyệt spec]
      ─▶ architect ─▶ tasks (wave 1..n)
      ─▶ builder × N (song song, file tách rời) ─▶ commit mỗi wave
      ┌▶ tester ∥ reviewer
      │      ▼
      │  feedback (conductor gom must-fix)
      │      ├─ sạch ─▶ [Gate B: anh Ship / góp ý / sửa thêm]
      │      ├─ kẹt 2 round ─▶ architect re-plan
      └──────┴─ còn lỗi ─▶ fixer × N ─▶ round+1
                                        ▼ (hết round) ─▶ báo anh quyết
      close ─▶ đúc rule vào .pipeline/LESSONS.md (anh duyệt)
```

## Artifact

Mỗi run nằm ở `.pipeline/<slug>/`: `01-spec.md`, `02-plan.md`, `03-tasks.md`,
`rounds/rN/{test-report,review,feedback}.md`, `state.json` (resume được khi crash).

## Mang sang project khác

Copy `.claude/agents/`, `.claude/skills/vibe/`, `.pipeline/LESSONS.md`
(hoặc đặt vào `~/.claude/` để dùng cho mọi repo).
