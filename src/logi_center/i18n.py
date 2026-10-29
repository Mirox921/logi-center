"""English translations for the Russian source UI. No external dependencies."""
LANGUAGE='ru'
EN={
'Аппаратный профиль':'Hardware profile',
'Профиль по кэшу ratbagd':'Profile from ratbagd cache',
'ratbagd сообщает другой профиль':'ratbagd reports a different profile',
'Показаны настройки аппаратного профиля. Перед записью синхронизируй ratbagd; открытие страницы не меняет устройство.':'Settings of the hardware profile are shown. Synchronize ratbagd before writing; opening this page does not change the device.',
'Синхронизировать профиль':'Synchronize profile',
'Библиотека макросов':'Macro library',
'Кнопка назначения':'Assignment button',
'Новый макрос':'New macro',
'Название макроса':'Macro name',
'Сохранить в библиотеку':'Save to library',
'Библиотека макросов повреждена. Исходный файл сохранён; запись в библиотеку отключена.':'The macro library is damaged. The original file is preserved; library writes are disabled.',
'Остановить запись':'Stop recording',
'Начать запись':'Start recording',
'Записывать паузы':'Record delays',
'Запись: нажимай клавиши и щёлкай в этой области. Остановка — кнопкой выше.':'Recording: press keys and click in this area. Use the button above to stop.',
'Здесь записываются щелчки. Клавиши записываются только пока это окно активно.':'Mouse clicks are recorded here. Keys are recorded only while this window is active.',
'Библиотека хранится локально. Сохранение не меняет мышь. Системные сочетания Wayland могут перехватываться рабочим столом.':'The library is stored locally. Saving does not change the mouse. Wayland system shortcuts may be intercepted by the desktop.',
'Удалить событие':'Remove event',
'Сверху':'Top',
'Сбоку':'Side',
'Верхние и боковые кнопки показаны отдельно. Механическая разблокировка колеса не переназначается.':'Top and side buttons are shown separately. The mechanical wheel release cannot be reassigned.',
'Щелчки записаны в библиотеку, но запись мышиных событий в аппаратный макрос G502 этим backend не подтверждена. Макрос не отправлен.':'Clicks are recorded in the library, but storing mouse events in a G502 hardware macro is unverified with this backend. The macro was not sent.',
'Проверь имя и завершённость нажатий макроса.':'Check the macro name and ensure every press has a release.',
'Остановить воспроизведение':'Stop playback',
'Предыдущий эффект':'Previous effect',
'Проверка нажатий':'Key event test',
'Тест получает обычные события клавиш только в этой области. Ход магнитного переключателя не измеряется. Esc завершает тест.':'The test receives ordinary key events only in this area. It does not measure magnetic switch travel. Press Esc to finish.',
'Начать проверку клавиш':'Start key test',
'Нажми клавишу…':'Press a key…',
'Проверка остановлена':'Test stopped',
'Левая кнопка мыши':'Left mouse button',
'Правая кнопка мыши':'Right mouse button',
'Средняя кнопка мыши':'Middle mouse button',
'Ярче':'Brighter',
'Темнее':'Dimmer',
'Выключить подсветку':'Turn lighting off',
'Разные значения':'Mixed values',
'Выбрано клавиш':'Selected keys',
'Выбрать WASD':'Select WASD',
'Выбрать все':'Select all',
'Инвертировать выбор':'Invert selection',
'Снять выделение':'Clear selection',
'Значения на схеме':'Diagram values',
'Прочитать поклавишные цвета':'Read per-key colors',
'Сначала примени режим поклавишных цветов, затем прочитай банк и выбери клавиши. Цвета сохраняются в клавиатуре; приложение не запускает анимацию.':'Apply Custom mode first, then read the bank and select keys. Colors are stored on the keyboard; no application animation loop is used.',
'Изменения относятся к выбранным клавишам. «Применить» сохраняет все черновики срабатывания текущего профиля.':'Changes affect the selected keys. Apply saves all trigger drafts in the current profile.',
'Выбери клавиши на схеме':'Select keys on the diagram',
'Можно выбрать несколько клавиш или воспользоваться кнопкой WASD.':'Select multiple keys or use the WASD button.',
'На схеме показан предпросмотр, а не измеренное свечение клавиш.':'The diagram shows a preview, not measured key lighting.',
'Возможности, требующие проверки протокола':'Features awaiting protocol validation',
'Калибровка, смена типа переключателя, точности и прошивки не выполняются из этого редактора.':'Calibration, switch type, precision and firmware changes are unavailable in this editor.',
'Пункты из M HUB не становятся доступными для записи только по наличию на скриншоте. Существующая конфигурация сохраняется.':'M HUB screenshots alone do not establish safe write support. Existing configuration is preserved.',
'Прочитать назначения':'Read assignments',
'Выбранный слой редактируется отдельно; просмотр слоя не переключает режим клавиатуры.':'Each layer is edited independently; viewing a layer does not switch keyboard mode.',
'Текущее назначение':'Current assignment',
'Назначения ещё не прочитаны.':'Assignments have not been read yet.',
'Действие добавляется в черновик выбранных клавиш. Запись — после «Применить». Последняя Fn-клавиша защищена.':'The action is drafted for the selected keys. Writing requires Apply. The last Fn key is protected.',
'Прочитать расширенные привязки':'Read advanced bindings',
'RS и SOCD: выбери две клавиши. DKS, MT и TGL: одну. Привязки выполняются прошивкой; программа не эмулирует нажатия.':'Select two keys for RS or SOCD; one for DKS, MT or TGL. Bindings run in firmware; the application does not emulate input.',
'Новая привязка':'New binding',
'Действие':'Action',
'Начало нажатия':'Press start',
'Конец нажатия':'Press end',
'Начало отпускания':'Release start',
'Конец отпускания':'Release end',
'Порог удержания, мс':'Hold threshold, ms',
'Приоритет SOCD':'SOCD priority',
'Последняя нажатая':'Last input priority',
'Первая клавиша пары':'First key priority',
'Вторая клавиша пары':'Second key priority',
'Взаимная отмена':'Cancel both',
'Коды фаз и приоритета соответствуют M HUB. Пороговые точки DKS сохраняются; неподтверждённые миллиметры не подставляются.':'Phase and priority codes match M HUB. DKS travel points are preserved; unverified millimeter values are not substituted.',
'Добавить в черновик':'Add to draft',
'Запись — только после «Применить», по одной привязке. Изменения остальных клавиш и слоёв сохраняются. Физическая работа новых привязок пока не проверена.':'Writing requires Apply, one binding at a time. Other keys and layers are preserved. New bindings have not yet been physically tested.',
'Редактировать':'Edit',
'Направление эффекта':'Effect direction',
'Блокировка Win':'Win Lock',
'Защита от случайных нажатий':'Stability mode',
'Оптимизация дребезга':'Debounce optimization',
'Адаптивная калибровка (бета)':'Adaptive calibration (beta)',
'Режим клавиатуры':'Keyboard mode',
'Флаг включает автоматическую калибровку в прошивке. Снимок настроек не сохраняет измеренную калибровку сенсоров.':'This flag enables automatic firmware calibration. The settings snapshot does not preserve measured sensor calibration.',
'Режим Mac отключает блокировку Win; остальные настройки сохраняются.':'Mac mode disables Win Lock; other settings are preserved.',
'Назначение клавиши':'Key assignment',
'Прямое':'Forward',
'Обратное':'Reverse',
'Поклавишные цвета':'Per-key colors',
'Вертикальная волна':'Vertical wave',
'Из центра':'Center spread',
'Мерцание звёзд':'Star twinkle',
'Диско':'Disco',
'Линейный градиент':'Linear gradient',
'Снизу вверх':'Bottom up',
'Взаимный отскок':'Reciprocal rebound',
'Вращение из центра':'Center spin',
'Диагональный поток':'Diagonal flow',
'Лазерный дождь':'Laser rain',
'Мерцание точек':'Dot twinkle',
'Фейерверк':'Fireworks',
'Треугольный отскок':'Triangle bounce',
'Постоянная рябь':'Solid ripple',
'Рябь от клавиши':'Key ripple',
'След клавиши':'Key trail',
'Фейерверк клавиши':'Key firework',
'Луч клавиши':'Key beam',
'Расширенная привязка':'Advanced binding',
'Привязка недоступна: проверь клавиши, действия и параметры. Существующие данные сохранены.':'Binding unavailable: check keys, actions and parameters. Existing data is preserved.',
'Неизвестный формат привязки сохранён без изменений.':'Unrecognized binding format was left unchanged.',
'Назначение недоступно для выбранных клавиш.':'Assignment unavailable for the selected keys.',
'Значение не подходит всем выбранным клавишам.':'The value is not valid for all selected keys.',
'Блокировка Win недоступна в режиме Mac.':'Win Lock is unavailable in Mac mode.',
'Цвет выбранных клавиш':'Selected key color',
'Срабатывание':'Trigger',
'Назначения':'Key config',
'Расширенные клавиши':'Advanced keys',
'Производительность':'Performance',
'Прочее':'Others',
'Макрос на устройстве':'Onboard macro',
'Назначение не распознано':'Unrecognized assignment',
'Воспроизведение / пауза':'Play / pause',
'Следующий эффект':'Next effect',
'Ускорить эффект':'Faster effect',
'Замедлить эффект':'Slower effect',
'Следующий цвет':'Next color',
'Выделить всё':'Select all',
'Колесо вверх':'Wheel up',
'Колесо вниз':'Wheel down',

'Встроенный указатель':'Built-in pointer',
'Сенсорная панель':'Touchpad',
'Тачпад':'Touchpad',
'Мышь':'Mouse',
'Игровая мышь':'Gaming mouse',
'Беспроводная мышь':'Wireless mouse',
'Компактная мышь':'Compact mouse',
'Клавиатура':'Keyboard',
'Клавиатура 60%':'60% keyboard',
'Клавиатура 65%':'65% keyboard',
'Клавиатура TKL':'TKL keyboard',
'Полноразмерная клавиатура':'Full-size keyboard',
'Клавиатура ноутбука':'Laptop keyboard',
'Аудиоинтерфейс':'Audio interface',
'Встроенные динамики':'Built-in speakers',
'Нет настроек':'No settings',
'%1 настройка':'%1 setting',
'%1 настройки':'%1 settings',
'%1 настроек':'%1 settings',
'Нет данных':'No data',
'Последний заряд: %1':'Last charge: %1',
'Актуальность не подтверждена':'Freshness unconfirmed',
'Критический заряд':'Critical charge',
'Обобщённая графика':'Generalized artwork',
'Пользовательское изображение':'User image',
'Изображение недоступно':'Artwork unavailable',
'Источники и изображение':'Sources and artwork',
'Файл изображения':'Artwork file',
'Читаются только доступные сведения':'Information only',

'Анимация отключена системой':'Animations are disabled by the system',

'Ничего не найдено':'No matches found',
'В этой категории нет устройств':'No devices in this category',
'Измени поиск или очисти фильтры.':'Change your search or clear the filters.',

'Встроенные':'Built-in',
'Очистить поиск':'Clear search',
'Уменьшить анимацию':'Reduce motion',
'Параметры сохраняются локально. Аппаратные настройки не изменяются.':'Preferences are saved locally. Hardware settings remain unchanged.',
'Не удалось сохранить настройки интерфейса.':'Could not save interface preferences.',

'До восстановления':'Before restore',

'Чувствительность нажатия RT':'RT press sensitivity',
'Чувствительность отпускания RT':'RT release sensitivity',
'Мёртвая зона нажатия':'Press dead zone',
'Мёртвая зона отпускания':'Release dead zone',
'Отключение подсветки при бездействии':'Idle lighting timeout',
'Задержка перехода в сон':'Sleep timeout',
'Профиль':'Profile',
'Кнопка':'Button',
'Частота опроса':'Polling rate',

'Задержка кнопок':'Button debounce',
'Энергосбережение':'Power saving',
'Ступень DPI':'DPI stage',
'Ступени DPI':'DPI stages',
'Скорость эффекта':'Effect speed',
'Палитра подсветки':'Lighting palette',
'Остановить':'Stop',
'Операция отменяется…':'Cancelling…',

'Получено:':'Received:',
'Защитная копия:':'Safety snapshot:',

'Контрольная сумма или формат копии неверны':'Backup checksum or format is invalid',
'Для восстановления требуется подтверждённое подключение устройства.':'Restore requires a confirmed device connection.',

'Возможности устройства':'Device capabilities',
'Стандартная копия':'Standard backup',
'Настройки звукового сервера':'Audio server settings',
'Локальные настройки G515':'Local G515 settings',
'Подключение изменилось. Открой предпросмотр заново.':'Connection changed. Open the preview again.',
'Контрольная сумма копии неверна':'Backup checksum is invalid',
'Копия не соответствует модели устройства':'Backup does not match the device model',
'Состояние изменилось. Открой предпросмотр заново.':'State changed. Open the preview again.',
'Операция не выполнена. Проверь файл, подключение и доступ к устройству.':'Operation failed. Check the file, connection and device access.',
'Выбери поля и нажми «Восстановить выбранное».':'Choose fields, then select Restore selected.',
'Подтверждено чтением':'Confirmed by readback',
'Отправлено, не подтверждено':'Sent, unconfirmed',
'Сохранено локально':'Saved locally',
'Значение не совпало':'Value did not match',
'Устройство отключено; результат требует проверки':'Device disconnected; verify the result',
'Операция отменена; результат требует проверки':'Operation cancelled; verify the result',
'Ошибка применения':'Apply failed',
'Не выполнено':'Not performed',
'Восстановление остановлено. Проверь результаты по полям.':'Restore stopped. Check results for each field.',
'Операция завершена. Проверь подтверждение каждого поля.':'Operation finished. Check confirmation for each field.',
'Защитная копия сохранена приватно.':'A private safety snapshot was saved.',
'Симуляция: аппаратные настройки не изменены.':'Simulation: hardware settings were not changed.',
'Чтение с устройства':'Device read',
'Кэш демона':'Daemon cache',
'Локальные настройки':'Local settings',
'Звуковой сервер':'Audio server',
'Источник неизвестен':'Unknown source',
'Открыть резервную копию':'Open backup',
'Открыть копию':'Open backup',
'Открыть в GTK':'Open in GTK',
'Экспортировать':'Export',
'Проверь подключение и доступность backend.':'Check the connection and backend availability.',
'Пропущенные поля и технические подробности':'Skipped fields and technical details',

'Настройки':'Settings',
'Резервные копии':'Backups',
'Язык интерфейса':'Interface language',
'Предпросмотр':'Preview',
'%1 внешних · %2 встроенных · обновлено %3':'%1 external · %2 built-in · updated %3',
'Инструменты':'Tools',
'Настройки, резервные копии и диагностика':'Settings, backups and diagnostics',
'О программе':'About',
'Настройки этой сессии. Аппаратные параметры не изменяются.':'Session settings. Hardware settings remain unchanged.',
'Единый центр управления периферией Linux':'One control center for Linux peripherals',
'Нет доступных настроек для резервного копирования':'No settings available for backup',
'Не удалось открыть резервные копии GTK. Проверь доступ к графической сессии.':'Could not open GTK backups. Check access to your desktop session.',

'Код изображения':'Image slug',
'Неизвестное устройство':'Unknown device',
'Поиск устройств по названию':'Search devices by name','Устройства с таким названием не найдены':'No devices match this name',
'СИМУЛЯЦИЯ':'SIMULATION',
'Неоднозначный идентификатор backend':'Ambiguous backend identifier',
'Макросы':'Macros','Стандартный ввод':'Standard input','Заряд аккумулятора':'Battery','Без звука':'Muted',
'Другие доступные настройки можно проверить в Solaar.':'Other available settings can be checked in Solaar.',
'Данные аудиоустройства неполные; управление недоступно.':'Audio device data is incomplete; controls are unavailable.',
'Текущее значение: ':'Current value: ',
'Проверить отдельные настройки Solaar':'Probe individual Solaar settings','Явный запрос чтения. Только сообщённые backend варианты станут доступны для изменения.':'Explicit read request. Only backend-reported choices become writable.','Проверить':'Probe',
'Backend не подтвердил поддержку этого назначения для выбранной кнопки.':'The backend has not confirmed support for this assignment on the selected button.',
'Экспортировать отчёт JSON':'Export JSON report','Параметр':'Setting','Сейчас':'Current','Из копии':'From backup','Ожидаемое действие':'Expected action',
'Мыши через libratbag':'Mice via libratbag',
'Аудиоустройства Linux. Уровни применяются только по кнопке; выше 100% усиление не задаётся.':'Linux audio devices. Levels change only on request; gain above 100% is not set.',
'Устройства':'Devices',
'Клавиатуры':'Keyboards',
'СИМУЛЯЦИЯ: реальные устройства и аудиозапись отключены.':'SIMULATION: real devices and audio capture are disabled.',
'Аудиоустройства не обнаружены':'No audio devices detected',
'Проверь подключение и открой диагностику компонентов.':'Check the connection and open component diagnostics.',
'Стандартный ввод Linux; дополнительные функции показаны во вкладке устройств.':'Linux standard input; additional capabilities are listed in Devices.',
'Клавиатуры не обнаружены':'No keyboards detected',
'Дополнительные аппаратные функции требуют совместимого backend.':'Additional hardware features require a compatible backend.',
'Справочная раскладка выбрана вручную. Переназначение и подсветка отдельных клавиш не обнаружены.':'Reference layout selected manually. Per-key remapping and lighting have not been detected.',
'Обнаружено':'Detected',
'Не поддерживается устройством':'Unsupported by device',
'Поддержка не проверена':'Support not verified',
'Чтение и изменение':'Read and write',
'Изменение без чтения':'Write without readback',
'Только чтение':'Read only',
'Только информация backend':'Backend information only',
'Возможно повторное чтение':'Readback available',
'Аппаратное подтверждение недоступно':'Hardware verification unavailable',
'Источник: ':'Source: ',
'Устройства не обнаружены':'No devices detected',
'СИМУЛЯЦИЯ · ':'SIMULATION · ',
'Возможности не прочитаны':'Capabilities not read',
'Наличие устройства не означает поддержку настройки через backend.':'Device detection does not imply backend configuration support.',
'Ошибка чтения':'Read error',
'Диагностика backend':'Backend diagnostics',

'Доступно только локальное значение':'Only a locally saved value is available','Операция не поддерживается':'Operation unsupported','Нет доступа':'Access denied','Подтверждено звуковым сервером':'Confirmed by the audio server','Загрузить текущее':'Use current value','Черновик сохранён, но состояние устройства изменилось. Проверь значения или загрузи текущее.':'Draft retained, but device state changed. Review the values or use the current value.',
'Схема расположения кнопок · не отображает текущий цвет подсветки':'Button layout illustration · does not show the current lighting color',
'Кнопки':'Buttons','Подсветка':'Lighting','Профиль':'Profile','Звук':'Audio',
'Диагностика':'Diagnostics','Диагностика компонентов':'Component diagnostics','Скопировать отчёт без личных данных':'Copy redacted report','Закрыть':'Close',
'Не установлен компонент':'Component not installed','Установи пакет из репозитория своего дистрибутива.':'Install the package from your distribution repository.',
'Компонент установлен, но не работает':'Component installed but unavailable','Проверь версию и зависимости компонента; попробуй запустить его отдельно.':'Check the component version/dependencies and try running it separately.',
'Нет доступа к устройству или программе':'Access denied to device or component','Переподключи устройство и проверь правила доступа из пакета backend. Не используй chmod 777.':'Reconnect the device and check packaged backend access rules. Do not use chmod 777.',
'Функция не поддерживается':'Feature unsupported','Проверь возможности модели и версию backend.':'Check the device capabilities and backend version.',
'Подключи или включи устройство. Список обновится автоматически.':'Connect or turn on the device. The list updates automatically.',
'Истекло время ожидания':'Operation timed out','Проверь связь с устройством и повтори действие.':'Check the device connection and retry.',
'Состояние устройства изменилось или приложение закрывается.':'The device state changed or the application is closing.',
'Ошибка связи с устройством или сервисом':'Device or service communication error','Проверь, запущен ли нужный сервис, и подключено ли устройство.':'Check the service is running and the device is connected.',
'Некорректная конфигурация':'Invalid configuration','Проверь формат файла и совместимость с устройством.':'Check the file format and device compatibility.',
'Внутренняя ошибка приложения':'Internal application error','Сохрани диагностический отчёт и сообщи об ошибке.':'Save the diagnostic report and report the issue.',
'Программа найдена; аппаратные функции проверяются при использовании.':'Executable found; hardware functions are checked when used.',
'Поддерживаемая мышь не найдена.':'No supported mouse found.','Доступ к интерфейсу устройства есть.':'Device interface is accessible.','доступных источников; запись не запускалась.':'available sources; recording was not started.',
'Устройство не поддерживает функцию':'Device does not support this feature','Выбери доступную функцию для этой модели.':'Choose a supported feature for this model.',
'Backend не поддерживает операцию':'Backend does not support this operation','Проверь установленную версию backend и его возможности.':'Check the installed backend version and capabilities.',

'Наушники и динамики':'Headphones and speakers','Общий обход обработки влияет и на микрофон, и на наушники.':'Global bypass affects both microphone and headphone processing.',
'Пресеты микрофона':'Microphone presets','Пресеты наушников':'Headphone presets','Настройки входа и выхода сохраняются раздельно.':'Input and output settings are saved separately.',
'Импортируй файл для нужного направления или открой редактор эффектов.':'Import a preset for this direction or open the effects editor.','Проверка микрофона':'Microphone test',
'Микрофон не найден':'No microphone found','Микрофон не прослушивается. Нажми кнопку для начала.':'The microphone is not being captured. Click a button to start.',
'Показать уровень микрофона':'Show microphone level','Записать образец — до 8 секунд':'Record a sample — up to 8 seconds','Завершить запись':'Finish recording',
'Прослушать исходный':'Play original','Прослушать обработанный':'Play processed','Удалить образцы и остановить тест':'Delete samples and stop test',
'Запись временная: удаляется при обновлении, отключении устройства или закрытии приложения. Обработанный образец доступен только при подтверждённом маршруте EasyEffects от выбранного микрофона.':'Recordings are temporary and deleted on refresh, disconnect or exit. A processed sample is available only with a confirmed EasyEffects route from the selected microphone.',
'Подключи микрофон и проверь диагностику компонентов.':'Connect a microphone and check component diagnostics.','Тест остановлен, временные образцы удалены.':'Test stopped; temporary samples deleted.',
'Идёт запись исходного и обработанного сигнала…':'Recording original and processed signals…','Идёт запись только исходного сигнала: маршрут обработки не подтверждён.':'Recording original only: the processing route is not confirmed.',
'Образец готов. Можно прослушать доступные сигналы.':'Sample ready. You can play the available signals.',

'Визуальный редактор кнопок':'Visual button editor','Схема мыши: выбери кнопку. Изменения остаются черновиком до применения.':'Mouse schematic: select a button. Changes remain a draft until applied.',
'Собственный макрос':'Custom macro','Записать клавиши':'Record keys','Добавить паузу':'Add delay','Очистить':'Clear','Отменить черновик':'Discard draft',
'Кнопка ':'Button ','Редактирование макросов не подтверждено backend для этой кнопки.':'The backend has not confirmed macro editing for this button.',
'Остановить запись клавиш':'Stop recording keys','Нажимай клавиши в этом окне. Системные сочетания могут перехватываться рабочим столом.':'Press keys in this window. Desktop shortcuts may be intercepted by your compositor.',
'Эта клавиша пока не поддерживается редактором.':'This key is not supported by the editor yet.','Макросы для этой кнопки недоступны.':'Macros are unavailable for this button.',
'Сочетание может конфликтовать с рабочим столом. Нажми «Применить» повторно для подтверждения.':'This shortcut may conflict with the desktop. Click Apply again to confirm.',

'Резервная копия':'Backup and recovery','Источник данных указан в файле; локальные настройки не являются аппаратной копией.':'The file identifies its source; local settings are not a hardware image.',
'Сохранить настройки устройства':'Save device settings','Восстановить настройки':'Restore settings','Копия сохранена. Источник: ':'Backup saved. Source: ',
'Предпросмотр восстановления':'Restore preview','Источник копии: ':'Backup source: ',
'Перед изменениями будет сохранена защитная копия. При ошибке восстановление остановится; автоматический откат не гарантируется.':'A safety snapshot is saved before changes. Restore stops on failure; automatic rollback is not guaranteed.',
'Пропущено: ':'Skipped: ','Изменений нет':'No changes','Отмена':'Cancel','Восстановить выбранное':'Restore selected',
'Защитная копия: ':'Safety snapshot: ','Восстановление остановлено после ошибки. Проверь частично применённые настройки.':'Restore stopped after an error. Review the partially applied settings.',

'Подтверждено устройством':'Confirmed by device/service','Команда отправлена, подтверждение недоступно':'Command sent; confirmation unavailable',
'Значение не совпадает':'Value mismatch','Ошибка применения':'Apply failed','Устройство отключено':'Device disconnected','Операция отменена':'Operation cancelled',
'Ответ из кэша backend, не аппаратное подтверждение':'Backend cache readback, not hardware confirmation','Запрошено: ':'Requested: ','Получено: ':'Reported: ',

'Мышь':'Mouse','Игровые мыши Logitech':'Logitech gaming mice','Подключена по USB':'Connected via USB','Проводной мыши батарея не нужна.':'A wired mouse does not need a battery.',
'Активный профиль не определён':'Active profile not detected','Обнови настройки мыши перед изменениями.':'Refresh mouse settings before making changes.',
'Изменения применяются только к выбранному профилю.':'Changes apply only to the selected profile.','Профиль ':'Profile ','Встроенный профиль':'Onboard profile',
'Уровень ':'Stage ','Активный уровень чувствительности':'Active DPI stage','Кнопка снижения DPI при удержании':'DPI shift button',
'Уменьшить DPI':'Decrease DPI','Увеличить DPI':'Increase DPI','Кнопка переключения профиля':'Profile switch button',
'Наклон колёсика вправо':'Tilt wheel right','Наклон колёсика влево':'Tilt wheel left','Снижение DPI при удержании':'DPI shift while held',
'Следующий профиль':'Next profile','G-Shift':'G-Shift','Зона подсветки ':'Lighting zone ',
'Показаны данные профиля; фактический цвет может отличаться.':'Saved profile data is shown; the physical color may differ.',

'Управление устройством':'Device actions',
'Твои устройства · один центр управления':'Your devices · one control center','Обновить устройства':'Refresh devices',
'Чтение устройств…':'Reading devices…','Выполняется…':'Working…','Готово':'Ready',
'Не удалось выполнить действие. Проверь подключение устройства.':'Could not complete the action. Check the device connection.',
'Настройка не применена. Проверь подключение и попробуй ещё раз.':'Setting was not applied. Check the connection and try again.',
'Настройка применена':'Setting applied','Применить':'Apply','Мышь ':'Mouse ','Клавиатура ':'Keyboard ',
'Мышь G305':'G305 mouse','Клавиатура G515':'G515 keyboard',' · Проверка заряда…':' · Checking battery…',
'Мышь сообщает уровень заряда без точного процента.':'The mouse reports a battery level, not an exact percentage.',
'Обновляется каждые 30 секунд. ':'Updates every 30 seconds. ','Показание устройства.':'Reported by the device.',
'Связь не подтверждена':'Connection not confirmed','Не в сети':'Offline','Подключена':'Connected',
'Поиск мыши…':'Looking for mouse…','Поиск клавиатуры…':'Looking for keyboard…','Чтение аудиоустройств…':'Reading audio devices…',
'Настрой скорость движения указателя, плавность и действия кнопок.':'Adjust pointer sensitivity, polling rate and button actions.',
'Прочитать настройки':'Read settings','Мышь недоступна':'Mouse unavailable','Включи мышь и подключи USB-приёмник.':'Turn on the mouse and connect its USB receiver.',
'Расширенный редактор':'Advanced editor','Полный интерфейс Piper: профили и макросы.':'Full Piper editor for profiles and macros.',
'Открыть Piper':'Open Piper','Открыть Solaar':'Open Solaar','Все настройки клавиатуры':'All keyboard settings',
'Выбери яркость, цвет и поведение подсветки.':'Choose lighting brightness, color and effects.',
'Клавиатура не в сети':'Keyboard offline','Не удалось проверить связь':'Could not verify connection',
'Сохранённые настройки доступны для просмотра. Включи клавиатуру и обнови список.':'Saved settings are shown. Turn on the keyboard and refresh devices.',
'Настройки недоступны':'Settings unavailable','Подключи клавиатуру и нажми кнопку обновления вверху окна.':'Connect the keyboard and click Refresh at the top.',
'Управление подсветкой из приложения':'Control lighting from this app','Приглушать подсветку при бездействии':'Dim lighting when idle',
'Выключать подсветку при бездействии':'Turn lighting off when idle','Включено':'Enabled','Выключено':'Off','Выключена':'Off','Никогда':'Never',
'Через 15 секунд':'After 15 seconds','Через 30 секунд':'After 30 seconds','Через минуту':'After 1 minute',
'Через 2 минуты':'After 2 minutes','Через 5 минут':'After 5 minutes','Через 10 минут':'After 10 minutes',
'Через 15 минут':'After 15 minutes','Через 30 минут':'After 30 minutes','Яркость подсветки':'Lighting brightness',
'Режим подсветки':'Lighting effect','Выбери эффект и цвет, затем нажми «Применить».':'Choose an effect and color, then click Apply.',
'Статичный цвет':'Solid color','Дыхание':'Breathing','Цикл цветов':'Color cycle','Выбери цвет подсветки':'Choose lighting color',
'Выбрать любой цвет':'Choose any color','Белый':'White','Красный':'Red','Оранжевый':'Orange','Жёлтый':'Yellow',
'Зелёный':'Green','Голубой':'Light blue','Синий':'Blue','Фиолетовый':'Purple','Розовый':'Pink','Подсветка применена':'Lighting applied',
'Цвета по клавишам и сложные параметры пока редактируются в Solaar.':'Per-key colors and advanced settings are edited in Solaar.',
'Звук и микрофон':'Sound and microphone','Выбери USB-карту G Pro X. Уровни применяются только по кнопке; выше 100% усиление не задаётся.':'Select the G Pro X USB sound card. Levels change only when applied and are limited to 100%.',
'Выход':'Output','Микрофон':'Microphone','Аудиоустройство':'Audio device','Монитор или телевизор (HDMI)':'Monitor or TV (HDMI)',
'Динамики ноутбука':'Laptop speakers','Встроенный микрофон':'Built-in microphone','Уровень громкости, %':'Volume, %',
'Громкость':'Set volume','По умолчанию':'Set as default','Вкл. микр.':'Unmute mic','Включить':'Enable','Заглушить':'Mute',
'USB-карта G Pro X пока не обнаружена':'G Pro X USB sound card not detected','Общие аудиоустройства доступны выше. Подключи карту и обнови список.':'Other audio devices are shown above. Connect the USB card and refresh.',
'Обработка звука':'Audio effects','Собственные пресеты EasyEffects можно включать отсюда. Редактирование цепочки эффектов открывается в его редакторе.':'Apply saved EasyEffects presets here. Use its editor to customize the effects chain.',
'Готовые эффекты сообщества':'Community presets','Настройки для микрофона и наушников. Откроются в браузере.':'Presets for microphones and headphones. Opens in your browser.',
'Найти готовые эффекты':'Browse presets','Добавить скачанный эффект':'Add a downloaded preset',
'Выбери файл .json для микрофона или наушников. Затем выбери его в списке ниже.':'Choose a microphone or headphone .json preset, then select it below.',
'Импортировать эффект':'Import preset','Пресет':'Preset','Пресетов пока нет':'No presets yet',
'Создай эквалайзер или обработку микрофона в редакторе EasyEffects.':'Create a headphone or microphone preset in the EasyEffects editor.',
'Эквалайзер и обработка микрофона':'Equalizer and microphone effects','Редактор эффектов':'Effects editor',
'Звуковые эффекты':'Sound processing','Эквалайзер и фильтры для наушников и микрофона. Без эффектов звук продолжает работать.':'Equalizer and filters for headphones and microphone. Audio still works when effects are bypassed.',
'С эффектами':'Effects on','Без эффектов':'Effects off','Гарнитура':'Headset',
'USB-карта подключена · можно настроить слышимость своего голоса':'USB sound card connected · sidetone available',
'Слышимость своего голоса':'Hear your own voice (sidetone)','Очень тихо':'Very quiet','Тихо':'Quiet','Средне':'Medium','Громко':'Loud','Максимально':'Maximum',
'Выбери желаемый уровень и нажми «Применить». Показан последний сохранённый выбор; текущее значение устройство не сообщает.':'Choose a level and click Apply. The last saved selection is shown; the device does not report its current level.',
'Настройки мыши':'Mouse settings','Мышь подключена':'Mouse connected','Настройки прочитаны. Изменения сохраняются по кнопке «Применить».':'Settings loaded. Click Apply to save each change.',
'Чувствительность DPI':'Pointer sensitivity (DPI)','Частота опроса, Гц':'Polling rate, Hz','Левая кнопка':'Left button','Правая кнопка':'Right button',
'Нажатие колёсика':'Middle click','Боковая кнопка «Назад»':'Back side button','Боковая кнопка «Вперёд»':'Forward side button',
'Кнопка переключения чувствительности':'DPI button','Левый щелчок':'Left click','Правый щелчок':'Right click','Назад':'Back','Вперёд':'Forward',
'Переключать чувствительность':'Cycle DPI','Копировать':'Copy','Вставить':'Paste','Вырезать':'Cut','Отменить':'Undo','Выделить всё':'Select all',
'Клавиша F':'F key ','Отключить кнопку':'Disable button','Не изменять':'Keep current action','Дополнительная кнопка':'Extra button',
'Сейчас: ':'Current: ','Собственное назначение':'Custom action','Импортировать готовый эффект':'Import a preset',
'Пресеты EasyEffects (*.json)':'EasyEffects presets (*.json)','Сначала скачай файл на компьютер.':'Download the file to your computer first.',
'Не удалось импортировать: ':'Import failed: ','Эффект добавлен: ':'Preset imported: ','. Выбери его и нажми «Применить».':'. Select it and click Apply.',
'Заряд недоступен':'Battery unavailable','Не подключено или спит':'Disconnected or asleep','Высокий заряд':'High battery','Средний заряд':'Medium battery',
'Требуется дополнительный компонент':'An additional component is required','Компонент сейчас недоступен':'The component is currently unavailable','Нет доступа к устройству':'No access to this device','Функция недоступна':'This feature is unavailable','Функция не поддерживается этим устройством':'This device does not support this feature','Backend не поддерживает операцию':'The backend does not support this operation','Не удалось связаться с устройством':'Could not communicate with the device','Устройство не ответило вовремя':'The device did not respond in time','Операция отменена':'The operation was cancelled','Ошибка связи с устройством':'Device communication error','Не удалось прочитать настройки устройства':'Could not read device settings','Дополнительные сведения доступны в диагностике.':'See Diagnostics for more information.',
'Настройки EWEADN':'EWEADN settings','Мышь доступна как устройство Linux. Встроенные DPI и частота опроса пока не подтверждены; неизвестные HID-команды не отправляются.':'The mouse is available as a Linux input device. Onboard DPI and polling rate are not confirmed; no unknown HID commands are sent.',
'Последнее значение: ':'Last reported: ','Устарело':'stale',
'Сохранённое значение: ':'Saved value: ',
'Главная':'Home','Звук':'Sound','Микрофон':'Microphone','Эквалайзер':'Equalizer','Эффекты':'Effects','Тест':'Test','Ещё':'More','подключено':'connected','Все устройства':'All devices',
'Проверь подключение; список обновится автоматически.':'Check the connection; the list updates automatically.','Основное устройство':'Primary device','Применить выбор':'Apply selection','Сделать выбранное устройство основным':'Set the selected device as default','Сделать основным':'Set as default',
'Основное устройство недоступно':'The default device is unavailable','Сначала выбери доступное устройство':'Select an available device first','Управление уровнем появится после выбора устройства.':'Level controls appear after you select a device.',
'Недоступно':'Unavailable','Доступность не подтверждена':'Availability not confirmed','Доступно':'Available','Управление уровнем недоступно':'Level controls are unavailable','Аудиосистема не сообщила текущее значение.':'The audio server did not report a current value.',
'Уровень громкости':'Output level','Уровень микрофона':'Microphone level','Звук выключен':'Sound muted','Звук включён':'Sound on','Включить звук':'Unmute','Выключить звук':'Mute','Заряд гарнитуры':'Headset battery',
'Устройства не найдены':'No devices found','Пресеты выхода':'Output presets','Эквалайзер наушников':'Headphone equalizer','Нет импортированных пресетов':'No imported presets','Импортируй профиль EasyEffects, чтобы он появился здесь.':'Import an EasyEffects profile to see it here.',
'Выбрать файл EasyEffects JSON':'Choose an EasyEffects JSON file','Импортировать эффект':'Import preset','Настройки эквалайзера':'Equalizer settings','Открыть редактор обработки звука':'Open the audio effects editor','Открыть EasyEffects':'Open EasyEffects',
'Эффекты звука':'Audio effects','Готовые эффекты':'Community presets','Открыть каталог пресетов EasyEffects':'Browse the EasyEffects preset catalog','Найти пресеты':'Browse presets','Цепочка обработки':'Effects chain','Настроить плагины и параметры':'Configure plugins and settings',
'Обработка звука':'Audio processing','Действует на микрофон и вывод звука':'Affects the microphone and audio output','Включить эффекты':'Enable effects','Обойти эффекты':'Bypass effects',
'Сохранить или восстановить доступные параметры':'Save or restore available settings','Другие выходы':'Other outputs','Другие микрофоны':'Other microphones','устройств':'devices','Аудиосистема':'Audio system','Компоненты и доступ к звуковым устройствам':'Audio components and device access',
'Низкий заряд':'Low battery','Пора заменить батарейку':'Replace the battery','Заряд неизвестен':'Battery unknown',' · заряжается':' · charging',' · заряжено':' · fully charged',
'Файл слишком большой для пресета (больше 2 МБ).':'Preset file exceeds the 2 MB limit.',
'Нужен пресет EasyEffects в формате JSON.':'Choose an EasyEffects JSON preset.',
'Это не пресет EasyEffects: настройки микрофона или наушников не найдены.':'Not an EasyEffects preset: no input or output settings found.',
'DPI по горизонтали':'Horizontal DPI','DPI по вертикали':'Vertical DPI','Возможности, сообщённые backend':'Backend-reported features',
'Предпросмотр отчёта JSON':'JSON report preview',
'Backend и компоненты':'Backends and components',
'Эффект подсветки':'Lighting effect','Яркость':'Brightness','Зоны подсветки':'Lighting zones','Ступень DPI':'Active DPI stage','Ступени DPI':'DPI stages','Задержка устранения дребезга, мс':'Debounce, ms','Таймер сна (единицы протокола)':'Sleep timer (protocol units)','Синхронизация сенсора':'Motion Sync','Подавление дрожания':'Ripple control','Выпрямление линий':'Angle snapping',
'Клавиатура не отвечает. Включи её и обнови список устройств.':'The keyboard is not responding. Turn it on and refresh devices.',
}
EN.update({'Точка срабатывания, мм': 'Actuation point, mm', 'Режим Rapid Trigger': 'Rapid Trigger mode', 'RT при нажатии, мм': 'RT press distance, mm', 'RT при отпускании, мм': 'RT release distance, mm', 'Верхняя мёртвая зона, мм': 'Upper dead zone, mm', 'Нижняя мёртвая зона, мм': 'Lower dead zone, mm', 'Параметры клавиш не прочитаны. Проверь доступ и диагностику устройства.': 'Key settings have not been read. Check device access and diagnostics.', 'Непрерывный RT': 'Continuous RT', 'Отменить черновик': 'Discard draft', 'Применить к выбранной клавише': 'Apply to selected key', 'Настройки магнитных клавиш прочитаны из устройства. Изменения применяются только по кнопке.': 'Magnetic key settings are read from the device. Changes require the Apply button.', 'Скорость эффекта': 'Effect speed'})

