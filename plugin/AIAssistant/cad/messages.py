PART_NAMES = {
    "bolt": {"ru": "Болт", "en": "Bolt"},
    "nut": {"ru": "Гайка", "en": "Nut"},
    "washer": {"ru": "Шайба", "en": "Washer"},
    "plate": {"ru": "Пластина", "en": "Plate"},
    "bracket": {"ru": "Кронштейн", "en": "Angle bracket"},
}

PARAM_NAMES = {
    "thread_size": {"ru": "Резьба", "en": "Thread"},
    "length_mm": {"ru": "Длина, мм", "en": "Length, mm"},
    "head_type": {"ru": "Головка", "en": "Head"},
    "pitch_mm": {"ru": "Шаг, мм", "en": "Pitch, mm"},
    "thread_length_mm": {"ru": "Длина резьбы, мм", "en": "Thread length, mm"},
    "thread_mode": {"ru": "Режим резьбы", "en": "Thread mode"},
    "clearance_mm": {"ru": "Компенсация, мм", "en": "Clearance, mm"},
    "load_bearing": {"ru": "Силовая деталь", "en": "Load bearing"},
    "thickness_mm": {"ru": "Толщина, мм", "en": "Thickness, mm"},
    "width_mm": {"ru": "Ширина, мм", "en": "Width, mm"},
    "depth_mm": {"ru": "Глубина, мм", "en": "Depth, mm"},
    "height_mm": {"ru": "Высота, мм", "en": "Height, mm"},
    "holes": {"ru": "Отверстий", "en": "Holes"},
    "hole_clearance_mm": {"ru": "Компенсация отверстий, мм", "en": "Hole clearance, mm"},
    "hole_diameter_mm": {"ru": "Диаметр отверстий, мм", "en": "Hole diameter, mm"},
    "holes_per_leg": {"ru": "Отверстий на полке", "en": "Holes per leg"},
}

VALUE_NAMES = {
    "hex": {"ru": "шестигранная", "en": "hex"},
    "cylindrical": {"ru": "цилиндрическая", "en": "cylindrical"},
    "countersunk": {"ru": "потайная", "en": "countersunk"},
    "modeled": {"ru": "моделируется", "en": "modeled"},
    "cosmetic": {"ru": "условная (гладкий цилиндр)", "en": "cosmetic (smooth cylinder)"},
    True: {"ru": "да", "en": "yes"},
    False: {"ru": "нет", "en": "no"},
}

WARNING_TEXTS = {
    "printer_calibration": {
        "ru": "Посадка не гарантируется без калибровки принтера: проверьте пробную печать и подберите компенсацию.",
        "en": "Fit is not guaranteed without printer calibration: check a test print and adjust the clearance."},
    "structural_fastener": {
        "ru": "Печатный пластиковый крепёж не заменяет сертифицированный металлический без инженерного "
              "расчёта и испытаний.",
        "en": "A printed plastic fastener does not replace a certified metal one without engineering "
              "calculation and testing."},
    "load_bearing_plastic": {
        "ru": "Резьба, напечатанная слоями, слабо работает на растяжение: не применяйте там, где отказ опасен.",
        "en": "A layered printed thread is weak in tension: do not use it where failure is dangerous."},
    "fine_thread": {
        "ru": "Мелкий шаг резьбы близок к пределу FDM-печати и может напечататься плохо.",
        "en": "A fine thread pitch is close to the limit of FDM printing and may print poorly."},
    "cosmetic_thread_replaced": {
        "ru": "Условная резьба заменена гладким цилиндром: деталь нельзя вкрутить.",
        "en": "The cosmetic thread is replaced by a smooth cylinder: the part cannot be screwed in."},
    "thin_wall": {
        "ru": "Самая тонкая стенка меньше трёх периметров сопла 0,4 мм: прочность и печать под вопросом.",
        "en": "The thinnest wall is thinner than three 0.4 mm perimeters: strength and printing are doubtful."},
    "bracket_layer_orientation": {
        "ru": "Слои идут параллельно изгибу, угол слабо работает на разрыв слоёв: проверьте ориентацию.",
        "en": "Layers run parallel to the bend, so the corner is weak against layer separation: check the "
              "orientation."},
}

ERROR_TEXTS = {
    "empty_mesh": {"ru": "Сетка пуста.", "en": "The mesh is empty."},
    "invalid_vertices": {"ru": "В сетке есть недопустимые координаты.", "en": "The mesh has invalid coordinates."},
    "degenerate_triangles": {"ru": "Есть вырожденные треугольники.", "en": "There are degenerate triangles."},
    "not_closed": {"ru": "Сетка не замкнута.", "en": "The mesh is not closed."},
    "non_manifold": {"ru": "Есть неманифолдные рёбра.", "en": "There are non-manifold edges."},
    "inconsistent_normals": {"ru": "Нормали согласованы не везде.", "en": "Normals are inconsistent."},
    "inward_normals": {"ru": "Нормали направлены внутрь.", "en": "Normals point inwards."},
    "size_mismatch": {"ru": "Габариты не совпадают со спецификацией.", "en": "Size differs from the specification."},
    "wall_too_thin": {"ru": "Стенка тоньше одной линии экструзии.", "en": "A wall is thinner than one extrusion line."},
    "exceeds_build_volume": {"ru": "Модель не помещается в рабочий объём.",
                             "en": "The model does not fit the build volume."},
    "unreadable_file": {"ru": "Файл геометрии не читается.", "en": "The geometry file cannot be read."},
}

UI = {
    "ru": {"model": "Созданная модель", "part": "Деталь", "size": "Габариты", "check": "Проверка",
           "ok": "пройдена", "failed": "есть ошибки", "unknown": "не выполнена", "warnings": "Предупреждения",
           "revision": "Версия", "defaults": "Допущения", "mm": "мм", "none": "нет"},
    "en": {"model": "Generated model", "part": "Part", "size": "Size", "check": "Check",
           "ok": "passed", "failed": "has errors", "unknown": "not run", "warnings": "Warnings",
           "revision": "Revision", "defaults": "Assumptions", "mm": "mm", "none": "none"},
}


def pick(table, key, language):
    entry = table.get(key)
    if entry is None:
        return str(key)
    return entry.get(language) or entry.get("en") or str(key)
