# Факты о дистрибутиве (§11 AGENTS.md)

Выяснено по исходникам STE Slicer и Uranium и подтверждено прогонами в STE Slicer 7.10 на шестерне (3D) и колесе (5D).

- Ключ режима печати: `printing_mode`, значения `classic` (3D), `cylindrical` (5D Spiral), `cylindrical_full` (5D);
  также существуют `discrete`, `spherical*`, `conical*` (не используются). Определение: `resources/definitions/fdmprinter.def.json`.
- Выбор бэкенда по режиму: `steslicer/BackendManager`, слежение за изменением `printing_mode`; для 5D бэкенд `CylindricalBackend`.
- Definition id Stereotech Hybrid 530 V5.2.4: `hte530v5.2.4` (наследует `steprinter530_v5.2.4`).
- Высота рабочего объёма: 300 мм в `classic`, 231.1 мм в остальных режимах.
- Для `cylindrical_full` по умолчанию `adhesion_type = raft`; размер центрального цилиндра задаёт `cylindrical_mode_base_diameter`.
- Профили качества (`quality_type`): `high` 0.06, `normal` 0.1, `fast` 0.15, `draft` 0.2, `verydraft` 0.3, `coarse` 0.4.
  Получение списка: `app.getQualityManager().getQualityGroups(global_stack)`; выбор: `MachineManager.setQualityGroup(group, no_dialog=True)`.
- Материалы: `app.getMaterialManager().getAvailableMaterialsForMachineExtruder(global_stack, extruder_stack)` -> `{root_material_id: node}`;
  выбор: `MachineManager.setMaterialById(position, root_material_id)`. Состав: generic (PLA, PETG, ABS, PC, Nylon, PP, TPU, CPE, CPE+, HIPS, PVA, Tough PLA),
  enduse_*, fiberpart_*, sealant_*, contifiber, metalcast, proto.
- Диалог «сохранить/сбросить изменения профиля» при смене материала/профиля в плагине не возникает: сравнение `active_mode == 1` в коде слайсера никогда не истинно,
  для профиля используется `no_dialog=True`.
- Слайсинг: `app.getBackend().forceSlice()`; состояния и прогресс - сигналы `backendStateChange` (`BackendState`: 1 NotStarted, 2 Processing, 3 Done, 4 Error) и `processingProgress`.
  В 5D составные бэкенды излучают промежуточные состояния, поэтому учитываются только события активного бэкенда.
- Время и материал: `app.getPrintInformation()` (`currentPrintTime`, `materialWeights`, `materialLengths`, `materialNames`).
- G-code: `app.getMeshFileHandler().getWriter("GCodeWriter").write(StringIO, None)`; данные берутся из `scene.gcode_dict`.
- Проект 3MF: `app.getWorkspaceFileHandler().getWriter("3MFWriter").write(BytesIO, [root])` (пишет модели, стеки машины и экструдеров, предпочтения).
- Потоки записи: `GCodeWriter._createSnapshot` и `ThreeMFWorkspaceWriter.write` обёрнуты в `call_on_qt_thread` (ставят вызов в очередь главного потока и ждут). Вызывать их из главного потока нельзя - взаимная блокировка, слайсер зависает. Экспорт выполняется из рабочего потока, как в `WriteFileJob`.
- G-code в 5D (`cylindrical_full`): два блока заголовка (классическая часть и основная), оси `A` и `C`, слои с отрицательными номерами и метка `SUPPORT` для базовой подложки (raft); суммарное время и расход равны сумме блоков.
- На новых процессорах встроенная MKL может завершать слайсер с ошибкой `CPU ... is not supported`; помогает переменная окружения `MKL_DEBUG_CPU_TYPE=5`. К плагину это не относится.
- Ограничения QML слайсера (Qt 5.10, набор разрешённых импортов) описаны в `docs/native_ui.md`.
- Загрузка модели: `app.readLocalFile(QUrl, skip_project_file_check)`; узел появляется асинхронно после `ReadMeshJob`.
- Система координат сцены: Y вертикальна, Z к зрителю; в инструментах плагина используются координаты стола (x вправо, y назад, z вверх).
- Settings: пользовательские изменения пишутся в `userChanges` глобального стека либо стека экструдера (если `settable_per_extruder`).
- Python встроенный в дистрибутив: 3.5 (`python35.dll`), Qt 5.10, OpenSSL 1.0 (`libeay32.dll`, `ssleay32.dll`). Код проверяется скриптом `scripts/check_py35.py`.
- Папка плагинов пользователя: `%APPDATA%\steslicer\7.10\plugins`. Встроенные плагины лежат в папке `plugins` рядом с `STESlicer.exe`.
- Язык слайсера хранится в настройке `general/language` (например `ru_RU`); плагин берёт его по умолчанию.
- Универсальные материалы на Hybrid 530 V5.2.4 доступны только с суффиксом `_175` (`generic_pc_175`, `generic_petg_175`, `generic_tpu_175`);
  `enduse_*` без суффикса. `generic_cpe_plus`, `generic_tough_pla` и `generic_pp` недоступны, PP есть только как `enduse_pp`.
- Сертификат `api.timeweb.ai` выдан цепочкой с корнем GlobalSign Root R46, которого нет в `certifi` слайсера (137 корней), поэтому корень лежит в `plugin/AIAssistant/certs`.
- `reset_settings` должен сбрасывать и кастомный профиль (`MachineManager.resetToUseDefaultQuality`), иначе настройки прошлой детали остаются активными.

## Гипотезы базы знаний (уточнить у экспертов)

- 5D выбирается для тел вращения с отношением длина/диаметр >= 0.35, средней стенкой >= 2.5 мм и требованиями точности/вращения/износа/нагрузки;
  валы (теги rotating + load_bearing + precision, длина/диаметр >= 0.5, боковая поверхность вдоль оси >= 50%) также идут в 5D. Критерии подобраны так, чтобы совпадать с пометками 3D/5D у семи тестовых деталей.
- Ось симметрии в 5D ставится вертикально, деталь по центру стола.
- Предпочтение Enduse-материалов для функциональных деталей.
- Теплостойкость материалов берётся из описаний самого слайсера: `generic_cpe` до 70 °C, `generic_abs` до 85 °C, `generic_cpe_plus` до 100 °C, `generic_pc` до 110 °C. На Hybrid 530 нет ASA и `generic_cpe_plus`; единственный УФ-стойкий материал в списке по описанию — `fiberpart_abspa_g8` (ABS/PA со стекловолокном), он требует решения экспертов.
- Если лучший по рейтингу тип недоступен на принтере, правила переходят к следующему типу и сообщают, какие типы пропущены; подмена более слабым материалом (CPE+ → CPE) не допускается.
- Эластичные детали: мягкий `sealant_tpu93` / `sealant_tpu` / `sealant_tpu_A95` вместо Enduse TPU D70 (Шор 70D), без поддержек. По пыльнику (ТЗ: «жёсткие материалы не допускаются») это следует из ТЗ, конкретную марку стоит подтвердить у экспертов.
- Режим `cylindrical` (5D Spiral) правила не выбирают: критерии его применения не уточнены, требуется решение экспертов.
