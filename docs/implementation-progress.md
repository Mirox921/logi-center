# Reliability upgrade progress

## Baseline / preparation
- Baseline: v0.2.0, commit 64f232d; working tree clean. 16 baseline tests.
- Runtime: app.py (GTK + inline actions), backend.py (CLI + parsing), i18n.py, solaar_write.py. Installer is a fixed runtime file list. No cancellation or operation result model.
- Available: GTK/libadwaita, pyudev, pactl, parec/paplay and pw-record/pw-play. G502 HERO + G PRO X USB connected; G305/G515 absent. Reading can be tested; no physical writes/recording without deliberate action.
- Skill review: system installer/creator and existing Omarchy available; official catalog reviewed; no relevant additional package installed. Project workflow recorded in AGENTS.md and .agents/skills/logi-hardware-validation.

## Plan / status
1. Verification: implemented with documented limits; physical validation pending. Parameter-specific result states; cache vs device provenance; timeout/disconnect handling.
2. Backup/restore: implemented with documented limits; physical validation pending. Versioned checksummed export, compatibility validation, selected preview, pre-restore backup, partial results.
3. Discovery: implemented with documented limits; physical validation pending. Debounced udev / PulseAudio events, generation guards and lifecycle cleanup.
4. Mouse editor: implemented with documented limits; physical validation pending. Model layouts, key capture and actual macro view/edit, preserve old controls.
5. Audio: implemented with documented limits; physical validation pending. Split presets, opt-in live meter and temporary original/processed samples.
6. Diagnostics: implemented and tested. Typed faults, capability checks, redacted bounded logs + UI.

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

## Stage 4 implemented
- Added mouse_models.py / mouse_editor.py: G502 and G305 schematics + generic layout, selectable button regions, current action and macro events, direct key press/release capture, delay insertion/removal, draft reset and explicit apply.
- Macro validation rejects unbalanced keys and warns on desktop shortcuts. Existing assignment dropdowns remain. ratbag_dbus.py reads ActionTypes; unknown macro capability disables new macro writes rather than assuming support.
- 41 tests pass (layout, recording autorepeat, unbalanced keys, key mapping and conflict checks included). No button write performed on physical hardware. Full Wayland shortcut interception depends on compositor; UI explains the limit.
- Next: separate microphone/headphone presets, explicit audio meter and private temporary recording paths.

## Stage 5 implemented
- audio_pipeline.py + microphone_ui.py add explicitly started live meter, max-8-second original recording, playback and immediate/delete-on-exit temporary sample cleanup. No capture occurs during construction/refresh/smoke tests.
- A processed sample is captured only when a real EasyEffects source exists AND its capture stream is linked to the selected raw source. Otherwise the UI explicitly records original only. No fabricated before/after comparison.
- Headphones/microphone controls and presets are separate. Inspected upstream EasyEffects CLI: `-l name` loads both directions if names collide. Direction-specific managed aliases prevent that; last selections are saved independently. Readback remains marked backend cache, not proven audible DSP.
- 49 tests pass: opt-in invariant, missing microphone/backend, actual route check, preset name collision isolation, temporary cleanup, peak processing and synthetic PCM WAV encoding. No user microphone capture was started; real signal/meter/playback still need user-triggered hardware validation.
- Next: diagnosis window, useful fault-specific recovery, bounded redacted logs, final integration smoke and documentation.

## Stage 6 implemented; integration reviewed
- diagnostics.py adds component/device/backend-specific faults and recovery hints, read-only diagnostics dialog and rotating private redacted logs. Requested/actual macro values never enter logs. scripts/diagnose.py emits a safe report; scripts/check.py runs syntax + tests; scripts/gui_smoke.py exercises widgets without writes/capture.
- Fixed ratbag key/disabled parsing, quote handling, macro tap comparison, LED case normalization, readback failures and EasyEffects boolean bypass parsing. Injected runners no longer query real D-Bus capabilities. Restore reports now include readable statuses and fault/mismatch details.
- Fixed microphone preparation cancellation race and surfaced asynchronous playback failures. Mock test added for playback failure; GUI smoke covers cancellation before recording.
- 64 unit tests pass; compileall passes. Connected G502 read-only snapshot: 5 profiles, JSON write/read/validate and identical preview passed. Audio server snapshot validates. GUI editor/language smoke passed; expanded dialog/cancel smoke passed.
- No physical write/restore, USB unplug, G515/G305 reconnect or real microphone capture performed. Final constraints and file map: docs/reliability-upgrade.md. No system permission/config changes or external publication.
- Final: all runtime modules installed for current user and compared byte-for-byte with source. Documentation lists per-stage scope and pending physical checks. Local changes retained in logical commits; no release/push performed.

## Mouse illustration refinement
- Replaced generic capsule with model-specific Cairo vectors: angular G502 with thumb shelf/paddles and rounded wireless G305 with two side buttons. Added metal wheel/grip/panel details, isolated callouts, selected-only leader and direct diagram hit selection. The illustration explicitly does not claim live RGB color.
- Files: mouse_art.py (new shared renderer), mouse_editor.py, mouse_models.py, i18n.py, install.py, scripts/gui_smoke.py. GUI smoke now uses its own application ID so an already open app cannot absorb the test launch.
- Checked rendered G502/G305 PNG previews visually; 64 unit tests, compileall, diff check and independent live GTK smoke pass. No hardware writes or microphone capture. G305 physical device remains unavailable.

## Assignment label correction
- Fixed typed assignment matching: `button 1` was incorrectly compared with `1`, causing standard clicks to select the custom macro entry. Both assignment interfaces now share assignment_label; recognized macros compare equivalent tap/press-release forms.
- Files: mouse_models.py, mouse_editor.py, app.py, test_mouse_editor.py. 67 unit tests, compileall and diff check pass. Actual device assignments are unchanged.