EN.update({'Версия прошивки': 'Firmware version', 'Версия USB-устройства': 'USB device release', 'Раскладка клавиатуры': 'Keyboard layout', 'Точка срабатывания': 'Actuation point', 'RT при нажатии': 'RT press distance', 'RT при отпускании': 'RT release distance', 'Верхняя мёртвая зона': 'Upper dead zone', 'Нижняя мёртвая зона': 'Lower dead zone', 'Параметры магнитных переключателей': 'Magnetic switch parameters', 'Динамическое нажатие (DKS)': 'Dynamic keystroke (DKS)', 'Переназначение клавиш': 'Key remapping', 'Слои клавиатуры': 'Keyboard layers', 'Настройка отдельных клавиш доступна во вкладке «Клавиатура».': 'Individual key settings are available in the Keyboard tab.'})

EN.update({'Палитра подсветки':'Lighting palette'})
EN.update({'Предпросмотр изображения':'Image preview','Использовать':'Use image','ПЕРЕДПРОСМОТР':'PREVIEW',
           'ИСПОЛЬЗОВАТЬ':'USE IMAGE',
           'Внешняя периферия':'External peripherals','Встроенные устройства':'Built-in devices','Другие устройства':'Other devices',
           'Заряд: нет данных':'Battery: no data','ПАРАМЕТРЫ':'SETTINGS','ЗАРЯДКА':'CHARGING',
           'ИМЯ':'NAME','ИЗОБРАЖЕНИЕ':'ARTWORK','СБРОСИТЬ':'RESET','СОХРАНИТЬ':'SAVE','ОТМЕНА':'CANCEL',
           'Системное изображение':'System image','Точная модель':'Exact model','Сгенерировано':'Generated','Резервное изображение':'Fallback image'})
