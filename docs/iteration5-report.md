# Итерация 5 — результат для визуальной приёмки

Работа находится в прежнем worktree/ветке ui/dashboard-iteration. Это результат
для просмотра пользователем; визуальное утверждение пользователя не предполагается.
GTK остаётся основным интерфейсом. Публикации, установки, аппаратных записей,
прошивок и изменений системных прав не было.

| Группа | Изменения | Файлы / коммит |
|---|---|---|
| A | LC из трёх вариантов, размеры16/24/32/40 и две подложки; общий фильтр/счётчики, отдельные аудио/прочие | device_presentation.py, bridge.py, AppHeader.qml, SVG; de50ba6 |
| B | Нейтральные переключатели и настройки, маленький маркер активности, маска акцента | CutButton/DashboardToolbar/DeviceCard, iteration5_review.py;1437d67 |
| C | Общая сцена320x240, независимое вписывание по выбору пользователя, батарея только где уместна, floor-сегменты, читаемые метки | DeviceCard/DeviceSection/SegmentedBattery/ConnectionTag/CutFrame, presentation;944efdf |
| D | Непрозрачная панель, затухание12px, отступ контента и отдельный gutter18px | DashboardToolbar/DashboardPage, matrix smoke;6883959 |
| E | Итоговый контур iteration4, сглаженный C2, встроенные боковые кнопки wireless/gaming, нейтральные touchpad/pointer_generic | illustrations/models/{mouse,touchpad}.py, materials/checks, PNGs, выбор изображения;93c7117 |
| F | Финальные снимки, поля включая тень и hover, HiDPI-файл/масштаб/хеш, тесты, CI/Arch и отчёт | scripts/card_metrics.py, smoke/gallery/prepare-arch, PKGBUILD; текущий HEAD |

Последние уточнения пользователя имеют приоритет: форма мышей — предоставленные
изображения iteration4, а не отвергнутый shape-cycle2. Боковые кнопки немного
увеличены (длина10mm, внутренний вылет2.6mm) и выделены светлее, стальным графитом.
Наружный выступ <=.58mm, расстояние центров13mm. У plain/compact кнопок нет.
Это обобщённая графика классов, не утверждение о точной форме/функциях K7/G502.

Светлый размытый прямоугольник вокруг тачпада удалён. Остались тонкий паз/фаска и
едва заметные тёмные углы palm-rest. Touchpad1.55:1 с зоной кнопок, generic1.4:1
без зоны/микротекстуры. Старый перфорированный mouse_builtin использует generic.

## Изображения и списки дефектов

