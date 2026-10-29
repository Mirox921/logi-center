# G515 LS TKL: «Настройки Solaar недоступны» — 2026-10-29

## Подтверждённая ошибка кода

Редактор очищал G515 controls и пропускал чтение, если отдельный
`keyboard_online()` не возвращал строго `True`. Этот ROOT-пробник ищет только
`HID_NAME=.*G515` в sysfs; он не является универсальной проверкой устройств за
приёмником. Статус Solaar, WPID 40B4 и чтение настроек через Solaar вообще не
участвовали в этом решении. Даже при разрешённом чтении редактор загружал только
сохранённый YAML, не обращаясь к живым значениям. Это воспроизведено тестом:
подключённая G515, успешный Solaar, отдельный sysfs-пробник False.

Предоставленные пользователем диагностики: Solaar 1.1.20 обнаруживает G515 LS TKL,
WPID 40B4; CLI возвращает настройки, config.yaml читается, HOME корректен,
rgb_control=False. В доступном текущему агенту sysfs самой G515 нет; поэтому
физическая проверка этого случая здесь не заявляется.

Чтение локального файла и `!LEDEffectSetting` с BaseLoader успешно работает;
это не установленная причина ошибки. `False` разбирался корректно и не означает
отключение устройства. Однако прежний ранний gate скрывал все controls до
проверки этих данных. Имя `G515` допустимо как подстрока Solaar; теперь при наличии
единственной сохранённой записи используется её точное имя, в том числе
`G515 LS TKL`. Неоднозначные записи не выбираются случайно.

## Исправление

- G515 загружается независимо от результата вспомогательного sysfs ping.
  Worker запрашивает только шесть явно разрешённых настроек через Solaar CLI,
  без полного `config/show`, enumerating settings или startup/shutdown probes.
- `g515_adapter.py`: настоящие getters `rgb_control` и `brightness_control`
  имеют приоритет над локальным конфигом. False — доступное значение.
  Write-only RGB/per-key возвращают кэш Solaar. Host idle/sleep defaults не
  выдаются за чтение прошивки и не заменяют ранее сохранённые таймеры.
- Запросы не требуют наличия локального конфига. При частичных ошибках остаются
  доступные controls с объяснением; пустой stdout, `?` и ошибки парсинга никогда
  не считаются успешным пустым результатом. Кэш используется как fallback.
- Solaar YAML читается как данные без конструкторов объектов. Поддержаны
  `!LEDEffectSetting`, неизвестные теги и CLI-карта `{1:0xffffff}`. Сохраняется
  лимит 2 MiB; config lookup учитывает XDG_CONFIG_HOME, иначе HOME/.config.
- Scoped read-only процесс разрешает ровно одно известное поле без значения.
  Блокирует Setting.write/apply, overrides, базовые RW.write, запуск RGB manager;
  cleanup останавливает manager без проигрывания shutdown animation. Обычный
  явный путь записи сохранён. Установленные пакеты Solaar не менялись.
- stdout используется для данных; stderr при успешном exit code не портит
  парсинг. Ненулевой код вызывает Fault, а не успех по наличию stdout. Ошибки
  процесса относятся к Solaar, selector скрывается. Обработка процесса остаётся
  ограниченной по времени и отменяемой через существующий execution.command.
- Яркость использует диапазон/ступени initialized validator Solaar (см. уточнение
  ниже). Старые процентные черновики продолжают читаться. Непрерывный диапазон
  остаётся для backend без дискретных уровней.
- Epoch/binding и проверка единственного подключённого G515 сохраняются. Перед
  фактической записью CLI сам проверяет доступность выбранного устройства;
  ложный name-only sysfs gate больше не запрещает путь через приёмник.

## Проверка

`test_g515_adapter.py` использует предоставленную диагностику как фикстуру, а не
отправляет команды клавиатуре: False + все настройки без cache, live/cache merge,
таймеры-defaults, WPID/tagged YAML, XDG и неоднозначность, stdout/stderr/exit,
невалидный вывод и запрет записи/полного enumeration в read-only процессе.
`test_g515_editor.py` покрывает False sysfs gate и сохранение редактора.
Результаты интеграционных тестов и smoke записаны в implementation-progress.md.
Ни настройки оборудования, ни разрешения, ни конфиг пользователя не изменялись.

Ручная read-only проверка после запуска новой версии: открыть G515 → настройки
клавиатуры, увидеть управление RGB «Выключено» и остальные настройки. Ничего не
применять; исходная подсветка должна сохраниться. Полнота поддержки G HUB этим
исправлением не заявляется.


## 2026-10-29 — brightness snapping in patched Solaar builds

The supplied screenshots show G515 brightness requested as 45/54 with actual
readback 50. The locally installed Solaar BrightnessControl.write explicitly
snaps values using halving_marks(validator.max_value, validator.steps). Therefore
comparing arbitrary slider values to the snapped readback produced a genuine
numerical mismatch; it was not an S9 lighting error or proof of a failed write.

The existing allowlisted read-only worker now annotates the single brightness
getter with its already initialized validator limits and, when supported by the
installed implementation, its native halving marks. No extra HID requests,
settings writes, full enumeration, installed-library changes or inferred levels
are introduced. For max=100/steps=5, the backend helper returns
[0,13,25,50,100]; this example is not a fixed list assigned to every keyboard.
Stock builds without snapping retain a range control.

The adapter validates metadata and exposes native levels as a QML selector.
Only supported levels can be applied. Exact device readback remains mandatory:
true mismatches retain the draft and error; no tolerance or success masking is
added. Metadata is transient and never stored as user hardware configuration.
Old off-grid drafts remain editable but must be changed to an available level
before Apply. User device confirmation of the new selector is still pending.

Tests cover metadata extraction without I/O, continuous-backend compatibility,
malformed metadata rejection, native-level validation, confirmed readback and
mismatch/draft retention. G515 QML smoke covers RU/EN at 640/1280 with the native
selector; commands go only to the existing fake runner.
