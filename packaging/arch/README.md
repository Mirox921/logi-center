# Arch Linux local package

This development recipe builds the current checkout, including local source edits. It does not download or guess a future release tag. It is not published to AUR.

```sh
python scripts/prepare-arch.py /tmp/logi-center-arch-build
cd /tmp/logi-center-arch-build
makepkg
```

Use a new empty directory for another build. The preparation script writes an exact SHA-256 into the generated PKGBUILD. Review the recipe/dependencies before building. If required dependencies are absent, install them deliberately using normal Arch tools; the helper does not install anything. Optional backends enable only their own functions; the GUI diagnoses missing components.

After reviewing the built package, installation is an explicit user action:

```sh
sudo pacman -U ./logi-center-0.5.1-1-any.pkg.tar.zst
```

Update by preparing/building the new checkout and installing its package. Remove with `sudo pacman -R logi-center`. Preferences, drafts, backups and EasyEffects presets in the home directory are preserved.

The system package installs `/usr/bin/logi-center`, runtime modules under `/usr/lib/logi-center`, a desktop entry, scalable icon, license and documentation. An existing per-user installer/desktop entry can take precedence; choose one installation method. Do not delete user settings when switching methods.

Validation in development uses the real `package()` function in a temporary staging directory and checks its manifest; the package is not installed. Full makepkg/namcap validation and installation remain conditional on available build tools/dependencies and are reported separately.

The launcher now starts Qt6/QML by default. PySide6, Qt Quick/Controls and SVG
are required; qt6-wayland is needed for native Wayland. GTK4/libadwaita and
runtime Cairo are not dependencies. python-gobject supplies the shared Gio/GLib
D-Bus readers; python-cairo is a build/test dependency for offline illustrations.
The archived GTK baseline is separate; see [cutover/recovery](../../docs/qml-cutover.md).
