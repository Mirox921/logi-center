# UI fonts

| File | Family / role | Author/source | License | Notes |
|---|---|---|---|---|
| `NotoSerifDisplay-Regular.ttf`, `NotoSerifDisplay-Bold.ttf` | Noto Serif Display; retained legacy display face | Google Fonts, `google/fonts`, `ofl/notoserifdisplay` | SIL Open Font License 1.1, no reserved font name | Not selected by the current QML theme. |
| `NotoSerifDisplay-OFL.txt` | License notice | Google Fonts | SIL OFL 1.1 | Must accompany the font files. |
| `JetBrainsMonoNerdFont-Regular.ttf` | JetBrains Mono Nerd Font; measurements and labels | JetBrains Mono / Nerd Fonts | SIL OFL 1.1 | Cyrillic and Latin coverage verified by `scripts/check_fonts.py`. |
| `JetBrainsMono-OFL.txt` | License notice | JetBrains Mono project | SIL OFL 1.1 | Must accompany the font file. |
| `NotoSans-Regular.ttf`, `NotoSans-Bold.ttf` | Noto Sans; readable UI/display family | Noto Project, supplied by Arch `noto-fonts` | Apache License 2.0 | Regular and bold are registered before QML loads; Cyrillic and Latin coverage verified. |
| `NotoSans-Apache-2.0.txt` | License notice | Noto Project | Apache License 2.0 | Must accompany the bundled Noto Sans files. |

The runtime registers fonts with Qt before loading QML and prints the family actually selected. Noto Sans is used for legible UI text; JetBrains Mono remains the data face. System sans fallback remains available if an asset cannot be loaded.
