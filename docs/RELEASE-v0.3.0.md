# Logi Center v0.3.0 — Reliability, backups and visual mouse editor

A substantial public preview update to the existing Linux control panel for Logitech G305, G502 HERO, G515 LIGHTSPEED TKL and wired G PRO X. This is a **pre-release**: automated and read-only checks pass, while hardware writes, restores, reconnects and voice capture still need broader physical validation.

## 1. Honest application results

- A shared operation model distinguishes **confirmed**, **sent without confirmation**, **mismatch**, **error**, **disconnected** and **cancelled**.
- Supported parameter-specific getters compare requested and observed values, including audio volume tolerance. Mismatches show both values.
- libratbag's G502 profile/RGB properties are explicitly labelled **backend cache**. A matching cache value is never presented as proof of the visible LED color.
- Unsupported readback, transport failures, deadlines and cancellation receive explicit results. Sidetone and unsupported keyboard RGB getters are not invented.

## 2. Device backup and guarded restoration

- Export supported profiles, DPI stages, polling rate, button actions/macros, lighting and supported audio/keyboard fields as versioned JSON with model identifiers, creation date, provenance and SHA-256.
- Validate structure, integrity, model compatibility and allowlisted actions before restoring. A checksum detects corruption; it is not a signature.
- Preview changes, select categories, save a private pre-restore snapshot and stop on the first mismatch/failure. Stale previews are rejected; partial results include individual outcomes.
- These are **supported backend-field backups, not firmware images**. Mouse values may be cached; G515 data is saved Solaar configuration. Unsupported independent channel-volume restoration is skipped. There is no speculative automatic rollback over a failed connection.

## 3. Connection and lifecycle handling

- udev and PulseAudio events trigger debounced refreshes; optional pyudev has a five-second sysfs fallback.
- Disconnected controls are disabled, old operations cancelled and late results discarded. Selection, tab and scroll position are preserved where possible.
- **Fixed stale “Connected via USB” for an unplugged G502**: the remembered model is separate from connection state. Backend failures mean unknown connectivity; an empty device list means offline.
- Explicit executor/subscription shutdown and bounded radio-keyboard polling.

## 4. Redesigned visual mouse editor

- Separate vector silhouettes for angular **G502 HERO** and rounded wireless **G305**, with a generic fallback for other layouts.
- Numbered controls, selected-only guide line, highlighted selection and direct selection on the illustration. The diagram does not claim to show live RGB.
- Current assignment, predefined actions, explicit keyboard recording, macro event/delay editing, validation, desktop-shortcut warnings and draft reset. Macro writing is enabled only when ratbag reports the capability.
- Existing assignment controls remain available.
- **Fixed standard clicks incorrectly selecting “Custom macro”**; both interfaces now share typed matching for clicks, special actions, keys and known macros.

![G502 and G305 vector illustrations](https://github.com/Mirox921/logi-center/raw/v0.3.0/docs/illustrations/mouse-layouts.png)

These are renderer previews with example selection, not screenshots of connected G305 hardware or live RGB readings.

## 5. Microphone and headphone workflows

- Separate input/output preset lists and independently saved selections. Managed direction-specific EasyEffects names prevent same-name presets loading both pipelines.
- An explicitly started microphone level meter, short recording (up to eight seconds), playback and deletion.
- Original/processed clips are offered only when an actual EasyEffects capture route from the selected microphone is detected; otherwise only the original is recorded. Streams may have different latency.
- No recording on startup. Clips are temporary and removed on refresh, disconnect, deletion or exit.
- Missing microphones/backends, access failures and playback errors are surfaced. Cancelled preparation cannot start a delayed recording.

## 6. Diagnostics and development

- A diagnostics window distinguishes missing/unavailable components, access permissions, unsupported device/backend operations, disconnects, communication errors, configuration and internal faults, with recovery suggestions.
- Bounded private rotating logs redact sensitive identifiers and omit assignment/macro values; backup/log files use private permissions.
- Business logic, execution, discovery, backup, audio and drawing modules are separated from GTK integration; writes are serialized outside the UI thread.
- Russian/English UI coverage, reusable check/diagnostic/GUI scripts, CI syntax checks, project instructions and implementation progress documentation.

## Validation

- **69 automated tests pass**, covering verification/mismatch/unavailable readback, cancellation/timeouts, mock reconnects, corrupt/incompatible backups, partial restore, missing backends/microphones, preset isolation, privacy and parsing regressions.
- Syntax compilation and whitespace checks pass. Independent GTK smoke covers widgets, language, dialogs, cancelled recording preparation and the unplugged-header regression, without device writes or microphone capture.
- Connected G502 read-only inspection validated five profiles and JSON export/read/unchanged-preview. Audio-server snapshots validated.
- **Not physically verified in this cycle:** writing G502 RGB/DPI/buttons/macros, hardware restore, rapid physical reconnects, G305/G515 behavior, real voice recording/playback or reboot persistence. No optical RGB measurement is available.

## Install or update

Install the [documented dependencies](https://github.com/Mirox921/logi-center/blob/v0.3.0/README.md), download **logi-center-0.3.0.tar.gz**, extract it, and run:

```sh
python install.py
```

Close an already open Logi Center window before reopening the updated app. The per-user installer retains existing preferences; it does not change system permissions or udev rules. Optional `python-pyudev` enables udev monitoring; `parec` and `paplay` provide test capture/playback. Arch Linux/Wayland was used for desktop checks; other distributions remain unverified.

Verify the attached archive beside `SHA256SUMS`:

```sh
sha256sum -c SHA256SUMS
```

GitHub's automatic source archives are separate and are not covered by this checksum file. Full implementation details: [reliability report](https://github.com/Mirox921/logi-center/blob/v0.3.0/docs/reliability-upgrade.md). This is an independent community project, without original Blue VO!CE/DTS, firmware updates or a full G HUB replacement.

## По-русски

Новая предварительная версия включает все шесть направлений улучшений:

- Честные статусы применения: подтверждено, отправлено без подтверждения, несовпадение, ошибка, отключение и отмена. Кэш G502 не выдаётся за фактический цвет подсветки.
- JSON-копии с проверкой целостности/модели, предпросмотром, выбором категорий, защитной копией и отчётом о частичном восстановлении. Это не полная копия памяти устройства.
- Автообнаружение подключений, отмена устаревших операций и исправление ложного USB-статуса после отключения G502.
- Новые силуэты G502/G305, интерактивный выбор кнопок, запись клавиш, поддерживаемые макросы и отмена черновика. Исправлено ошибочное «Собственный макрос» вместо ЛКМ/ПКМ.
- Раздельные пресеты микрофона/наушников, индикатор уровня, запись до восьми секунд и прослушивание реально доступных трактов. Запуск — только кнопкой; образцы временные.
- Диагностика компонентов, понятные ошибки, приватные журналы и архитектурное разделение модулей.

**69 тестов проходят**, проверка GTK выполнена без аппаратных записей и захвата голоса. Физическое применение настроек, восстановление, переподключение, запись/воспроизведение микрофона и перезагрузка ещё требуют проверки; G305/G515 во время разработки отсутствовали. Поэтому релиз помечен **Pre-release**.

Для установки/обновления скачай архив `logi-center-0.3.0.tar.gz`, распакуй и выполни `python install.py`, затем перезапусти приложение. Существующие предпочтения сохраняются. Подробные ограничения и проверки перечислены в отчёте выше.