EN.update({'Простая мышь · симуляция':'Simple mouse · simulation','Игровая мышь · симуляция':'Gaming mouse · simulation',
           'RGB-клавиатура · симуляция':'RGB keyboard · simulation','Обычная клавиатура · симуляция':'Standard keyboard · simulation',
           'USB-гарнитура · симуляция':'USB headset · simulation','Беспроводная гарнитура · симуляция':'Wireless headset · simulation',
           'Частично доступное устройство · симуляция':'Partially available device · simulation',
           'Отключение во время операции · симуляция':'Disconnect during operation · simulation',
           'Тестовая мышь Logitech · симуляция':'Logitech mouse fixture · simulation',
           'Тестовая мышь MCHOSE · симуляция':'MCHOSE mouse fixture · simulation',
           'Тестовая мышь Razer · симуляция':'Razer mouse fixture · simulation',
           'Тестовая клавиатура Corsair · симуляция':'Corsair keyboard fixture · simulation',
           'Тестовая мышь SteelSeries · симуляция':'SteelSeries mouse fixture · simulation',
           'Беспроводная мышь · зарядка · симуляция':'Wireless mouse · charging · simulation',
           'Устройство без настройки · симуляция':'Unconfigured device · simulation','Симулированное устройство':'Simulated device',
           'СИМ':'SIM','УПРАВЛЕНИЕ УСТРОЙСТВАМИ':'PERIPHERAL CONTROL'})

