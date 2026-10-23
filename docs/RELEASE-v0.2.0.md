# Logi Center v0.2.0 — G502 HERO support

Updated public preview with the current application and screenshots.

## New in this version

- G502 HERO support alongside G305: 5 onboard profiles, 11 buttons and 2 lighting zones.
- Active-profile DPI and polling-rate readout; inactive profile settings no longer appear as current values.
- Profile and DPI-stage selection, additional button actions, and visual lighting mode/color selection.
- Wired G502 is identified as USB-connected without a battery indicator.
- Mouse profile and lighting screenshots, plus updated English/Russian documentation.
- Improved audio layout: device names remain readable in narrower windows.

G502 readout was checked on connected hardware. Saved profile colors may differ from the visible lighting. Writing lighting, button mappings and profiles still needs broader physical testing.

## Download and install

This is a source release for Linux. Install the dependencies listed in the [README](https://github.com/Mirox921/logi-center/blob/v0.2.0/README.md), then download and extract **logi-center-0.2.0.tar.gz**. Open a terminal in the extracted directory and run:

```sh
python install.py
```

The installer updates the application for your current user. Open **Logi Center** from the application menu. Existing preferences are retained. Tested on Arch Linux/Wayland; other distributions are not yet verified.

To verify the attached source archive, place it beside `SHA256SUMS` and run:

```sh
sha256sum -c SHA256SUMS
```

GitHub's automatically generated source downloads are separate archives and are not covered by this checksum file.

## Checks and limitations

All 16 unit tests pass. The application was opened with a connected G502 HERO, its profile readout was checked, and the initial read-only inspection left the device settings unchanged.

This remains an early preview, not an official Logitech app or full G HUB replacement. Original Blue VO!CE/DTS, firmware updates, automatic game profiles and built-in advanced editors are not included. G515 lighting writes and G PRO X sidetone need further testing. See the README for first-time Solaar setup and known limitations.

## Screenshots

![G502 HERO profiles and DPI](https://github.com/Mirox921/logi-center/raw/v0.2.0/docs/screenshots/g502-profiles.png)

[G502 lighting and extra buttons](https://github.com/Mirox921/logi-center/blob/v0.2.0/docs/screenshots/g502-lighting.png)

## По-русски

Обновлённая версия с поддержкой G502 HERO: 5 профилей, 11 кнопок, две зоны подсветки и исправленное чтение DPI активного профиля. Скачай `logi-center-0.2.0.tar.gz`, распакуй и выполни `python install.py`. Программа обновится, пользовательские настройки сохранятся. Это предварительный релиз; ограничения описаны в README.
