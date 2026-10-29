# Release screenshots

The current gallery is [v0.5.1](releases/v0.5.1/): nine English screenshots of
the actual Qt6/QML application on Hyprland/Wayland workspace 9. The capture
script checks its own window's workspace before each image, queries live data
with a write/capture/playback guard, and restores the original workspace.
Language changes are not persisted. No synthetic device values are inserted.
`capture.json` records only image dimensions, language, workspace and platform.

- [Dashboard](releases/v0.5.1/dashboard.png)
- [G502 top view](releases/v0.5.1/mouse-buttons.png)
- [G502 side view](releases/v0.5.1/mouse-side.png)
- [Native mouse lighting](releases/v0.5.1/mouse-lighting.png)
- [Keyboard trigger editor](releases/v0.5.1/keyboard.png)
- [Keyboard lighting](releases/v0.5.1/keyboard-lighting.png)
- [Audio](releases/v0.5.1/audio.png)
- [Settings](releases/v0.5.1/settings.png)
- [Diagnostics](releases/v0.5.1/diagnostics.png)

Reproduce intentionally in a live Hyprland 0.55+ Lua session:

```sh
python scripts/release_screenshots.py --output /tmp/logi-release-gallery
```

Only curated release screenshots belong in Git. Review captures, comparisons,
local clipboard/reference images and generated metrics should use `/tmp` or
remain ignored. Never commit personal device reports, serials, macro contents
or desktop screenshots showing other applications. Tests use the four small
canonical silhouettes in `tests/fixtures/artwork/iteration4` and two G502
reference renders in `tests/fixtures/artwork/g502`, not review output.

## Historical reviews

The 2241 development-review screenshots were removed from the current Git
snapshot for v0.5.1 and preserved in an external local archive. They are not
required to run the app or reproduce the tests. Links in historical progress
notes refer here rather than to unavailable development-only GitHub commits.

The unpublished development history is retained locally. The public release
is a single clean commit on top of the previously published main branch, so
those intermediate binary captures are not uploaded through Git history.
Published Git history is not rewritten; the previous GTK release remains
available at [v0.4.0](https://github.com/Mirox921/logi-center/releases/tag/v0.4.0).
