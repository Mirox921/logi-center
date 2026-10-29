# Переход на единственную QML-оболочку — 2026-10-29

По явному решению пользователя обычный запуск `python app.py`, desktop entry
и устанавливаемый launcher теперь открывают Qt6/QML. `--ui qml` совместим с
прежними командами; `--ui gtk` сообщает, как вернуться к архивной версии,
и не запускает неожиданно другой интерфейс. `--simulate`, `--smoke`,
`--debug-text` и Qt platform arguments сохранены. Import `app` не создаёт GUI.

## Резервная копия до удаления

До изменений создан полный архив commit
`b0a58d3cb511ff4fde9e293697a005dd5a465703`:

```text
~/Backups/Logi-Center/gtk-before-qml-default-b0a58d3/
    logi-center-gtk.tar.gz
    SHA256SUMS
    README.ru.md
```

SHA-256 архива:
`85ac49dfc03984c476b3dd4010133f65921b9c73383ea1a1e19ddfedfa363acd`.
Проверены checksum и наличие всех удалённых GTK-модулей. Архив содержит обе
оболочки, общие сервисы, assets, тесты и документацию до переключения.
Он не содержит частных настроек, пользовательских макросов, записей микрофона
или аппаратных backup-файлов. Эти данные в home не изменялись.

Для восстановления в **отдельную пустую папку**:

```bash
cd ~/Backups/Logi-Center/gtk-before-qml-default-b0a58d3
sha256sum -c SHA256SUMS
mkdir gtk-recovery
tar -xzf logi-center-gtk.tar.gz -C gtk-recovery
cd gtk-recovery/logi-center-gtk
python app.py --ui gtk
```

Для архивной версии нужны PyGObject, Cairo, GTK4/libadwaita и PyYAML.
Git history также сохранена; destructive reset не выполнялся.

## Проверка функционального паритета перед удалением

Сопоставлены фактические пользовательские действия старого GTK с действующими
QML-путями; подробная матрица остаётся в [qml-parity.md](qml-parity.md).
До удаления прошли **492 unit tests**, функциональный QML smoke в offscreen
и настоящем Wayland, а также QML backup smoke с memory transport.

| Действия прежнего GTK | Действующий QML-путь | Основание |
|---|---|---|
| Dashboard, категории, выбор устройства, статус/заряд | Main / DeviceBridge / DeviceManager | model/service tests, native navigation |
| DPI, ступень, polling, профили, дополнительные scalars | DeviceEditor / ControlEditor / native model panels | shared plan + bridge tests, fake write/readback |
| Кнопки, shortcuts, макросы | MouseButtons / model panels / MacroWindow | keyboard/mouse capture, drafts and native capability guards |
| RGB, зоны, palette, effects, period/brightness | DeviceEditor / G515Panel / Ace68Panel / K7DockPanel | shared plans, provider ownership and readback tests |
| Раскладка/выбор клавиш, поддержанные Ace68 параметры | KeyboardEditor / Ace68 panels | shared layouts, key/profile isolation tests |
| Audio endpoints, default, volume/mute, sidetone | AudioPage / AudioEndpoint / EditorController | audio-server mock verification |
| Mic meter, recording/playback/delete, processed route | MicrophoneTest / AudioController / AudioSession | explicit actions, fake-session/cancellation/resource tests |
| EasyEffects presets, import, bypass, external editor | AudioPage / AudioController | direction-safe service tests, empty/error states |
| Backup обоих форматов, preview, selection, restore/cancel | BackupsPage / BackupController | native Wayland memory-I/O smoke, private safety snapshot, partial results |
| Inventory, Solaar probes, diagnostics/export | DiagnosticsPage / DiagnosticController | actual shared APIs, privacy tests |
| Drafts, Apply/Cancel, errors, reconnect protection | Existing DraftStore / Epoch / shared executor | legacy-compatible draft keys and regression tests |
| Language, motion, user artwork | SettingsPage / preferences / DeviceArtworkProvider | RU/EN/model/artwork tests |

Не найдено поддержанного GTK backend-действия, для которого требовался бы
оставшийся GTK-виджет. Неопределённые vendor-функции не становятся доступными
только из-за перехода на QML. В частности, безопасная загрузка native S9/Ace68
macro banks и неподтверждённые возможности G HUB остаются ограничениями
backend, а не скрытой GTK-реализацией.