EN.update({'Открыть': 'Open', 'Настройки устройства': 'Device settings', 'Нет доступа к заряду': 'Battery access denied', 'Сохранённое значение': 'Cached value', 'Устаревшее значение': 'Stale value', 'Свежесть неизвестна': 'Freshness unknown', 'Встроенное устройство': 'Internal device', 'Тип соединения неизвестен': 'Unknown connection type', 'Мыши не обнаружены': 'No mice detected', 'Подключи устройство. Сохранённые черновики останутся доступны после подключения.': 'Connect a device. Saved drafts remain available after reconnection.', 'Выбрать устройство': 'Select device', 'Аккумулятор': 'Battery', 'Обзор': 'Overview', 'Возможности устройства': 'Device capabilities', 'Доступны только настройки, предоставленные обнаруженными backend.': 'Only settings provided by detected backends are available.', 'Чувствительность и скорость': 'Sensitivity and speed', 'Диагностика возможностей': 'Capability diagnostics', 'Почему некоторые настройки недоступны': 'Why some settings are unavailable', 'Все устройства': 'All devices', 'Вернуться к устройствам': 'Back to devices', 'Диагностика и дополнительные инструменты': 'Diagnostics and tools', 'Устройства и компоненты': 'Devices and components', 'Полный диагностический отчёт': 'Full diagnostic report', 'Пресеты микрофона': 'Microphone presets', 'Обработка микрофона': 'Microphone processing', 'Профили микрофона EasyEffects появятся после импорта.': 'Imported EasyEffects microphone profiles will appear here.', 'Уровень громкости': 'Output level', 'Уровень микрофона': 'Microphone level'})

