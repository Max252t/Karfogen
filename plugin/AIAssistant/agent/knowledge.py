from collections import OrderedDict

MODE_LABELS = OrderedDict([
    ("classic", "3D"),
    ("cylindrical", "5D Spiral"),
    ("cylindrical_full", "5D"),
])

TAGS = OrderedDict([
    ("load_bearing", "Механическая нагрузка, прочность, крутящий момент, усталость"),
    ("high_temp", "Нагрев в эксплуатации (используй max_temp_c)"),
    ("flexible", "Нужна эластичность/гибкость (резиноподобная деталь)"),
    ("wear", "Износ, трение скольжения, абразив"),
    ("uv", "Ультрафиолет, улица, солнечный свет"),
    ("chemical", "Контакт с химией: щёлочи, спирты, масла, топливо, теплоносители"),
    ("humidity", "Высокая влажность или контакт с водой"),
    ("food_safe", "Контакт с пищей / безопасность по токсичности"),
    ("decorative", "Декоративная деталь, внешний вид важнее прочности"),
    ("precision", "Высокая точность размеров и поверхности, допуски"),
    ("fast_proto", "Быстрый прототип, скорость важнее качества"),
    ("no_supports", "Поддержки нежелательны или запрещены"),
    ("rotating", "Деталь вращается или работает на оси"),
    ("lightweight", "Малый вес/плотность важны"),
    ("impact", "Ударные нагрузки, нужна вязкость"),
    ("airtight", "Герметичность / водонепроницаемость"),
    ("esd", "Антистатические свойства"),
    ("stiff", "Высокая жёсткость, малая ползучесть"),
    ("thin_features", "Тонкие хрупкие элементы"),
])

MATERIAL_TYPES = OrderedDict([
    ("PLA", dict(heat=55, stiff=4, flex=1, uv=2, chem=2, moist=3, wear=2, impact=1, ease=5, light=3, food=3, esd=1, detail=5)),
    ("TOUGH_PLA", dict(heat=58, stiff=3, flex=1, uv=2, chem=2, moist=3, wear=2, impact=3, ease=4, light=3, food=3, esd=1, detail=4)),
    ("PETG", dict(heat=75, stiff=3, flex=2, uv=3, chem=4, moist=4, wear=3, impact=3, ease=4, light=3, food=4, esd=1, detail=4)),
    ("CPE", dict(heat=78, stiff=3, flex=2, uv=3, chem=4, moist=4, wear=3, impact=3, ease=4, light=3, food=4, esd=1, detail=4)),
    ("CPE_PLUS", dict(heat=100, stiff=4, flex=1, uv=3, chem=4, moist=4, wear=3, impact=3, ease=3, light=3, food=3, esd=1, detail=3)),
    ("ABS", dict(heat=95, stiff=3, flex=2, uv=2, chem=3, moist=4, wear=3, impact=3, ease=2, light=5, food=1, esd=1, detail=3)),
    ("PC", dict(heat=115, stiff=4, flex=1, uv=2, chem=2, moist=3, wear=3, impact=5, ease=1, light=3, food=2, esd=1, detail=3)),
    ("PA", dict(heat=85, stiff=3, flex=2, uv=3, chem=4, moist=1, wear=5, impact=5, ease=2, light=4, food=3, esd=2, detail=3)),
    ("PP", dict(heat=100, stiff=2, flex=3, uv=2, chem=5, moist=5, wear=3, impact=4, ease=1, light=5, food=5, esd=1, detail=2)),
    ("SBS", dict(heat=70, stiff=2, flex=3, uv=3, chem=3, moist=4, wear=3, impact=4, ease=3, light=3, food=2, esd=1, detail=3)),
    ("TPU", dict(heat=70, stiff=1, flex=5, uv=3, chem=4, moist=4, wear=5, impact=5, ease=2, light=3, food=2, esd=1, detail=2)),
])

MATERIAL_IDS = OrderedDict([
    ("PLA", ["generic_pla", "proto_pla", "generic_pla_175"]),
    ("TOUGH_PLA", ["generic_tough_pla", "generic_pla"]),
    ("PETG", ["generic_petg", "enduse_petg", "generic_petg_175"]),
    ("CPE", ["generic_cpe", "generic_cpe_175", "generic_petg"]),
    ("CPE_PLUS", ["generic_cpe_plus", "generic_cpe"]),
    ("ABS", ["generic_abs", "enduse_abs", "generic_abs_175"]),
    ("PC", ["generic_pc", "enduse_pc", "generic_pc_175"]),
    ("PA", ["generic_nylon", "enduse_pa6", "generic_nylon_175"]),
    ("PP", ["generic_pp", "enduse_pp"]),
    ("SBS", ["enduse_sbs"]),
    ("TPU", ["generic_tpu", "enduse_tpu_d70", "sealant_tpu", "generic_tpu_175"]),
])

