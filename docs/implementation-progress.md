# Reliability upgrade progress

## Baseline / preparation
- Baseline: v0.2.0, commit 64f232d; working tree clean. 16 baseline tests.
- Runtime: app.py (GTK + inline actions), backend.py (CLI + parsing), i18n.py, solaar_write.py. Installer is a fixed runtime file list. No cancellation or operation result model.
- Available: GTK/libadwaita, pyudev, pactl, parec/paplay and pw-record/pw-play. G502 HERO + G PRO X USB connected; G305/G515 absent. Reading can be tested; no physical writes/recording without deliberate action.
- Skill review: system installer/creator and existing Omarchy available; official catalog being checked. Project workflow recorded in AGENTS.md and .agents/skills/logi-hardware-validation.

## Plan / status
1. Verification: pending. Parameter-specific result states; cache vs device provenance; timeout/disconnect handling.
2. Backup/restore: pending. Versioned checksummed export, compatibility validation, selected preview, pre-restore backup, partial results.
3. Discovery: pending. Debounced udev / PulseAudio events, generation guards and lifecycle cleanup.
4. Mouse editor: pending. Model layouts, key capture and actual macro view/edit, preserve old controls.
5. Audio: pending. Split presets, opt-in live meter and temporary original/processed samples.
6. Diagnostics: pending. Typed faults, capability checks, redacted bounded logs + UI.

## Audit findings
- Generic success on exit code; direct raw RGB writes; no readback policy.
- Main executor never shut down, UI rebuilds can race with queued callbacks.
- CLI profile data can be backend cache; hardware RGB previously differed physically.
- Solaar saved settings are local, not hardware snapshots.
- Presets combined by filename; global bypass affects both directions.
- All button key mappings lack visual editing and direct key capture.

Update after each stage with changed files, checks, limits and next action. Do not call mock tests hardware tests.

## Stage 1 implemented
- Added execution.py (typed faults, process deadlines/cancellation), operations.py (plans, observations, five result states + cancellation).
- UI writes now report verified / sent without verification / mismatch / fault / disconnected instead of generic success; profile/DPI/RGB paths included.
- Parameter policies: PulseAudio live server volume/mute/default; G515 live brightness only; G502 daemon cache is explicitly unverified even when matching; RGB cache mismatch reports requested and returned values; sidetone/RGB/timers without getter stay unverified.
- 26 tests pass (10 new operation tests), including mismatch, unavailable readback, disconnect, missing backend, cancellation and real subprocess timeout. No device writes made.
- Limits: libratbag does not expose optical LED state; retained provenance. UI generation/cancellation integration remains for stage 3.
- Next: versioned backup/restore with typed allowlisted actions and pre-restore safety snapshot.

## Stage 2 implemented
- Added backups.py: versioned JSON + SHA-256, model/type validation, typed allowlisted restore actions, per-category preview, pre-restore safety snapshot, stale-preview rejection and partial outcome report.
- Mouse captures supported profiles/macros/DPI/LED data as backend_cache; G515 exports local_saved_settings; audio exports audio_server values. Files are private and never execute embedded commands.
- Added export/restore controls for mouse, keyboard and audio. Restore stops at first mismatch/error/disconnect; no speculative automatic rollback over a failed transport. Safety snapshot can be restored explicitly.
- 33 tests pass, including corrupt input, incompatible model, unsafe action, partial restore, selection and changed-since-preview abort. Hardware restore not performed.
- Limits: not a full firmware image; independent audio channel restoration is skipped rather than flattened. Device-specific unsupported writes remain diagnosed by backend results.
- Next: event-based discovery, stale-task guards, cancellation and resource lifecycle.

## Stage 3 implemented
- discovery.py adds udev add/remove monitoring and a PulseAudio subscription (restart bounded at 5 seconds); cheap sysfs fallback only when udev unavailable.
- Debounced refresh preserves tab/scroll/selected mouse, deduplicates devices, blocks stale controls, invalidates old tokens and terminates cancellable command processes. Late results are ignored. Radio keyboard polling stays bounded at 30 seconds and reenables controls on reconnect.
- Executor and subscriptions have explicit shutdown. Old mouse selection/refresh callbacks use revision checks.
- 37 tests pass; inspected the installed pyudev callback signature and corrected to one Device argument. Mock rapid disconnect/reconnect and cancellation checked. Physical unplug/replug not exercised.
- Next: model-aware visual mouse editor and real key/macro capture.