EN.update({'Клавиши':'Keys','Профили':'Profiles','Дополнительные функции':'Additional features'})

EN.update({'параметр':'setting','параметров':'settings','Назад':'Back','Диагностика и устройства':'Diagnostics and devices',
           'Твои устройства · один центр управления':'Your devices · one place to manage them',
           'Подключённая периферия':'Connected peripherals','Поиск устройств':'Search devices','Обновить':'Refresh',
           'Все':'All','Аудио':'Audio','Показывать встроенные':'Show built-in devices','Подключённые устройства появятся здесь':'Connected devices will appear here',
           'Устройство отключено':'Device disconnected','Симуляция · аппаратные операции недоступны':'Simulation · hardware operations unavailable',
           'Обзор возможностей':'Capability overview','доступных настроек':'available settings','Нет доступных настроек':'No settings available','Настройки доступны на следующих этапах переноса. Сейчас эта страница показывает подтверждённые возможности устройства.':'Settings will be added in later migration phases. This page currently shows confirmed device capabilities.',
           'Значение получено':'Value read','Чтение недоступно':'Reading unavailable','Неизвестно':'Unknown','Подтверждённые настройки не обнаружены':'No confirmed settings found',
           'Диагностика и компоненты':'Diagnostics and components','Подробности обнаружения доступны только для чтения.':'Discovery details are read-only.',
           'устройств':'devices','Данные о backend пока не получены':'Backend information is not available yet','Обновить диагностику':'Refresh diagnostics',
           'Не удалось обновить список устройств':'Could not refresh the device list',
           'Внешнее устройство':'External device','Тип не определён':'Type unknown','Встроенная мышь':'Built-in mouse','Встроенная клавиатура':'Built-in keyboard','Встроенная сенсорная панель':'Built-in touchpad',
           'Подключение не определено':'Connection unknown','Беспроводное 2,4 ГГц':'2.4 GHz wireless','Подключение не подтверждено':'Connection unconfirmed','Отключено':'Disconnected'})

EN.update({'Последнее чтение не удалось':'Last read failed','Производитель':'Manufacturer'})

EN.update({'Дополнительно':'More','Обнаруженное оборудование':'Detected devices','Разверни устройство, чтобы просмотреть возможности и действия.':'Expand a device to view its capabilities and actions.'})

EN.update({'Мыши':'Mice'})

EN.update({
'Выполняется операция':'Working…','Подключено':'Connected','Подключение не подтверждено':'Connection not confirmed',
'Мышь':'Mouse','Клавиатура':'Keyboard','Аудиоустройство':'Audio device','Устройство ввода':'Input device','Интерфейс устройства':'Device interface','Устройство':'Device',
'Недоступно для этой модели':'Not available for this model','Совместимость ещё не проверена':'Compatibility not checked yet','Настройка доступна':'Setting available','Доступен просмотр':'View only','Возможность обнаружена':'Capability detected',
'Настройки пока не обнаружены':'No settings detected yet','Для этой модели не найден совместимый инструмент управления.':'No compatible configuration tool was found for this model.',
'Расширенная диагностика':'Advanced diagnostics','Источники данных, backend и ограничения':'Data sources, backends and limitations','Диагностика':'Diagnostics','Проверь компоненты, если нужная настройка отсутствует.':'Check components if a setting you need is missing.',
'Компоненты и доступ':'Components and access','Проверить настройки устройства':'Check device settings','Запросить текущее состояние у приложения Logitech.':'Read the current state from the Logitech service.',
'Локальная настройка сохранена':'Local setting saved','Эта настройка не поддерживается':'This setting is not supported','Нет доступа к устройству':'Device access denied','Изменение применено':'Change applied',
'Изменение отправлено, но устройство его не подтвердило':'Change sent, but the device did not confirm it','Устройство вернуло другое значение':'The device returned a different value',
'Не удалось применить изменение':'Could not apply change','Устройство отключено':'Device disconnected','Операция отменена':'Operation cancelled',
'Изменение подтверждено аудиосистемой':'Change confirmed by the audio system','Подтверждение устройства недоступно':'Device confirmation is unavailable',
'Отменить изменение':'Discard change','Применить изменение':'Apply change',
'Управление аудио':'Audio controls','Сохранить или восстановить доступные параметры':'Save or restore available settings','Устройства вывода':'Output devices','Устройства ввода':'Input devices',
'Устройство вывода':'Output device','Устройство ввода':'Input device','Громкость':'Volume','Действия':'Actions','Включить микрофон':'Unmute microphone','Включить звук':'Unmute output','Выключить звук':'Mute',
'Пресеты и эффекты':'Presets and effects','Пресеты сообщества':'Community presets','Открыть набор готовых пресетов EasyEffects.':'Browse EasyEffects community presets.',
'Импорт пресета':'Import a preset','Выбери скачанный JSON-файл EasyEffects.':'Choose a downloaded EasyEffects JSON file.',
'Пока нет пользовательских пресетов':'No custom presets yet','Импортируй пресет EasyEffects, чтобы он появился здесь.':'Import an EasyEffects preset to see it here.','Последние проблемы обнаружения':'Recent discovery issues',
'Редактировать цепочку обработки':'Edit the effects chain','Открыть EasyEffects':'Open EasyEffects','Обработка звука':'Sound processing',
'Этот переключатель действует на микрофон и наушники.':'This switch affects both microphone and headphones.','Включить':'Enable','Обойти эффекты':'Bypass effects',
'Управление профилем':'Profile settings','Настройки профиля':'Profile settings',
'Аудиоустройства не найдены':'No audio devices found','Подключи микрофон или устройство вывода; звук системы появится автоматически.':'Connect a microphone or output device; system audio will appear automatically.',
'Остановить тест':'Stop test','Удалить временную запись':'Delete temporary recording','Как работает тест':'About the test',
'Запись временная и удаляется при обновлении, отключении устройства или закрытии приложения. Обработанный образец появится только при подтверждённом маршруте EasyEffects от выбранного микрофона.':'Recordings are temporary and removed on refresh, device disconnect or app close. A processed sample is available only when an EasyEffects route from the selected microphone is confirmed.',
'Тест остановлен.':'Test stopped.','Тест микрофона завершился с ошибкой. Проверь диагностику.':'The microphone test failed. Check diagnostics.'
})