SPECIAL_PREFIXES = ("fiberpart_", "contifiber", "metalcast_", "sealant_", "proto_")

ENDUSE_IDS = {
    "PETG": "enduse_petg", "ABS": "enduse_abs", "PC": "enduse_pc",
    "PA": "enduse_pa6", "PP": "enduse_pp", "SBS": "enduse_sbs", "TPU": "enduse_tpu_d70",
}

TAG_WEIGHTS = {
    "load_bearing": {"stiff": 2.0, "impact": 1.0, "heat": 0.01},
    "high_temp": {"heat": 0.0},
    "flexible": {"flex": 4.0, "impact": 1.0},
    "wear": {"wear": 2.5, "chem": 0.3},
    "uv": {"uv": 2.5},
    "chemical": {"chem": 3.0},
    "humidity": {"moist": 3.0},
    "food_safe": {"food": 2.5},
    "decorative": {"detail": 2.0, "ease": 1.0},
    "precision": {"detail": 1.5, "ease": 1.0, "stiff": 0.5},
    "fast_proto": {"ease": 3.0},
    "rotating": {"wear": 1.0, "stiff": 1.0},
    "lightweight": {"light": 2.0},
    "impact": {"impact": 3.0},
    "airtight": {"moist": 1.0, "chem": 1.0},
    "esd": {"esd": 3.0},
    "stiff": {"stiff": 3.0, "heat": 0.01},
    "thin_features": {"impact": 2.0, "ease": 0.5},
}

QUALITY_LAYER_HEIGHT = OrderedDict([
    ("high", 0.06),
    ("normal", 0.1),
    ("fast", 0.15),
    ("draft", 0.2),
    ("verydraft", 0.3),
    ("coarse", 0.4),
])


def rank_materials(tags, max_temp_c=None, flexibility=None):
    tags = [t for t in (tags or []) if t in TAG_WEIGHTS]
    ranked = []
    for name, props in MATERIAL_TYPES.items():
        score = 0.0
        reasons = []
        for tag in tags:
            for prop, weight in TAG_WEIGHTS[tag].items():
                if prop == "heat":
                    score += weight * props["heat"]
                else:
                    score += weight * props[prop]
        score += 0.25 * props["ease"]
        if max_temp_c is not None:
            margin = props["heat"] - float(max_temp_c)
            if margin < 0:
                score -= 40.0 + abs(margin) * 0.5
                reasons.append("не выдерживает %s °C" % max_temp_c)
            elif margin >= 10:
                score += 4.0
                reasons.append("запас по температуре %d °C" % margin)
            else:
                score += 1.0
        if flexibility == "flexible" and props["flex"] < 4:
            score -= 30.0
        if flexibility == "rigid" and props["flex"] >= 4:
            score -= 30.0
        if "flexible" not in tags and flexibility != "flexible" and props["flex"] >= 4:
            score -= 8.0
        ranked.append({"type": name, "score": round(score, 2), "notes": reasons})
    ranked.sort(key=lambda r: -r["score"])
    return ranked


def resolve_material_id(material_type, available_ids, prefer_enduse=False):
    available = set(available_ids)
    candidates = list(MATERIAL_IDS.get(material_type, []))
    if prefer_enduse and material_type in ENDUSE_IDS:
        candidates.insert(0, ENDUSE_IDS[material_type])
    for cid in candidates:
        if cid in available:
            return cid
    needle = material_type.lower().replace("_", "")
    for cid in available_ids:
        if cid.startswith(SPECIAL_PREFIXES):
            continue
        if needle in cid.lower().replace("_", ""):
            return cid
    return None


def is_special_material(material_id):
    return material_id.startswith(SPECIAL_PREFIXES)


def choose_mode(analysis, tags, machine_height_5d=231.1):
    tags = set(tags or [])
    sym = (analysis or {}).get("axisymmetry") or {}
    wall = (analysis or {}).get("mean_wall_mm", 0.0)
    reasons = []
    if "flexible" in tags or "decorative" in tags or "fast_proto" in tags:
        reasons.append("флекс/декор/прототип: стандартная 3D-печать")
        return "classic", reasons
    if sym.get("is_axisymmetric"):
        aspect = sym.get("aspect", 0.0)
        if aspect < 0.35:
            reasons.append("тело вращения, но плоский диск (длина/диаметр=%.2f < 0.35): в 3D эффективнее" % aspect)
            return "classic", reasons
        if wall and wall < 2.5:
            reasons.append("тонкостенная оболочка (средняя стенка %.1f мм < 2.5): в 3D" % wall)
            return "classic", reasons
        if sym.get("length_mm", 0) > machine_height_5d:
            reasons.append("длина оси больше рабочей высоты 5D (%.0f мм)" % machine_height_5d)
            return "classic", reasons
        if tags & {"precision", "rotating", "wear", "load_bearing", "airtight"}:
            reasons.append("тело вращения (симметрия, ось %s, длина/диаметр=%.2f) с требованиями к точности/нагрузке: слои по окружности" % (sym.get("axis"), aspect))
            return "cylindrical_full", reasons
    elif ({"rotating", "load_bearing", "precision"} <= tags and sym.get("aspect", 0) >= 0.5
          and sym.get("lateral_area_ratio", 0) >= 0.5):
        reasons.append("вал/ось: призматический профиль вдоль оси (боковая поверхность %.0f%%), вращение, "
                       "нагрузка на скручивание и точный профиль: 5D" % (sym.get("lateral_area_ratio", 0) * 100))
        return "cylindrical_full", reasons
    reasons.append("нет признаков, требующих 5D")
    return "classic", reasons