## Удалено и сохранено

Удалены GTK `Center`, dashboard, peripheral/device/audio/microphone/mouse/key
widgets, отдельное GTK backup window и его QProcess route. Резервные копии
обрабатываются внутри QML; `backups.py` и `capability_backup.py` не менялись.
Сохранены DeviceManager, adapters, plans/readback, serialization, DraftStore,
AudioSession, diagnostics и приватные пользовательские данные.

В Arch runtime required dependencies теперь PySide6, Qt Quick/Controls и SVG.
GTK4/libadwaita исключены; Cairo нужен только offline developer tools/tests.
PyGObject сохранён для **Gio/GLib D-Bus readers**: это не GTK UI. Установщик
удаляет только известные устаревшие bundled GTK-модули при обновлении,
сохраняя посторонние файлы. Автоматического системного install не выполнялось.
Устаревший GTK StartupWMClass убран из desktop entry.

`gui_smoke.py` теперь проверяет основной QML launcher и qmllint;
`simulation_smoke.py` вызывает функциональные QML-сценарии;
`peripheral_smoke.py` — существующую QML-навигацию с запретом write/capture.

## Проверки после удаления

- 100 целевых tests на первом шаге — pass.
- `scripts/check.py`: **496 tests — OK**, compileall — pass. Найденная ссылка
  translation test на удалённый GTK-файл исправлена до этого успешного прогона.
- Финальные 53 targeted tests после уточнения сообщения K7 — pass.
- Default `python app.py --simulate --smoke`, gui smoke, qmllint — pass.
- Missing PySide6, явный/неявный QML, CLI help, archived GTK request — tested;
  silent fallback/GTK import/hardware discovery при ошибке Qt отсутствуют.
- QML functional simulation — pass в настоящем Wayland: DPI, профиль,
  buttons/macros, Ace68 keys, audio, reports, RU/EN; requested viewports
  640×780, 800×780, 1000×780, 1280×800, 1600×900, 1920×1080.
  Native DPR 1.25: например 1280×800 → PNG 1600×1000.
- Native Wayland QML backup smoke — pass: preview, выбор полей клавиатурой,
  selective restore, safety snapshot, частичный результат, RU/EN.
  Первый параллельный GUI-запуск получил от compositor width 375 вместо 640;
  отдельный повтор после завершения других окон прошёл без изменения assertion.
- Real read-only navigation — pass для ratbagctl, MCHOSE, Ace68, HeadsetControl.
  Это проверка загрузки/обработки состояния, не подтверждение каждой настройки.
- При read-only проверке K7 вернул `Empty identity reply`; доступны были
  только indicator/dock sections без подтверждённых sensor values. В QML
  исправлено скрытие ошибки в этих секциях и добавлена подсказка разбудить
  мышь/проверить соединение/повторить чтение. Автоматического profile recovery,
  reset или конфигурационных writes не выполнялось. Работа K7 в этом состоянии
  **не заявлена подтверждённой**; тот же ответ использует общий backend.
- GTK backup checksum и содержимое проверены; личные настройки не включались.
- Fresh Arch source checksum — pass; `makepkg --nodeps --nocheck --noconfirm`
  собрал локальный package. Повторный suite внутри makepkg намеренно пропущен:
  он уже выполнен отдельно. Runtime modules/assets package побайтово совпадают
  с исходниками, GTK-файлы/dependencies отсутствуют, Qt dependencies присутствуют.
  Запуск из package staging без `--ui` (`--simulate --smoke`) — pass.
  Package не устанавливался. Локальный артефакт:
  `/tmp/logi-center-qml-only-20261029/logi-center-0.4.0-1-any.pkg.tar.zst`.

После удаления не заявляется универсальная аппаратная сертификация или полный
релизный статус. Реальные restore, microphone recording, G515/S9 writes и
остальные неподтверждённые аппаратные сценарии требуют отдельной проверки
по соответствующим device reports. Наличие GTK для них не давало другого
аппаратного протокола; архив сохраняет возможность вернуться к прежней оболочке.

Итоговые собственные окна:
[Dashboard](screenshots/README.md#historical-reviews),
[мышь](screenshots/README.md#historical-reviews),
[клавиатура](screenshots/README.md#historical-reviews),
[аудио](screenshots/README.md#historical-reviews),
[backup preview](screenshots/README.md#historical-reviews).
