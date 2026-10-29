<p align="center"><img src="assets/icons/logi-mark.svg" width="80" alt="Logi Center"></p>
<h1 align="center">LOGI / CENTER</h1>
<p align="center"><strong>Центр управления периферией Linux на Qt6/QML.</strong><br>
Мыши, клавиатуры и аудио — один интерфейс поверх существующих Linux-backend.</p>
<p align="center"><a href="README.md">English</a> · <a href="https://github.com/Mirox921/logi-center/releases/tag/v0.5.1">Скачать v0.5.1</a> · <a href="docs/backend-support.md">Поддержка устройств</a> · <a href="https://github.com/Mirox921/logi-center/issues">Сообщить о проблеме</a></p>

![Новый Dashboard Logi Center на Qt6/QML](docs/screenshots/releases/v0.5.1/dashboard.png)

## Новая основа

**Qt6/QML теперь единственная оболочка приложения.** Вместо GTK — графитовый
Dashboard с янтарными акцентами, интерактивные редакторы устройств и общие
Python-сервисы. `python app.py` и пункт меню приложений запускают QML.
Прежняя GTK-версия сохранена в истории Git и отдельном локальном архиве;
[проверки перехода и восстановление](docs/qml-cutover.md).

Logi Center больше не ограничен Logitech. Программа объединяет существующие
Linux-сервисы и адаптеры конкретных моделей. Настройки появляются по реальным
capabilities устройства, прошивки и backend. Наличие производителя в списке
не означает поддержку каждой его модели или полного набора функций Windows-ПО.

## Интерфейс

<table>
<tr>
<td width="50%"><a href="docs/screenshots/releases/v0.5.1/mouse-side.png"><img src="docs/screenshots/releases/v0.5.1/mouse-side.png" alt="Назначения кнопок G502 HERO" width="100%"></a><br><sub>Мышь: SVG, интерактивные кнопки и черновики назначений.</sub></td>
<td width="50%"><a href="docs/screenshots/releases/v0.5.1/keyboard.png"><img src="docs/screenshots/releases/v0.5.1/keyboard.png" alt="Выбор клавиш Ace68-II" width="100%"></a><br><sub>Клавиатура: выбор клавиш, срабатывание и Rapid Trigger.</sub></td>
</tr>
<tr>
<td width="50%"><a href="docs/screenshots/releases/v0.5.1/mouse-lighting.png"><img src="docs/screenshots/releases/v0.5.1/mouse-lighting.png" alt="Подсветка мыши" width="100%"></a><br><sub>Подсветка: штатные эффекты устройства и параметры, доступные через backend.</sub></td>
<td width="50%"><a href="docs/screenshots/releases/v0.5.1/audio.png"><img src="docs/screenshots/releases/v0.5.1/audio.png" alt="Настройки аудио Linux" width="100%"></a><br><sub>Аудио: маршруты звукового сервера, громкость и mute.</sub></td>
</tr>
</table>

Скриншоты сняты **на английском языке в настоящем Wayland-окне на рабочем столе 9**.
Использованы реальные read-only данные; настройки оборудования ради кадров
не менялись. Предупреждения и неизвестные значения соответствуют фактическому
состоянию. [Галерея и сведения о съёмке](docs/screenshots/README.md).

## Возможности

- **Мыши:** поддержанные DPI-ступени и цвета, частота опроса, профили, кнопки,
  макросы и подсветка. У G502 — виды сверху/сбоку и все 11 native button IDs.
- **Клавиатуры:** интерактивная схема, RGB и доступные поклавишные параметры.
  Ace68-II ограничена реализованным протоколом прошивки; G515 использует Solaar.
- **RGB:** предпочтение штатным аппаратным эффектам; зоны, период и яркость
  отображаются при наличии поддержки. Скрытого программного цикла RGB-записей нет.
- **Макросы:** отдельное окно записи клавиш, щелчков и пауз, частная библиотека.
  Загрузка на устройство зависит от подтверждённых возможностей backend.
- **Аудио:** выходы/входы, устройство по умолчанию, громкость/mute,
  явный тест микрофона и пресеты EasyEffects. Запись начинается только по запросу.
- **Данные:** черновики до Apply, предпросмотр и выборочное восстановление
  резервной копии, частный защитный снимок и обезличенная диагностика.
- **Настройки:** RU/EN, уменьшение анимаций, имя/изображение устройства,
  масштаб QML 75–200% после перезапуска.

Аппаратные операции идут вне GUI-потока и сериализуются. Сохраняются проверки
переподключения, профиля и устаревших команд. Отправка команды, кэш и
подтверждение устройства — разные состояния. Форматы существующих копий и
общие сервисы сохранены.

## Поддержка и степень проверки

