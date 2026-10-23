---
name: logi-hardware-validation
description: Implement and validate Logi Center hardware operations, recovery and GTK integration, with protocol-specific readback and no unsolicited device writes. Use for this project's device-control changes.
---

Read AGENTS.md and docs/implementation-progress.md in the project root, then inspect the targeted adapter and tests.

- Inject command runners in operation tests. Test mismatch, unavailable readback, disconnected device and timeout separately; success exit status is not a confirmed setting.
- G502 libratbag properties may be daemon cache: retain this provenance and do not claim optical color verification. Solaar YAML is local history, not hardware readback. Sidetone readback is capability-dependent.
- Before restore, validate schema/model/digest and preserve an independent pre-restore snapshot. Allowlisted typed actions only; never execute commands embedded in a backup.
- GUI changes must preserve generation guards and close resources on disconnect/shutdown. Audio capture is opt-in and temporary.
- Run relevant tests first, then full suite for integration. Log only redacted fault classifications. Record actual hardware checks and unresolved limits in the progress file.

- For multi-device changes, inspect devices.py and docs/universal-progress.md. Unknown capability differs from unsupported; merge only reliable identities and route a write once. Preserve private drafts separately from observations. Simulation evidence never upgrades to hardware evidence; public reports use the allowlist in reports.py.

- Optional providers run in sdk_worker.py; test fake public API objects as well as the shared Plan path. Do not turn SDK cache into hardware confirmation. MCHOSE read recovery must never send a profile write; retain per-connection selectors and unrelated-byte checks. ckb-next metadata discovery does not authorize FIFO writes. Test RGB ownership guards on legacy restoration, not just visible controls. See docs/backend-support.md for the source audit and denied physical K7 access.