def recommend_settings(tags, mode, precision_level=None):
    tags = set(tags or [])
    reasons = OrderedDict()
    settings = OrderedDict()
    quality = "fast"
    if "fast_proto" in tags:
        quality = "draft"
        reasons["quality"] = "быстрый прототип: слой 0.2"
    elif tags & {"precision"} or (tags & {"decorative"} and "thin_features" in tags):
        quality = "high" if precision_level == "extreme" or "decorative" in tags else "normal"
        reasons["quality"] = "точность/внешний вид: тонкий слой (%.2f мм)" % QUALITY_LAYER_HEIGHT[quality]
    elif "decorative" in tags:
        quality = "normal"
        reasons["quality"] = "декор: слой 0.1, слои почти не видны"
    else:
        reasons["quality"] = "стандартное функциональное качество: слой 0.15"

    walls = 2
    infill = 20
    pattern = None
    top = None
    if "load_bearing" in tags or "stiff" in tags:
        walls, infill, pattern, top = 4, 40, "gyroid", 6
        reasons["wall_line_count"] = "нагрузка: 4 периметра"
        reasons["infill_sparse_density"] = "нагрузка: заполнение 40%"
        reasons["infill_pattern"] = "нагрузка: изотропный gyroid"
    if "airtight" in tags:
        walls = max(walls, 4)
        infill = max(infill, 40)
        reasons["wall_line_count"] = "герметичность: не менее 4 периметров"
        top = max(top or 0, 6)
    if "decorative" in tags and not tags & {"load_bearing", "stiff"}:
        walls, infill = 2, 10
        reasons["wall_line_count"] = "декор: 2 периметра"
        reasons["infill_sparse_density"] = "декор: заполнение 10%"
    if "fast_proto" in tags:
        walls, infill = 2, 10
        reasons["infill_sparse_density"] = "прототип: заполнение 10%"
    if "flexible" in tags:
        walls, infill, pattern = 3, 15, "gyroid"
        settings["speed_print"] = 25
        reasons["speed_print"] = "эластичный материал: низкая скорость"
        reasons["infill_sparse_density"] = "эластичная деталь: заполнение 15%"
    settings["wall_line_count"] = walls
    settings["infill_sparse_density"] = infill
    if pattern:
        settings["infill_pattern"] = pattern
    if top:
        settings["top_layers"] = top
        settings["bottom_layers"] = top
        reasons["top_layers"] = "нагрузка/герметичность: %d верхних и нижних слоёв" % top
    if "no_supports" in tags:
        settings["support_enable"] = False
        reasons["support_enable"] = "поддержки запрещены: ориентация с минимумом нависаний"
    return quality, settings, reasons


def build_prompt_rules():
    lines = []
    lines.append("ПРАВИЛА ВЫБОРА (детерминированные, применяются инструментом recommend_setup):")
    lines.append("- Режим 5D (cylindrical_full) выбирается для тел вращения с отношением длина/диаметр >= 0.35, "
                 "средней стенкой >= 2.5 мм и требованиями точности, вращения, износа, нагрузки или герметичности. "
                 "Плоские диски (<0.35), тонкостенные оболочки, эластичные и декоративные детали, прототипы - 3D (classic).")
    lines.append("- Теплостойкость материала должна быть не ниже max_temp_c + 10 °C. Эластичность - TPU. "
                 "Влажность/химия - PP, PETG, CPE. Износ/скольжение - PA. Жёсткость и нагрев - PC, CPE+.")
    lines.append("- Нагрузка: 4 периметра, заполнение 40% gyroid. Декор: 2 периметра, заполнение 10%, тонкий слой. "
                 "Прототип: слой 0.2, заполнение 10%.")
    lines.append("- Без поддержек: support_enable=false и ориентация с минимумом нависаний (suggest_orientation, goal=no_supports).")
    lines.append("- Допустимые значения тегов: " + ", ".join(TAGS.keys()))
    return "\n".join(lines)