EN.update({
    'Bluetooth-аудио':'Bluetooth audio',
    'Источники и изображение':'Sources and artwork',
    'Модуль управления':'Device backend',
    'Файл изображения':'Artwork file',
    'Системное изображение':'System artwork',
    'Точная модель':'Exact model',
    'Настройки будут перенесены на следующем этапе. Сейчас эта страница показывает данные и возможности, прочитанные из устройства.':'Controls will move in a later stage. This page currently shows the data and capabilities reported by the device.',
    'Подтверждённые настройки не обнаружены':'No confirmed settings found',
    'Этому устройству пока не найден совместимый модуль управления.':'A compatible control backend has not been found for this device yet.',
})

EN.update({
    'Заряжается':'Charging',
    'Выбери изображение устройства':'Choose device artwork',
    'Имя устройства':'Device name',
    'Локальное имя для этого устройства':'Local name for this device',
    'НЕТ ДАННЫХ':'NO DATA',
    'ПРОЧИТАНО':'READ',
    'НЕДОСТУПНО':'UNAVAILABLE',
    'Источники оборудования':'Device sources',
    'Подключи оборудование или проверь установленные компоненты.':'Connect a device or check the installed components.',
    'ОБНОВИТЬ ДИАГНОСТИКУ':'REFRESH DIAGNOSTICS',
})

EN.update({
    'Bluetooth-аудиоустройство':'Bluetooth audio device',
    'USB-аудио':'USB audio', 'USB-аудиоустройство':'USB audio device',
    'Беспроводное':'WIRELESS', 'Беспроводное подключение':'Wireless',
    'Беспроводное через USB-приёмник':'Wireless via USB receiver',
    'Встроенное аудиоустройство':'Built-in audio device',
    'Динамики':'Speakers', 'Наушники':'Headphones',
    'Неизвестная клавиатура':'Unknown keyboard', 'Неизвестная мышь':'Unknown mouse',
    'Неизвестное аудиоустройство':'Unknown audio device', 'Симуляция':'Simulation',
})

EN.update({'%1 внешних · %2 встроенных · %3 аудио':'%1 external · %2 built-in · %3 audio', '%1 других':'%1 other','обновлено %1':'updated %1'})

def set_language(language):
    global LANGUAGE
    LANGUAGE=language if language in ['ru','en'] else 'en'

EN.update({'Выбери клавишу на схеме': 'Select a key on the diagram', 'Выбрать цвет': 'Choose color', 'Зарядка': 'Charging', 'Значение вне допустимого диапазона': 'Value outside the supported range', 'Изменение': 'Write', 'Кнопки и макросы': 'Buttons and macros', 'Конфликт черновика': 'Draft conflict', 'Копия сохранена': 'Backup saved', 'Кэш приложения': 'Application cache', 'Макрос': 'Macro', 'Макрос содержит незавершённые нажатия клавиш.': 'The macro contains unfinished key presses.', 'Не сохранено': 'Unsaved', 'Не удалось восстановить стандартное изображение': 'Could not restore the default image', 'Не удалось использовать это изображение': 'Could not use this image', 'Не удалось сохранить имя устройства': 'Could not save the device name', 'Некоторые изменения применены. Проверь результат.': 'Some changes were applied. Review the result.', 'Отчёт сохранён': 'Report saved', 'Переназначение и подсветка отдельных клавиш не обнаружены.': 'Per-key assignments and lighting were not detected.', 'Пресеты изменяют программную обработку звука.': 'Presets change software audio processing.', 'Применить макрос': 'Apply macro', 'Применить назначение': 'Apply assignment', 'Проверить компоненты': 'Check components', 'Прочитано с устройства': 'Read from device', 'Сначала примени смену профиля, ступени или режима отдельно.': 'Apply the profile, stage or mode change separately first.', 'Удалить': 'Delete', 'Устройство сейчас недоступно': 'Device currently unavailable', 'Цвет': 'Color', 'Черновик конфликтует с текущим значением. Отмени его и проверь настройку.': 'The draft conflicts with the current value. Discard it and review the setting.', 'Чтение': 'Read', 'Эквалайзер и эффекты': 'Equalizer and effects', 'Волна': 'Wave', 'Один цвет': 'Single color', 'Случайные цвета': 'Random colors', 'Выбери гарнитуру на главной странице.': 'Select a headset on the dashboard.'})
EN['Профиль устройства изменился. Обновляю настройки; черновик сохранён.']='The device profile changed. Refreshing settings; your draft is preserved.'
EN.update({'Аппаратный режим · физическое подтверждение требуется':'Firmware mode · physical confirmation needed',
           'Период эффекта, мс':'Effect period, ms','Яркость эффекта':'Effect brightness',
           'Меньший период — быстрее':'Shorter period means faster animation',
           'Уровень, сообщаемый ratbagd':'Level reported by ratbagd',
           'Нулевая длительность: выбери скорость для анимации.':'Zero duration: choose a speed to animate.'})
EN.update({'Медленно':'Slow','Обычно':'Normal','Быстро':'Fast',
           'Для нового режима предложено значение; оно ещё не применено.':'A value is suggested for the new mode; it has not been applied.'})
EN['Дополнительный слот ratbagd · назначение не подтверждено']='Additional ratbagd slot · physical purpose unverified'

EN.update({'Дождись завершения текущей операции.':'Wait for the current operation to finish.'})

EN.update({'Запись временная и удаляется при смене микрофона, отключении устройства или закрытии приложения. Обработанный образец появится только при подтверждённом маршруте EasyEffects от выбранного микрофона.':'The temporary recording is deleted when changing the microphone, disconnecting the device or closing the app. A processed sample appears only when the EasyEffects route from the selected microphone is confirmed.'})

EN.update({'Пауза':'Wait','Нажать':'Press','Отпустить':'Release','Нажать и отпустить':'Tap'})

EN.update({'Операция прервана. Проверь состояние устройства перед повторным применением.':'Operation interrupted. Check the device state before applying again.'})

EN.update({'Отправлено · кэш backend совпал. Подтверждение устройства недоступно.': 'Sent · backend cache matches. Device verification is unavailable.', 'Отправлено · прочитать результат не удалось.': 'Sent · could not read back the result.', 'Отправлено · проверка результата не поддерживается.': 'Sent · result verification is unsupported.', 'Отправлено · без аппаратного подтверждения': 'Sent · hardware verification unavailable', 'Проверено': 'Verified', 'Результат отличается': 'Readback differs', 'Проверь результат операции': 'Review the operation result', 'Загрузка пресетов…': 'Loading presets…', 'EasyEffects не установлен. Для применения пресетов нужен EasyEffects.': 'EasyEffects is not installed. It is required to apply presets.', 'Не удалось прочитать пресеты. Проверь доступ к настройкам EasyEffects.': 'Could not read presets. Check access to EasyEffects settings.', 'Пресеты не установлены. Импортируй JSON или найди готовый пресет.': 'No presets installed. Import JSON or find a preset.', 'Аудиовыход': 'Audio output', 'Источник записи': 'Recording source', 'Маршрут': 'Route', 'Левая кнопка': 'Left click', 'Правая кнопка': 'Right click', 'Нажатие колеса': 'Wheel click', 'Назад': 'Back', 'Вперёд': 'Forward', 'Смена профиля': 'Cycle profile', 'Колесо вправо': 'Wheel right', 'Колесо влево': 'Wheel left', 'Кнопка': 'Button'})

EN.update({'Последнее значение: ':'Last observed: '})

EN.update({'Зона подсветки':'Lighting zone','Клавиша':'Key'})

EN.update({'Сохранено локально':'Saved locally'})

EN.update({
    'Индикаторы мыши':'Mouse indicators',
    'Док-станция':'Dock station',
    'Настройки прочитаны с устройства.':'Settings read from the device.',
    'Состояние зарядки':'Charging state',
    'Связь с мышью':'Mouse link',
    'Мышь подключена':'Mouse connected',
    'Мышь не подключена':'Mouse disconnected',
    'Заряжается':'Charging',
    'Не заряжается':'Not charging',
    'Активный профиль':'Active profile',
    'Последний прочитанный профиль':'Last read profile',
    'Профиль':'Profile',
    'Верхний LED зарядки':'Top charging LED',
    'Нижний LED DPI':'Bottom DPI LED',
    'Состояние не сообщается':'State not reported',
    'Нижний LED показывает ступень DPI после нажатия кнопки DPI. Верхний LED: красный при зарядке, зелёный после полного заряда. Яркость LED устройством не сообщается.':
        'The bottom LED shows the DPI stage after pressing the DPI button. The top LED is red while charging and green when fully charged. The device does not report LED brightness.',
    'Подключение док-станции':'Dock connection',
    'Не определяется отдельно':'Not detected separately',
    'Приёмник обнаружен. Его RGB-команда может управлять подсветкой дока, но физическая цель пока не подтверждена.':
        'The receiver is detected. Its RGB command may control dock lighting, but the physical target remains unverified.',
    'Запись флагов сенсора для K7 Ultra не проверена; настройка доступна только для чтения.':
        'K7 Ultra sensor-flag writes are unverified; this setting is read-only.',
    'Управление LED K7 Ultra не подтверждено. Данные зарядки и DPI не показывают фактическое свечение индикаторов.':
        'K7 Ultra LED control is unverified. Charging and DPI data do not show whether the indicators are actually lit.',
    'Приёмник обнаружен вместе с мышью. Отдельное состояние док-станции и назначение RGB-команды пока не подтверждены.':
        'The receiver is detected with the mouse. A separate dock state and the target of the RGB command are unverified.',
    'Рабочий индикатор уровня заряда док-станции не изменяется приложением.':
        'The existing dock battery-level indicator is not changed by the app.',
})

