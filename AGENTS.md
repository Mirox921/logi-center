# Working on Logi Center

Python 3 / GTK4 / libadwaita Linux desktop application. `app.py` owns the UI; `backend.py` contains legacy CLI/read adapters. New operation/backup/discovery/audio modules separate hardware work from widgets. `i18n.py` contains Russian → English translations. `install.py` copies runtime modules into the user's data directory. Tests run without hardware using injectable runners/transports.

- Read `docs/implementation-progress.md` when continuing; inspect only affected code and diffs.
- Run `python -m unittest -v`; syntax: `python -m compileall -q .`. GUI smoke requires a live desktop: `python app.py --smoke` (no writes or recording).
- Changes to runtime modules require updating the installer and CI checks. Keep Russian and English UI usable.
- All hardware writes require explicit UI action. Exit code zero means sent, not verified. Readback needs backend/parameter-specific support; cached libratbag/Solaar values are not optical RGB confirmation.
- Never use full `solaar config/show` enumeration on app startup: this build may trigger RGB shutdown cleanup. Use cached settings + isolated ROOT ping. Do not modify installed backend packages.
- Do not change udev rules, global configuration or permissions. Do not record audio without explicit user action; test clips must be temporary and cleaned up.
- Backups must label device reads vs daemon cache vs local preferences, validate device model and checksum before writing, save pre-restore state, and report partial/unverified outcomes honestly.
- Serialize writes; use generation/cancellation guards for disconnects, rebinds and shutdown. No subprocess waits on GTK's main thread.
- Keep raw HID identifiers, user paths, tokens and recordings out of diagnostic reports/repository. Existing private backups are outside the project.
- No new release or external publication is implied by a code change. Keep logical local commits; preserve unrelated working changes.

Universal architecture: `devices.py` adapter registry/capability inventory; `device_ui.py` shared presentation; `drafts.py` private base/desired state; `reports.py` allowlisted public JSON; `solaar_adapter.py` explicit scalar probes. Read `docs/universal-progress.md` for this cycle. `--simulate` must stay isolated from real command execution. Never merge units by model/VID/PID alone; require exact physical identity or unique candidates/selectors. Drafts and submitted-unverified values must survive refresh. Arch recipe is local; `scripts/prepare-arch.py` supplies a checksummed source archive, never installs.