| Устройство / backend | Реализация | Граница проверки |
|---|---|---|
| **Logitech G502 HERO / libratbag** | DPI, polling, профили, кнопки/макросы, две сообщённые зоны подсветки | Пользователь подтвердил Color Cycle LED 1: 8000 ms, яркость 255, работает после закрытия программы. Другие режимы и зоны проверены не полностью. [RGB](docs/g502-rgb.md) |
| **MCHOSE K7 Ultra** | DPI, кнопки, сенсор, индикаторы и штатная RGB дока | Отдельные обратимые тесты и наблюдения за доком описаны по параметрам. Приёмник может быть виден, когда спящая мышь не отвечает; значения не выдумываются. [Настройки](docs/k7-controls.md), [док](docs/k7-dock-rgb.md) |
| **MCHOSE Ace68-II, firmware 121** | Выбор клавиш, actuation/RT/dead zones, подсветка, key maps и поддержанные advanced banks | Некоторые прежние операции подтверждены физически; многие новые bank/per-key пути — только mocks. Неподтверждённые прошивка/калибровка не запускаются. [Редактор](docs/ace68-editor.md) |
| **Logitech G515 LS TKL / Solaar** | Scoped settings, RGB, яркость/таймеры, доступные per-key данные | Живые настройки имеют приоритет; rgb_control=False не скрывает устройство. Полный паритет с G HUB не заявлен. [G515](docs/g515-settings-fix.md) |
| **EWEADN S9** | Model-verified DPI, polling/performance/sensor, кнопки и пользовательский SVG | Протокол и mocks; физической S9 здесь не было. Native macro upload отключён до установления безопасного чтения/восстановления банка. [S9](docs/eweadn-s9.md) |
| **Другие backend** | OpenRGB, OpenRazer, rivalcfg, HeadsetControl, PipeWire/PulseAudio, Linux input | Только реализованные capabilities. ckb-next — обнаружение. [Матрица](docs/backend-support.md) |

**Реализовано, проверено на mocks и подтверждено физически — разные статусы.**
Неизвестное устройство может оставаться стандартным Linux input без расширенных
настроек. [Подробная матрица действий](docs/qml-parity.md).

## Скачать и запустить

В [релизе v0.5.1](https://github.com/Mirox921/logi-center/releases/tag/v0.5.1)
доступны исходный архив и пакет Arch. Проверьте `SHA256SUMS` перед использованием.
Это приложение Python/Qt, а не автономный AppImage: зависимости нужны отдельно.

Runtime для Arch Linux:

```sh
sudo pacman -S --needed python python-yaml python-gobject pyside6 qt6-declarative qt6-svg qt6-wayland
```

Из распакованной папки:

```sh
python app.py
# Изолированная демонстрация без реальных аппаратных операций:
python app.py --simulate
```

Установка для текущего пользователя:

```sh
git clone --depth 1 https://github.com/Mirox921/logi-center.git
cd logi-center
python install.py
logi-center
```

Установщик обновляет `~/.local/share/logi-center`, `~/.local/bin/logi-center`
и пункт меню. **После обновления исходников повторно запускайте установщик**,
чтобы меню запускало новую копию. Предпочтения, черновики и backup-файлы сохраняются.
Root для этого установщика не требуется.

Аппаратные backend устанавливаются отдельно: например, libratbag, Solaar или
HeadsetControl — по необходимости. Не запускайте весь GUI от root для обхода
прав HID. [Инструкция запуска](START_HERE.ru.md) · [Сборка Arch](packaging/arch/README.md).

## Разработка и порядок в репозитории

Код находится в `src/logi_center`, общие ресурсы — в `assets`, тесты разделены на
`unit`, `integration` и mock-проверки `hardware`. См.
[архитектуру и сборку пакетов](docs/development/architecture.md).

```sh
python scripts/check.py
python scripts/gui_smoke.py
python scripts/simulation_smoke.py
```

Для offline-инструментов иллюстраций дополнительно нужен PyCairo.
CI проверяет редакторы, резервные копии, локализацию, SVG и guards.
Автотесты не заменяют физическую проверку оборудования.

В Git остаются код, assets с лицензиями, тесты/fixtures, протокольная документация
и небольшая релизная галерея. Генерируемые кадры, agent tooling, кэши и пакеты
не коммитятся. Исторические изображения сохранены в локальном архиве; прежние опубликованные
релизы остаются в истории Git. [Правила скриншотов](docs/screenshots/README.md).

## Лицензия и обратная связь

Код Logi Center распространяется по MIT. Для Qt, шрифтов, иллюстраций и backend
действуют соответствующие уведомления; см. `SOURCES.md` и license-файлы.
В issue укажите модель, прошивку/версию backend и обезличенную диагностику.
Не публикуйте серийные номера, приватные макросы, raw HID и личные настройки.
