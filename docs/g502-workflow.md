# G502 artwork, button editor and macro workflow

2026-10-28. GTK remains the default. No unattended physical writes.

## Implemented

- Four user-supplied SVGs copied unchanged; Dashboard and editor share the
  top asset. Top/side choice is independent of connection-based cable variant.
  Existing project art remains available. Resource hashes: `exact/g502-inputs.sha256`.
- Eight upper controls and three thumb controls have independent named
  callouts and click anchors, preserving native ratbag IDs 0–10. The mechanical
  wheel-release control is not assignable. Geometry lives in `mouse_models`,
  outside QML. Aspect ratios are 1103/2048 and 999/359.
- A compact header in the G502 button editor leaves space for its diagram.
  Scrollable controls remain reachable at 640 px; desktop uses two columns.
- Initial async ratbag discovery reads supported settings, so the Dashboard
  need not wait for a device editor to open before showing settings.
- Native/daemon profile synchronization and stale-profile safeguards: see
  [g502-rgb.md](g502-rgb.md). LED observations remain daemon-cache evidence.
- A separate modal macro window captures keyboard events before controls can
  activate. Physical scan codes cover Cyrillic-layout input, letters, modifiers,
  punctuation, navigation and function keys. Auto-repeat is ignored; held keys
  are balanced on Stop/deactivation. Mouse clicks are captured only in the
  labelled capture surface, leaving Stop/Close usable. System Wayland shortcuts
  can still be intercepted by the compositor; no global input grab is added.
- Named reusable macros use the existing private DraftStore, with validated
  tokens, bounded length/count, atomic storage and protected malformed-library
  handling. Per-device/profile/button drafts and native Apply/Cancel remain.

## Limitations

The original top SVGs use clipPath and rgba gradient stops which Qt
misrendered as black fields. Qt compatibility copies now restore the intended
contour and gradients while retaining the LC mark; the supplied files remain
unchanged. See [g502-svg-compatibility.md](g502-svg-compatibility.md). The wireless-style SVG is not independently
verified against an actual wireless unit. G502 X geometry/firmware is excluded.
User-supplied SVG authorship/license is not established; see asset SOURCES.md.

Mouse clicks are recorded and retained in the local library. The existing
backup/operation macro format and G502 HID++ driver do not establish verified
mouse-button-event playback. Such a hardware macro is explicitly blocked with
an explanation; keyboard-only native macros retain the existing backend path.
No alternate input driver/background macro service was introduced. Neither
real button reassignment nor new physical macro playback was tested.

## Verification and visual review

Screenshots: `docs/screenshots/g502-workflow/`; mocked G502 state, RU/EN,
640×780 and 1280×800. Supplied SVGs were opened after Qt SVG rendering.
Primary review found wheel anchor overlap risk (20 px targets at closer
centres), insufficient room under the large header, and a recorder-window lifecycle/checking issue. Targets are now distinct 12 px markers
with full named buttons, header is compact only in this editor, and the
recorder uses an ApplicationWindow with explicit content parenting. The smoke
now addresses its actual window rather than another hidden instance, and
refreshes the PySide window wrapper after event delivery.

Focused smoke clicks every label and anchor in both connection variants,
checks SVG loading/aspect ratios, and exercises Space/letters/navigation/F5/
punctuation/mouse events in the modal recorder, Stop and balanced tokens.
Read-only profile observation was performed on the real wired G502; other
new actions are mocked. Actual validation output is in `g502-workflow-checks.md`.

Final software validation: 446 tests passed (`scripts/check.py`, includes
compileall); qmllint/QML smoke passed; fake-I/O matrix saved 32 screenshots.
Native GTK GUI smoke and 15-scenario simulation passed. Peripheral snapshot
smoke stopped with `Widget snapshot not ready`, despite a mapped/realized
window; no success is claimed for that script. Final screenshots were opened
and reviewed. The originally reported dark fields were subsequently traced to unsupported
Qt SVG features and corrected with compatibility copies; long panels use vertical scrolling, and no interactive controls were
hidden to pass the click checks. Fresh Arch source archive was prepared and
runtime resources compared byte-for-byte; no package was installed.

Final guard review additionally pins the submitted button profile before
queuing work: a newer hardware observation cannot retarget its validation
to another profile while leaving the old command queued. The regression test
blocks the executor, changes the observed profile, and proves no write occurs.
The 68 relevant editor/mouse/workflow tests passed after this narrow fix.
