# Факты о дистрибутиве (§11 AGENTS.md)

Выяснено по исходникам STE Slicer и Uranium, запуск в реальном слайсере ещё не выполнялся.

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
- Загрузка модели: `app.readLocalFile(QUrl, skip_project_file_check)`; узел появляется асинхронно после `ReadMeshJob`.
- Система координат сцены: Y вертикальна, Z к зрителю; в инструментах плагина используются координаты стола (x вправо, y назад, z вверх).
- Settings: пользовательские изменения пишутся в `userChanges` глобального стека либо стека экструдера (если `settable_per_extruder`).
- Python встроенный в дистрибутив: `TODO` (проверять в самом слайсере; код проверяется скриптом `scripts/check_py35.py`).
- Папка плагинов пользователя: `%APPDATA%\steslicer\<версия>\plugins` (точная версия `TODO`).

## Гипотезы базы знаний (уточнить у экспертов)

- 5D выбирается для тел вращения с отношением длина/диаметр >= 0.35, средней стенкой >= 2.5 мм и требованиями точности/вращения/износа/нагрузки;
  валы (теги rotating + load_bearing + precision, длина/диаметр >= 0.5, боковая поверхность вдоль оси >= 50%) также идут в 5D. Критерии подобраны так, чтобы совпадать с пометками 3D/5D у семи тестовых деталей.
- Ось симметрии в 5D ставится вертикально, деталь по центру стола.
- Предпочтение Enduse-материалов для функциональных деталей.