EN.update({'Выбери цвет для этой зоны перед включением подсветки.':'Choose a color for this zone before turning on lighting.'})

EN.update({
    'Бирюзовый':'Cyan',
    'Подсветка дока изменилась. Прочитай настройки заново; черновик сохранён.':
        'Dock lighting changed. Read settings again; your draft is preserved.',
    'Уровень заряда':'Battery level', 'Вспышки':'Flash away', 'Звёзды':'Stars', 'Волны':'Waves',
    'Длительность':'Duration', 'Короткая':'Short', 'Средняя':'Medium', 'Долгая':'Long',
    'Направление':'Direction', 'По часовой стрелке':'Clockwise', 'Против часовой стрелки':'Counterclockwise',
    'Подсветка дока не прочитана':'Dock lighting has not been read',
    'Разбуди K7 Ultra и нажми «Прочитать настройки».':'Wake K7 Ultra and choose “Read settings”.',
    'Предпросмотр':'Preview', 'Эффекты подсветки':'Lighting effects',
    'Яркость док-станции':'Dock brightness', 'Аппаратный эффект':'Hardware effect',
    'Цвет выбирает док-станция по заряду мыши. Пороги не изменяются.':
        'The dock chooses its color from the mouse battery level. Thresholds are unchanged.',
    'Эффект выполняет док-станция. Свечение и анимация программой не считываются.':
        'The dock runs the effect. Visible lighting and animation cannot be read by the app.',
    'Изменения отправляются только кнопкой «Применить». Музыкальный режим недоступен.':
        'Changes are sent only with Apply. Music mode is unavailable.',
    'Автообновление настроек: ':'Settings auto-refresh: ',
    'Старый черновик без профиля или ступени: %1. Проверь значение и выбери его заново.':
        'Old draft without a profile or stage: %1. Review the value and select it again.',
    'Профиль или ступень DPI изменились. Прочитай настройки заново; черновик сохранён.':
        'The profile or DPI stage changed. Read settings again; your draft is preserved.',
    'Последняя прочитанная ступень DPI':'Last read DPI stage',
    'Цвет ступени DPI указан по руководству; состояние LED не считывается. Верхний LED: красный при зарядке, зелёный после полного заряда.':
        'DPI stage colors follow the manual; LED state is not read. The top LED is red while charging and green when fully charged.',
})

EN.update({
    'Активная':'Active','Активная ступень DPI':'Active DPI stage','Выбрать':'Select',
    'Количество ступеней':'Number of stages','Раздельно X / Y':'Separate X / Y',
    'Цвета ступеней — по руководству K7. Изменения DPI отправляются вместе после «Применить».':
        'Stage colors follow the K7 manual. DPI changes are sent together only after Apply.',
    'Назначение кнопки':'Button assignment','Поиск действия':'Search actions',
    'Мышь / DPI':'Mouse / DPI','Сочетания':'Shortcuts','Мультимедиа':'Media',
    'Исходное назначение':'Original assignment','Прокрутить вверх':'Scroll up','Прокрутить вниз':'Scroll down',
    'Громче':'Volume up','Тише':'Volume down','Воспроизведение / пауза':'Play / pause',
    'Предыдущий трек':'Previous track','Следующий трек':'Next track','Сохранить':'Save',
    'Профиль 1':'Profile 1','Профиль 2':'Profile 2','Профиль 3':'Profile 3',
    'Сначала выбери кнопку на схеме, затем действие. Запись — только после «Применить». Хотя бы одна кнопка должна сохранять левый щелчок.':
        'Select a button on the diagram, then an action. Only Apply writes to the mouse. Keep at least one left-click button.',
    'Редактор сложных макросов K7 пока недоступен: формат записи не проверен. Существующие макросы не изменяются.':
        'The K7 complex macro editor is unavailable: its write format is unverified. Existing macros are preserved.',
    'Режим сенсора':'Sensor mode','Производительный':'Performance','Игровой':'Gaming','Экстремальный':'Extreme',
    'Высота отрыва, мм':'Lift-off distance, mm','Угол сенсора, °':'Sensor angle, °',
    'Таймер сна, мин (0 — никогда)':'Sleep timer, min (0 = never)',
    'Параметры прочитаны с K7. Черновик не меняет мышь; результат записи проверяется чтением. Новые команды требуют физической проверки.':
        'Settings were read from K7. Drafts do not change the mouse; writes are checked by readback. New commands need physical verification.',
    'Режим сенсора и фильтры могут влиять на отклик и расход батареи. Неподдерживаемые значения не отправляются; другие настройки сохраняются.':
        'Sensor mode and filters may affect response and battery use. Unsupported values are rejected; other settings are preserved.',
    'Сохрани хотя бы одну кнопку с левым щелчком.':'Keep at least one button assigned to left click.',
    'Конфигурация K7 изменилась. Прочитай настройки заново; черновик сохранён.':
        'The K7 configuration changed. Read settings again; your draft is preserved.',
    'Уровень DPI':'DPI stage',
    'Макрос на устройстве':'On-device macro','Назначение не распознано':'Unrecognized assignment',
    'Назначить сочетание':'Assign shortcut',
    'Старые черновики сохранены. Проверь профиль и ступень, затем введи нужные значения в новый редактор.':
        'Older drafts are preserved. Review their profile and stage, then enter the desired values in the new editor.',
    'Удалить старый черновик':'Delete old draft',
    'Получено неизвестное или неподдерживаемое значение; запись недоступна.':
        'An unknown or unsupported value was read; writing is unavailable.',
})

