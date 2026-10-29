# EWEADN S9 — реализация и границы проверки

Состояние на 2026-10-29: реализован собственный ограниченный ByteTech adapter
в существующей архитектуре Logi Center. Протокол проверен по предоставленному
архиву и исходникам официального EWEADN Hub; физической S9 в этой среде нет.
Это **не подтверждение полной аппаратной совместимости**.

## Источники

- Предоставленный `eweadn-s9-linux.zip`, SHA-256
  `bff2e66e3ed4416c11a2567055d61520a6c0bda7635840fe112caac8f7cea1ae`.
  Его installer/GUI не запускались, udev rules не устанавливались.
- [Официальный Hub](https://new-hub.eweadn.cn/), build
  `3.3.4-20261029054305455`, изучен как текст, без выполнения загруженного JS:
  [mouse SDK](https://new-hub.eweadn.cn/main.sdk-mouse-beiying.01fc5daacd5c1a5fe4b2.js),
  SHA-256 `721a3e92ba476c92d2d33665fc2fe94db42bdabf5a3db658abb36f6b56d6cabe`;
  [ByteTech codec](https://new-hub.eweadn.cn/main.vendor-bytech.803cedc7e7fc4dcad3e3.js),
  SHA-256 `252fbd62a7cc964e38f6ac84d80cf88967c3de31c17f389da01d58b253913797`.
- Семь пользовательских скриншотов использованы как UX-референсы. Наличие
  элемента на скриншоте само по себе не считается доказательством протокола.

Архив не содержал рабочего writer макросов, всегда возвращал успех записи
(`acks or True`), передавал Hz вместо native polling code и обозначал sleep
как минуты. Эти ошибки в новый adapter не перенесены: успех требует полного
readback, polling сохраняет второй nibble, единица sleep — **30 секунд**
по официальному SDK. Multipart-чтение проверяет offset/encapsulation/длину,
не принимает ACK или заполнение нулями за данные устройства.

## Идентификация

VID `372e`; PID `1026` — общий wireless receiver, `103d` — 1 kHz receiver.
Wired PID: `1027` Ultra, `105e` Max, `1029` Pro (1 kHz), `108d` Ultra+.
Общий receiver используется также другими моделями: обязательно читается
модельный ID страницы 128:

| ID модели | Модель |
|---|---|
| 9895604650026 | S9 Max |
| 9895604649998 | S9 Pro |
| 9895604650000 | S9 Ultra |
| 9895604650058 | S9 Ultra+ |

Это ID модели, не уникальный серийный номер. Две физические мыши разделяются
по USB-пути, HID-instance и descriptor hash. Для переподключения/смены
конфигурации проверяется generation и fingerprint. Перепривязку такой же
модели к тому же receiver без изменения конфигурации этот протокол не позволяет
надёжно отличить; pairing API не предоставляется. Вспомогательная input-клавиатура
скрывается только при совпадении точного физического узла подтверждённой S9.

## Реализовано

| Возможность | Реализация | Проверка |
|---|---|---|
| DPI | 1–8 ступеней, цвет каждой, активная ступень; предел из устройства, шаг 50 DPI; текущие отдельные X/Y сохраняются | Codec, mock write/readback, QML |
| Polling | Реальные native codes 125–8000 Hz, ограниченные сообщённым максимумом и типом соединения | Codec/RMW/mock |
| Performance | 4 native режима; wired firmware-controlled режим не редактируется | Codec/RMW/mock |
| Sensor | Motion Sync, Ripple Control, Angle Snapping, LOD, debounce 0–20 ms, sleep 0–3000 s с шагом 30 s (0 — никогда) | Codec/RMW/mock |
| Кнопки | Интерактивные 5 физических точек; mouse/keyboard/media назначения; редактируются только прочитанные доступные слоты | QML hitbox/capture, mock readback |
| Макросы | Отдельное окно, локальная библиотека, запись клавиш/мыши/пауз; сохранение once/toggle/held metadata | Mock/QTest, без native playback |
| Батарея/профиль/FW | Read-only данные устройства, ограниченный status poll; профиль привязан к черновику | Mock/identity tests |
| Factory reset | Отдельное явное подтверждение, снимок читаемых настроек, без обещания полного отката | Mock, результат sent/unverified |
| Изображение | Один SVG для Dashboard и редактора, исходник сохранён, Qt derivative без raster | Qt/librsvg + QML 1×/2× |
| Масштаб QML | Настройки → 75/90/100/110/125/150/175/200%; после перезапуска | Preferences + QML mock |

Действия используют `Control` → `Plan/perform` → `sdk_worker` → единственный
adapter. HID I/O выполняется вне GUI с существующим deadline. Записи
сериализованы, не повторяются автоматически; проверяются профиль, свежая
конфигурация и неизменность остальных прочитанных полей. Новая ЛКМ назначается
и проверяется **до** удаления прежнего назначения. Снимки перед записью остаются
частными в state directory; диагностические отчёты не включают raw pages.
Переключение страницы/обновление не удаляет черновик. Неактивные DPI-ступени
сохраняют локальные правки, но не применяются скрытно.

Discovery/status/open editor не отправляют конфигурационные setters.
Read queries используют feature report ID 3, main 79; pages 0/64/65/128/129.
Allowlisted setters: main 48 (button slot), 53 (sensor field), 58 (DPI v2.1),
6/sub255 (явный reset). Произвольного HID/OTA/firmware API в bridge нет.
Открытая вкладка обновляет конфигурацию не чаще чем раз в 15 s; отдельный
battery service читает короткий статус без полного rescan. Ошибки не заменяют
предыдущее значение нулём и не выдаются за подтверждение применения.

## Оставшиеся ограничения

- **Native macro upload не включён.** Официальный writer форматирует банк через
  OTA, а архив не содержит чтения/экспорта существующего банка. Без проверенного
  формата, восстановления и аппаратного readback это может уничтожить прежние
  макросы. Локальные repeat modes ещё не означают playback на мыши.
- Не добавлены firmware update, receiver firmware read и переключение onboard
  профиля: эти операции используют отдельные пути, не подтверждённые этим этапом.
  Показан фактически прочитанный native профиль; его slot count не выдумывается.
- Не добавлено включение separate X/Y, если этот режим не активен: текущие оси
  сохраняются, но непроверенная комбинация не записывается.
- Не вычисляется фиктивная оценка оставшихся часов батареи.
- У базовой ревизии side slots могут быть пустыми. Пять видимых физических
  кнопок не означают пять гарантированно writable слотов на любой прошивке.
- Доступ к hidraw должен быть предоставлен системой. Installer не меняет
  permissions/udev; недоступный интерфейс остаётся read-only с диагностикой.
- GTK сохранён и остаётся default; новые S9 composite editors доступны в QML.

Масштаб сохраняется в существующих private GUI preferences и применяется до
создания Qt application, дополняя системный/внешний `QT_SCALE_FACTOR`.
GTK и глобальные настройки рабочего стола не изменяются.

## Проверки и изображения

- 135 целевых unit/integration tests — pass.
- Общая suite: 491 tests, 490 pass; один отсутствующий EN перевод Reset исправлен,
  `test_qml_translations` после исправления — pass. Не повторялся весь suite
  ради одной строки перевода.
- `compileall`, `qml_smoke`/qmllint, `eweadn_smoke` — pass.
- Финальные 25 тестов codec/adapter/editor/translations — pass, включая stale
  поля после ошибки обновления и снятие stale после успешного чтения.
- Qt/librsvg SVG comparison: 73 существенно отличающихся pixels из 237650;
  прозрачный фон/контур/красный материал сохранены.
- QML offscreen: RU 1280×800 / EN 640×780, 1× и 2×; mock Apply/readback,
  5 hitboxes, hover без записи, Cancel, reconnect, capture A/Space/click,
  library metadata, UI scale/restart state. Итоговые изображения открыты.
- `peripheral_smoke`: недоступен GTK display в sandbox, read-only dconf;
  это ограничение окружения, не успешная GTK-проверка. Повтор не выполнялся.
- Подготовлен свежий Arch source archive; проверены runtime manifests,
  наличие SVG/helper/tests/docs и checksum. Из распакованного архива QML
  simulation startup/navigation smoke — pass. Системная установка не выполнялась.

Изображения: [Dashboard](screenshots/README.md#historical-reviews),
[кнопки](screenshots/README.md#historical-reviews),
[DPI](screenshots/README.md#historical-reviews),
[sensor](screenshots/README.md#historical-reviews),
[макросы](screenshots/README.md#historical-reviews),
[масштаб](screenshots/README.md#historical-reviews).

## Нужна физическая проверка

Сначала read-only: определить точную ревизию/firmware, сравнить все прочитанные
поля с официальным Hub, проверить wireless/wired, смену DPI физической кнопкой,
battery/charging и доступные button slots. Затем с явным согласованием:
по одному reversible параметру (DPI/color, sensor flag, polling, side button),
readback, проверка остальных полей и возврат оригинала. Не использовать ЛКМ
как первую тестовую кнопку. Reset и запись macro bank не входят в этот тест.
Пока это не выполнено, поддержка имеет статус **реализовано / проверено mocks**,
а не **физически подтверждено**.


## 2026-10-29 — discovery and sleeping-device diagnostics fix

`EweadnAdapter.discover()` passed its fault list as Device's positional
`simulated` argument, even when that list was empty. Real S9 records were then
filtered out; a timeout inserted Fault objects into the public `simulated`
field and broke QML report JSON serialization. Connection, capabilities and
faults now use explicit keywords, leaving `simulated=False`.

Regression tests cover successful and timed-out discovery, real/simulation
filtering, disabled writes when identity cannot be read, allowlisted fault
serialization and DiagnosticController.sync/inventory. Discovery performs only
existing read operations. The user reported a successful live S9 check with the
keyword fix; this development run used fake devices and did not perform new
physical S9 writes. Existing transport/timeout and wake/retry behavior remains.
