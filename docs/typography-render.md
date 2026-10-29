# QML text rendering investigation — 2026-10-26

The color fringe was reproduced on Qt 6.12 / Hyprland Wayland / OpenGL. The window used a fractional device pixel ratio (the compositor's baseline is 1.25 on the capture output; another window was placed at 2.0). No `QT_SCALE_FACTOR`, `QSG_RHI_BACKEND` or `QT_QUICK_BACKEND` override was active in the normal application. `QT_SCALE_FACTOR_ROUNDING_POLICY` was unset and Qt reported `PassThrough`. `python app.py --ui qml --simulate --smoke --debug-text` now prints these values, the actual Qt font family/style/size/hinting/render path, TrueType hint table lengths, Cyrillic coverage, and the count of labels on fractional device coordinates. It prints no device IDs.

The bundled Noto Sans regular/bold and JetBrainsMono Nerd Font are registered and used, rather than silently falling back. `fc-query` returned raw fontversion values 132055 (Noto Sans Regular) and 150994 (JetBrainsMono Nerd Font Regular). QRawFont reports nonempty `fpgm`, `prep`, `cvt ` and `gasp` TrueType tables, including `prep` 261/214 bytes and `gasp` 8 bytes for Noto/JetBrains. Both fonts cover Latin A–Z/a–z, Cyrillic А–я and Ё/ё (`scripts/check_fonts.py`). FontTools was absent locally, so Qt's QRawFont inspected the tables. Nothing in this evidence suggests a broken font file or weak/missing TrueType hint instructions. License/source details remain in `qml_ui/assets/fonts/SOURCES.md`.

The Qt 6 scenegraph source defaults distance-field glyphs to **HighQualitySubPixelAntialiasing** and recognizes `QSG_DISTANCEFIELD_ANTIALIASING=gray`: [Qt implementation](https://codebrowser.dev/qt6/qtdeclarative/src/quick/scenegraph/qsgdefaultcontext.cpp.html). The initial Dashboard viewport also had `layer.enabled: true`; resampling its texture could further roughen small glyphs at fractional scales. Other device cards animate background color or artwork position, not text scale/rotation/opacity; no text is under a ShaderEffect. Some layout items have fractional scene positions at 125%; that is a secondary source of thickness variation. The Flickable now requests pixel-aligned scrolling. Globally adding a Translate to every text element was tested, but it left some nested layout items unsnapped and made placement more fragile, so it was dropped. The grayscale glyph path removes the observed color fringe without shifting layout.

## Two review cycles

1. Explicit `Text.QtRendering` with `Font.PreferNoHinting`, 12 px minimum mono captions, and direct-window Dashboard drawing was captured on Wayland at DPR 1.25. The close-up still had blue/orange edges; `QtRendering` alone had retained Qt's default LCD subpixel distance-field material. This rejected implementation is under `screenshots/redesign/typography/cycle1/wayland/`. The 1× offscreen capture had no such fringe because it used Qt's software renderer, so it was insufficient evidence.
2. Set `QSG_DISTANCEFIELD_ANTIALIASING=gray` before importing Qt in the QML launcher. The same `QtRendering` comparison then lost the colored edge. The code uses `StyledText` for QML labels with no hinting (the viewed 12–13 px Latin/Cyrillic stems were more even), gray AA for the Qt glyph shader, and no viewport text layer. `NativeRendering` with vertical hinting was compared separately on Wayland at DPR 1.25 and 2: it also has no color fringe under this configuration, but gives little visible benefit and a firmer, sometimes uneven small mono stroke. The shared Qt/no-hint path is retained for consistency across pages and scales. Font sizes below 12 were raised; Noto Sans secondary body labels below 13 were raised. `ConnectionTag` and `StatusLED` no longer add tiny letter spacing.

The `scripts/text_render_check.py` reference window contains `USB`, `Нет данных`, `libratbag →`, `15 настроек`, type caption, `46%`, card title, tabs, header status, and English equivalents. Each image is captured at original pixels and enlarged ×4 with nearest-neighbour sampling. Its color metric counts edge pixels whose RGB channels cannot be explained by gray coverage of the configured foreground color against `#171713`. It is an aid to manual inspection, not a substitute for it. The actual QML Dashboard captures are in `after/dashboard-wayland/` and passed the smoke navigation/layout checks.

| Effective Wayland DPR | Subpixel chromatic edge pixels | Gray chromatic edge pixels |
|---|---:|---:|
| 1.0 | 5401 / 6188 | 0 / 4513 |
| 1.25 | 7210 / 8428 | 0 / 6047 |
| 1.5 | 8363 / 9787 | 0 / 7152 |
| 2.0 | 9708 / 11419 | 0 / 8304 |

The monitor's native 1.25 scale was left unchanged; per-process `QT_SCALE_FACTOR` values 0.8/1/1.2/1.6 produced the effective DPRs above. Qt reported `PassThrough` without a new global policy. Running offscreen at explicit `QT_SCALE_FACTOR=1/1.25/1.5/2` also checks clipping/layout, but only the Wayland/OpenGL comparison reproduced the fringe. Screenshots document pixels returned by `QQuickWindow.grabWindow()` in the user's real Wayland session, not a photograph or separate monitor capture. It is not possible to assert how every physical panel's subpixel order looks from those files alone.

For reproducing the baseline scale on this session, leave `QT_SCALE_FACTOR` unset. `QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough` is optional because Qt already reports that policy; no startup override is necessary. The smoke window can be moved to workspace 6 for visual inspection and the prior workspace restored afterward, without changing Hyprland configuration. The GTK peripheral smoke initially got an empty widget snapshot while its window was on an inactive workspace; it passed once workspace 6 was visible.

Examples: [subpixel 125%](screenshots/README.md#historical-reviews), [gray 125%](screenshots/README.md#historical-reviews), [Native/vertical 125%](screenshots/README.md#historical-reviews), [USB and no-data before](screenshots/README.md#historical-reviews), [USB and no-data after](screenshots/README.md#historical-reviews), [real Dashboard RU](screenshots/README.md#historical-reviews).

Limitations: scene/layout coordinates are still fractional in some nested rows (diagnostic count 222 of 233 visible/dynamic text items at offscreen DPR 1.25); Qt's grayscale sampling handles those without color fringes, but a small change in stem weight with animation/scroll may remain. The `--debug-text` log surfaces these positions. There was no font replacement or change to the system's scaling configuration. GTK uses its own text rendering and remains the default UI.

## Validation

- `python -m compileall -q .`: exit 0, no diagnostics.
- `python -m unittest -q`: 288 tests in 22.951 s, OK.
- `python scripts/check.py`: 288 tests in 23.355 s, OK.
- `python scripts/qml_smoke.py`: Dashboard/detail/diagnostics/settings/About plus `qmllint`, PASS.
- `python scripts/qml_backup_smoke.py`: preview, selection, private snapshot, partial result and RU/EN with memory I/O, PASS.
- `python scripts/gui_smoke.py`: editor, language, dialogs, cancellation; no writes/capture, PASS.
- `python scripts/simulation_smoke.py`: 15 GTK scenarios, no real CLI/capture, PASS.
- `python scripts/peripheral_smoke.py`: real GTK width 640×780 and audio/theme captures, PASS with workspace 6 visible; the previous workspace was restored. The earlier runs with workspace 6 hidden could not produce a GTK widget snapshot.
- `python scripts/text_render_check.py`: offscreen sample, PASS; Wayland/OpenGL captures and gray-vs-subpixel metrics at four effective DPRs are tabulated above.
- `scripts/prepare-arch.py` and archive inspection: new runtime/script files present; `bash -n packaging/arch/PKGBUILD` passed. Source archive prepared locally; nothing installed or published.