# G515 editor (native effects and local per-key drafts).
EN.update({'Анимации': 'Animations',
 'Настройки клавиатуры': 'Keyboard settings',
 'Интенсивность эффекта, %': 'Effect intensity, %',
 'Схема ANSI. Цвета — локальная конфигурация Solaar, не показания светодиодов.': 'ANSI diagram. Colors show local '
                                                                                 'Solaar configuration, not LED '
                                                                                 'readback.',
 'Быстрый выбор клавиш': 'Quick key selection',
 'Цифры': 'Numbers',
 'Модификаторы': 'Modifiers',
 'Стрелки': 'Arrows',
 'Все клавиши': 'All keys',
 'Выбрано клавиш: ': 'Selected keys: ',
 'Множественный выбор': 'Multi-selection',
 'Применить включает управление RGB и статичный эффект, затем отправляет цвета выбранных клавиш. Изменения остальных клавиш сохраняются. Аппаратное считывание цветов недоступно.': 'Apply '
                                                                                                                                                                                    'enables '
                                                                                                                                                                                    'RGB '
                                                                                                                                                                                    'control '
                                                                                                                                                                                    'and '
                                                                                                                                                                                    'a '
                                                                                                                                                                                    'static '
                                                                                                                                                                                    'effect, '
                                                                                                                                                                                    'then '
                                                                                                                                                                                    'sends '
                                                                                                                                                                                    'the '
                                                                                                                                                                                    'key '
                                                                                                                                                                                    'color '
                                                                                                                                                                                    'drafts. '
                                                                                                                                                                                    'Other '
                                                                                                                                                                                    'saved '
                                                                                                                                                                                    'key '
                                                                                                                                                                                    'colors '
                                                                                                                                                                                    'are '
                                                                                                                                                                                    'preserved. '
                                                                                                                                                                                    'Hardware '
                                                                                                                                                                                    'color '
                                                                                                                                                                                    'readback '
                                                                                                                                                                                    'is '
                                                                                                                                                                                    'unavailable.',
 'Нет сохранённой карты LED. Сначала настрой поклавишную подсветку в Solaar; неизвестные зоны не записываются.': 'No '
                                                                                                                 'saved '
                                                                                                                 'LED '
                                                                                                                 'map. '
                                                                                                                 'Configure '
                                                                                                                 'per-key '
                                                                                                                 'lighting '
                                                                                                                 'in '
                                                                                                                 'Solaar '
                                                                                                                 'first; '
                                                                                                                 'unknown '
                                                                                                                 'zones '
                                                                                                                 'are '
                                                                                                                 'never '
                                                                                                                 'written.',
 'Статичный цвет, дыхание, цикл цветов и выключение передаются штатному эффекту Solaar. Меньший период — быстрее. Доступность проверяется backend при применении; автономность G515 после выхода не подтверждена.': 'Static, '
                                                                                                                                                                                                                    'breathing, '
                                                                                                                                                                                                                    'color '
                                                                                                                                                                                                                    'cycle '
                                                                                                                                                                                                                    'and '
                                                                                                                                                                                                                    'off '
                                                                                                                                                                                                                    'use '
                                                                                                                                                                                                                    'native '
                                                                                                                                                                                                                    'Solaar '
                                                                                                                                                                                                                    'effects. '
                                                                                                                                                                                                                    'A '
                                                                                                                                                                                                                    'shorter '
                                                                                                                                                                                                                    'period '
                                                                                                                                                                                                                    'is '
                                                                                                                                                                                                                    'faster. '
                                                                                                                                                                                                                    'The '
                                                                                                                                                                                                                    'backend '
                                                                                                                                                                                                                    'validates '
                                                                                                                                                                                                                    'availability '
                                                                                                                                                                                                                    'on '
                                                                                                                                                                                                                    'Apply; '
                                                                                                                                                                                                                    'G515 '
                                                                                                                                                                                                                    'behavior '
                                                                                                                                                                                                                    'after '
                                                                                                                                                                                                                    'exit '
                                                                                                                                                                                                                    'is '
                                                                                                                                                                                                                    'unverified.',
 'Анимации G HUB': 'G HUB animations',
 'Память и питание': 'Memory and power',
 'Contrast · Lightning · Ocean Wave · Red White Blue · Verticool. Это каталог из референса G HUB; воспроизведение, редактор кадров, экранные и аудиоэффекты пока не реализованы. Штатные эффекты находятся в разделе подсветки.': 'Contrast '
                                                                                                                                                                                                                                  '· '
                                                                                                                                                                                                                                  'Lightning '
                                                                                                                                                                                                                                  '· '
                                                                                                                                                                                                                                  'Ocean '
                                                                                                                                                                                                                                  'Wave '
                                                                                                                                                                                                                                  '· '
                                                                                                                                                                                                                                  'Red '
                                                                                                                                                                                                                                  'White '
                                                                                                                                                                                                                                  'Blue '
                                                                                                                                                                                                                                  '· '
                                                                                                                                                                                                                                  'Verticool. '
                                                                                                                                                                                                                                  'This '
                                                                                                                                                                                                                                  'is '
                                                                                                                                                                                                                                  'the '
                                                                                                                                                                                                                                  'G '
                                                                                                                                                                                                                                  'HUB '
                                                                                                                                                                                                                                  'reference '
                                                                                                                                                                                                                                  'catalog; '
                                                                                                                                                                                                                                  'playback, '
                                                                                                                                                                                                                                  'a '
                                                                                                                                                                                                                                  'frame '
                                                                                                                                                                                                                                  'editor, '
                                                                                                                                                                                                                                  'screen '
                                                                                                                                                                                                                                  'and '
                                                                                                                                                                                                                                  'audio '
                                                                                                                                                                                                                                  'effects '
                                                                                                                                                                                                                                  'are '
                                                                                                                                                                                                                                  'not '
                                                                                                                                                                                                                                  'implemented. '
                                                                                                                                                                                                                                  'Native '
                                                                                                                                                                                                                                  'effects '
                                                                                                                                                                                                                                  'are '
                                                                                                                                                                                                                                  'in '
                                                                                                                                                                                                                                  'Lighting.',
 'Backend G515 пока не предоставляет проверенного переназначения BASE/FN/G-SHIFT, действий при нажатии/удержании/отпускании и аппаратных макросов. LED-зоны не являются кодами назначения клавиш. Изменение этих функций недоступно.': 'The '
                                                                                                                                                                                                                                       'G515 '
                                                                                                                                                                                                                                       'backend '
                                                                                                                                                                                                                                       'has '
                                                                                                                                                                                                                                       'no '
                                                                                                                                                                                                                                       'verified '
                                                                                                                                                                                                                                       'BASE/FN/G-SHIFT '
                                                                                                                                                                                                                                       'remapping, '
                                                                                                                                                                                                                                       'press/hold/release '
                                                                                                                                                                                                                                       'actions '
                                                                                                                                                                                                                                       'or '
                                                                                                                                                                                                                                       'hardware '
                                                                                                                                                                                                                                       'macros. '
                                                                                                                                                                                                                                       'LED '
                                                                                                                                                                                                                                       'zones '
                                                                                                                                                                                                                                       'are '
                                                                                                                                                                                                                                       'not '
                                                                                                                                                                                                                                       'remapping '
                                                                                                                                                                                                                                       'codes. '
                                                                                                                                                                                                                                       'These '
                                                                                                                                                                                                                                       'features '
                                                                                                                                                                                                                                       'cannot '
                                                                                                                                                                                                                                       'be '
                                                                                                                                                                                                                                       'edited.',
 'Эти таймеры относятся к подсветке, а не к переходу всей клавиатуры в сон. Автономность, слоты встроенной памяти, стартовые эффекты и сброс не подтверждены backend; они не изменяются. Настройки Solaar локальные, батарея показывается в заголовке по доступным данным устройства.': 'The '
                                                                                                                                                                                                                                                                                         'timers '
                                                                                                                                                                                                                                                                                         'control '
                                                                                                                                                                                                                                                                                         'lighting, '
                                                                                                                                                                                                                                                                                         'not '
                                                                                                                                                                                                                                                                                         'keyboard '
                                                                                                                                                                                                                                                                                         'sleep. '
                                                                                                                                                                                                                                                                                         'Battery '
                                                                                                                                                                                                                                                                                         'life '
                                                                                                                                                                                                                                                                                         'estimates, '
                                                                                                                                                                                                                                                                                         'onboard '
                                                                                                                                                                                                                                                                                         'memory '
                                                                                                                                                                                                                                                                                         'slots, '
                                                                                                                                                                                                                                                                                         'startup '
                                                                                                                                                                                                                                                                                         'effects '
                                                                                                                                                                                                                                                                                         'and '
                                                                                                                                                                                                                                                                                         'reset '
                                                                                                                                                                                                                                                                                         'are '
                                                                                                                                                                                                                                                                                         'not '
                                                                                                                                                                                                                                                                                         'verified '
                                                                                                                                                                                                                                                                                         'by '
                                                                                                                                                                                                                                                                                         'the '
                                                                                                                                                                                                                                                                                         'backend '
                                                                                                                                                                                                                                                                                         'and '
                                                                                                                                                                                                                                                                                         'remain '
                                                                                                                                                                                                                                                                                         'unchanged. '
                                                                                                                                                                                                                                                                                         'Solaar '
                                                                                                                                                                                                                                                                                         'settings '
                                                                                                                                                                                                                                                                                         'are '
                                                                                                                                                                                                                                                                                         'local; '
                                                                                                                                                                                                                                                                                         'available '
                                                                                                                                                                                                                                                                                         'battery '
                                                                                                                                                                                                                                                                                         'data '
                                                                                                                                                                                                                                                                                         'is '
                                                                                                                                                                                                                                                                                         'shown '
                                                                                                                                                                                                                                                                                         'in '
                                                                                                                                                                                                                                                                                         'the '
                                                                                                                                                                                                                                                                                         'header.'})

EN.update({'Начальное значение эффекта; аппаратное считывание недоступно.':'Initial effect value; hardware readback is unavailable.',
'Настройки Solaar недоступны. Проверь подключение G515 и сохранённую конфигурацию Solaar.':'Solaar settings unavailable. Check the G515 connection and saved Solaar configuration.'})

EN.update({'Часть настроек Solaar недоступна; показаны доступные данные.':'Some Solaar settings are unavailable; available data is shown.',
'Настройки получены через Solaar. Цвета и таймеры могут быть кэшированными.':'Settings received through Solaar. Colors and timers may be cached.'})

# EWEADN S9 and application scale.
EN.update({
    'Мышь не ответила на запрос состояния. Разбуди её движением, проверь подключение и нажми «Прочитать настройки».': 'The mouse did not answer the status request. Wake it by moving it, check the connection and choose Read settings.',
    'Сбросить': 'Reset',
    'Высокая скорость': 'High speed',
    'Высота отрыва': 'Lift-off distance',
    'Для этой кнопки устройство не сообщило доступный слот переназначения.': 'The device did not report a writable remapping slot for this button.',
    'До повторного нажатия': 'Until pressed again',
    'Запись и редактирование': 'Record and edit',
    'Запись клавиш, щелчков и пауз сохраняется локально. Загрузка в S9 требует форматирования аппаратной области макросов через OTA; безопасное чтение и восстановление этой области пока не подтверждены.': 'Keys, clicks and delays are recorded locally. Uploading to the S9 formats its hardware macro bank through OTA; safe reading and restoration of that bank are not verified.',
    'Количество ступеней DPI': 'Number of DPI stages',
    'Максимальная производительность': 'Maximum performance',
    'Масштаб интерфейса': 'Interface scale',
    'Масштаб изменится после перезапуска Logi Center.': 'The scale will change after restarting Logi Center.',
    'Масштаб приложения дополняет масштаб системы; GTK не изменяется.': 'Application scale is combined with system scaling; GTK is unchanged.',
    'Мышь вернётся к заводским настройкам: DPI, кнопки и другие сохранённые параметры могут быть потеряны. Создаётся частный снимок читаемых параметров; аппаратная библиотека макросов в него не входит. Полный откат не гарантируется. Продолжить?': 'The mouse will return to factory settings: DPI, button assignments and other stored parameters may be lost. A private snapshot of readable parameters is saved; it does not include the hardware macro library. Full rollback is not guaranteed. Continue?',
    'Назначение сохраняется в черновик. Сохрани хотя бы одну кнопку с левым щелчком.': 'Assignments are staged as drafts. Keep at least one left-click button.',
    'Назначить': 'Assign',
    'Настройки устройства недоступны': 'Device settings unavailable',
    'Обычный': 'Normal',
    'Один раз': 'Once',
    'Параметры сенсора': 'Sensor parameters',
    'Пока кнопка удерживается': 'While the button is held',
    'Проверь подключение по USB или приёмнику, закрой веб-конфигуратор и пошевели мышью для пробуждения.': 'Check the USB or receiver connection, close the web configurator and move the mouse to wake it.',
    'Профиль (значение устройства)': 'Profile (native value)',
    'Прошивка приёмника не считана. Сброс всех настроек и обновление прошивки автоматически не выполняются.': 'Receiver firmware has not been read. Settings reset and firmware updates are never performed automatically.',
    'Режим работы сенсора': 'Sensor operating mode',
    'Режим сохранён в локальной библиотеке; аппаратная передача макросов S9 пока недоступна.': 'The mode is stored in the local library; hardware macro upload to the S9 is currently unavailable.',
    'Сброс всех настроек': 'Reset all settings',
    'Сон через, мин': 'Sleep after, min',
    'В проводном режиме режим сенсора задаётся прошивкой. Оценка оставшегося времени работы не вычисляется без достоверных данных устройства.': 'Sensor mode is firmware-controlled over USB. Remaining battery runtime is not estimated without reliable device data.',
    'Сон через, с': 'Sleep after, s',
    'Действие устройства': 'Device action',
    'Черновик: ': 'Draft: ',
    'Изображение карточки': 'Card artwork',
    'Расширенные настройки S9 доступны в QML-интерфейсе: python app.py --ui qml': 'Advanced S9 settings are available in the QML interface: python app.py --ui qml',
})

def tr(text):
    if LANGUAGE=='ru':return text
    if text in EN:return EN[text]
    # Battery suffixes arrive as a formatted percentage string.
    for source in [' · заряжается',' · заряжено']:
        text=text.replace(source,EN[source])
    return text

def canonical_text(text):
    if text in EN:return EN[text]
    for source in ['Профиль ','Уровень ','Клавиша F']:
        if text.startswith(source):return EN.get(source,source)+text[len(source):]
    return text

EN.update({'Рябь':'Ripple','Насыщенность':'Saturation','Период эффекта':'Effect period'})