- [Мыши на приёмку](screenshots/README.md#historical-reviews).
- [Сенсорные поверхности](screenshots/README.md#historical-reviews).
- [Iteration4 / итог рядом](screenshots/README.md#historical-reviews).
- [Wireless ×4 до/после](screenshots/README.md#historical-reviews).
- [Gaming ×4 до/после](screenshots/README.md#historical-reviews).
- [Тачпад ×4 на белом](screenshots/README.md#historical-reviews).
- [Все классы / серия / тёмная и светлая1x2x](screenshots/README.md#historical-reviews).
- [Реальные файлы и SHA-256](screenshots/README.md#historical-reviews).
- [Dashboard до/после](screenshots/README.md#historical-reviews).
- [Нативная Wayland-матрица](screenshots/README.md#historical-reviews).
- [Дефекты по A–F](screenshots/README.md#historical-reviews).
- [Циклы правок иллюстраций и последующие уточнения](screenshots/README.md#historical-reviews).

Финальные кадры RU/EN:1000/1280/1600/1920 плюс800/640. Сохранены верх списка,
секции02/03, фокус поиска/карточки, hover мыши/тачпада, фильтр встроенных, пустой
результат, последняя строка и страницы устройств. Native DPR1.25: логический1000
даёт1250px PNG. Открыты итоговые ×4 сравнения мышей, black/white поверхности,
серии/контактные листы, RU1280, native EN1920 и hover тачпада RU1000. Письменные
циклы включают найденные дефекты и отвергнутые варианты, а не заявления по коду.

## Измерения

Янтарная площадь во всех восьми итоговых обычных RU/EN кадрах1000–1920:
**0.2497–0.4763%**, включая графику устройств, меньше5%. Правило HSV и абсолютное
число пикселей — final-accent/accent-metrics.json; рядом greyscale и бинарная маска.

Сцена320x240 у всех карточек, батарейный резерв не меняет её размер. Фактическая
непрозрачная мышь занимает около75.1–75.2% высоты; клавиатуры85.0% ширины. Поля
включая тень измерены по PNG, не только Image-виджету: вертикальные минимум8.2%,
мыши имеют >30% горизонтального поля. У тачпада обычное поле около12.5%; hover
ограничен так, чтобы сохранить12% (допуск измерения субпикселя в smoke). Загружается
@2x, source_pixel_scale<1, то есть исходный растр не увеличивается на проверенном
HiDPI. Все значения/хеши — after/card-metrics.json и after/wayland/card-metrics.json.

Силуэт мышей сравнивается с iteration4 IoU>=.97; C2-разрыв касательной/кривизны
<1e-12, шаг поворота полигонального приближения<2deg. Новые более сильные изгибы
были отвергнуты пользователем и не используются. Touchpad/display distance на64px
около.22, выше.15; отличие от клавиатур/прочих форм также проверено. Ободок цвета
за пределом1px не найден; чёрная контактная тень допускается. Плоская затухающая
панель больше не существует, исключения для её fringe-проверки удалены.

Клавиатуры/гарнитуры/колонки/микрофон/донгл и audio_unknown:24 PNG побайтно совпали
с iteration4. Laptop-контраст8–12 L*, приглушённая подсветка без периметра,
TKL87/Full104, суммы рядов/зазоры.5u/непересечение уже проходили и сохранены.

## Реальный вывод проверок

```
python -m compileall -q .
(no output, exit0)
python -m unittest -q
Ran 288 tests in 25.039s
OK
python scripts/check.py
Ran 288 tests in 24.115s
OK
python -m illustrations.checks --deterministic
PASS: 52 PNGs; 5 layouts; 0 failures
python scripts/qml_smoke.py
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
PASS: qmllint accepted the QML pages and Theme module.
python scripts/telemetry_review.py
PASS: eight RU/EN tags have >=6px padding; seven rendered meters round down exactly.
python scripts/qml_backup_smoke.py
PASS: QML backup preview, keyboard field selection, selective restore, private snapshot, partial result and RU/EN; memory I/O only.
python scripts/ui_iteration_smoke.py --stage cards --matrix ...
PASS: uniform cards/scenes; real PNG bounds/hash; separate G502 provider records; battery delta keeps card/focus/scroll; charging without percent, denied state and reconnect; no real I/O.
PASS: visual matrix RU/EN, five widths, hover/focus/search/empty/categories/built-in/last row and six device details; no writes.
python scripts/illustration_dashboard.py --stage after
PASS: ru: ten device silhouettes unclipped; mouse75–84% scene height, keyboard~85% scene width; five widths.
PASS: en: ten device silhouettes unclipped; mouse75–84% scene height, keyboard~85% scene width; five widths.
```

В обычной Wayland-сессии, рабочий стол6, с восстановлением прежнего рабочего стола:

```
python scripts/ui_iteration_smoke.py --stage cards --matrix --wayland ...
PASS: uniform cards/scenes; real PNG bounds/hash; separate G502 provider records; battery delta keeps card/focus/scroll; charging without percent, denied state and reconnect; no real I/O.
PASS: visual matrix RU/EN, five widths, hover/focus/search/empty/categories/built-in/last row and six device details; no writes.
python app.py --ui qml --smoke
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
python scripts/gui_smoke.py
GUI smoke: no writes/capture; editor, language, dialogs and cancellation passed
python scripts/simulation_smoke.py
Simulation GTK smoke: 15 scenarios; real CLI never called; no capture
python scripts/peripheral_smoke.py
Actual narrow window: 640 780
Live peripheral review passed: /tmp/logi-peripheral-review
```

Живой smoke проверял обнаружение/чтение K7 Ultra, Ace68-II, G502 и встроенного
ввода; матрица событий — изолированные mock-устройства. Реальные переходы зарядки,
физическое отключение/подключение и записи настроек не выполнялись.

В расширении QA найдено: временная Qt-обёртка окна из art.window() разрушала
тестовое окно; DPR теперь передаётся от существующего root. Это дефект измерительного
скрипта, устранён и повторно проверен, не аппаратный сбой. F также ограничил
hover-сдвиг тачпада по полям и явно установил QML window icon/desktop ID, чтобы
источник LC использовался не только в шапке/About и упаковке.

Архив Arch проверен:52 PNG, geometry.json, QML, новые QA-скрипты/TelemetryReview.qml,
собственные reference PNG и лицензии присутствуют; bytecode/нелицензированных фото
нет. Installer копирует qml_ui рекурсивно, отдельный рендерер не входит в runtime.
CI/PKGBUILD/prepare-arch обновлены. Системная установка не выполнялась.

Ограничения: изображения обобщённые, полное совпадение с физической моделью не
заявляется; реальная зарядка не тестировалась; полный перенос редакторов в QML
остаётся отдельным паритет-гейтом. GTK/старые редакторы сохранены. Релиза нет.
