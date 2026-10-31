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

## Đội hình (v2 — 4 agent)

- **conductor** — Opus · high — trinh sát, viết spec + plan, điều phối, giữ gate, re-plan, đúc rule
- **builder** — Sonnet · high — code task; chế độ fix: root cause + regression test
- **tester** — Sonnet · medium — test mù theo spec, chụp màn hình UI, mock API trả phí
- **reviewer** — Opus · high — review read-only, finding có bằng chứng

Mỗi vai tồn tại vì thêm được thứ vai khác không làm được: **quyết · làm · kiểm hành vi · kiểm chất lượng**.

Tier: **Lite** (conductor → builder → reviewer, ≤6 AC) · **Standard** (đủ 4, ≤15 AC).
Lớn hơn → cắt milestone bằng `roadmap`, không thêm agent.

## Vòng lặp

```
brief ─▶ conductor: spec ─▶ [Gate A: anh duyệt]
      ─▶ conductor: plan + tasks
      ─▶ builder: wave 1 = khung UI bấm được ─▶ [mini-gate: anh xem ảnh chụp]
      ─▶ builder: các wave còn lại, commit mỗi wave
      ┌▶ tester ∥ reviewer
      │      ▼
      │  conductor gom feedback
      │      ├─ sạch ─▶ [Gate B: Ship / góp ý / sửa thêm]
      │      ├─ kẹt 2 round ─▶ conductor re-plan
      └──────┴─ còn lỗi ─▶ builder (fix mode) ─▶ round+1
      close ─▶ đúc rule vào .pipeline/LESSONS.md (anh duyệt)
```

## Artifact

Mỗi run nằm ở `.pipeline/<slug>/`: `01-spec.md`, `02-plan.md`, `03-tasks.md`,
`rounds/rN/{test-report,review,feedback}.md`, `state.json` (resume được khi crash).

## Mang sang project khác

Copy `.claude/agents/`, `.claude/skills/vibe/`, `.pipeline/LESSONS.md`
(hoặc đặt vào `~/.claude/` để dùng cho mọi repo).
