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
    ("CPE", dict(heat=70, stiff=3, flex=2, uv=3, chem=4, moist=4, wear=3, impact=3, ease=4, light=3, food=4, esd=1, detail=4)),
    ("CPE_PLUS", dict(heat=100, stiff=4, flex=1, uv=3, chem=4, moist=4, wear=3, impact=3, ease=3, light=3, food=3, esd=1, detail=3)),
    ("ABS", dict(heat=85, stiff=3, flex=2, uv=2, chem=3, moist=4, wear=3, impact=3, ease=2, light=5, food=1, esd=1, detail=3)),
    ("PC", dict(heat=110, stiff=4, flex=1, uv=2, chem=2, moist=2, wear=3, impact=5, ease=1, light=3, food=2, esd=1, detail=3)),
    ("PA", dict(heat=85, stiff=3, flex=2, uv=3, chem=4, moist=1, wear=5, impact=5, ease=2, light=4, food=3, esd=2, detail=3)),
    ("PP", dict(heat=100, stiff=2, flex=3, uv=2, chem=5, moist=5, wear=3, impact=4, ease=1, light=5, food=5, esd=1, detail=2)),
    ("SBS", dict(heat=70, stiff=2, flex=3, uv=3, chem=3, moist=4, wear=3, impact=4, ease=3, light=3, food=2, esd=1, detail=3)),
    ("TPU", dict(heat=70, stiff=1, flex=5, uv=3, chem=4, moist=4, wear=5, impact=5, ease=2, light=3, food=2, esd=1, detail=2)),
])

MATERIAL_IDS = OrderedDict([
    ("PLA", ["generic_pla", "generic_pla_175"]),
    ("TOUGH_PLA", ["generic_tough_pla"]),
    ("PETG", ["generic_petg", "enduse_petg", "generic_petg_175"]),
    ("CPE", ["generic_cpe"]),
    ("CPE_PLUS", ["generic_cpe_plus"]),
    ("ABS", ["generic_abs", "enduse_abs", "generic_abs_175"]),
    ("PC", ["generic_pc", "enduse_pc", "generic_pc_175"]),
    ("PA", ["generic_nylon", "enduse_pa6", "generic_nylon_175"]),
    ("PP", ["generic_pp", "enduse_pp"]),
    ("SBS", ["enduse_sbs"]),
    ("TPU", ["generic_tpu", "enduse_tpu_d70", "generic_tpu_175"]),
])

SPECIAL_PREFIXES = ("fiberpart_", "contifiber", "metalcast_", "sealant_", "proto_")

ELASTIC_TPU_IDS = OrderedDict([
    ("flexible", ["sealant_tpu93", "sealant_tpu", "sealant_tpu_A95", "generic_tpu", "enduse_tpu_d70"]),
    ("semi", ["generic_tpu", "sealant_tpu_A95", "sealant_tpu", "enduse_tpu_d70"]),
])

LINE_WIDTH_MM = 0.4

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

LIMITATION_PROPS = OrderedDict([
    ("uv", ("uv", "lim_uv")),
    ("humidity", ("moist", "lim_moist")),
    ("chemical", ("chem", "lim_chem")),
    ("wear", ("wear", "lim_wear")),
    ("impact", ("impact", "lim_impact")),
    ("food_safe", ("food", "lim_food")),
])

LIMITATION_THRESHOLD = 2

PROPERTY_LABELS = {
    "ru": {"heat": "теплостойкость %d °C", "stiff": "жёсткость %d/5", "flex": "эластичность %d/5", "uv": "стойкость к УФ %d/5",
           "chem": "химстойкость %d/5", "moist": "стойкость к влаге %d/5", "wear": "износостойкость %d/5",
           "impact": "ударная вязкость %d/5", "light": "лёгкость %d/5", "food": "безопасность для пищи %d/5",
           "esd": "антистатичность %d/5", "detail": "детализация %d/5", "ease": "простота печати %d/5"},
    "en": {"heat": "heat resistance %d °C", "stiff": "stiffness %d/5", "flex": "elasticity %d/5", "uv": "UV resistance %d/5",
           "chem": "chemical resistance %d/5", "moist": "moisture resistance %d/5", "wear": "wear resistance %d/5",
           "impact": "impact toughness %d/5", "light": "lightness %d/5", "food": "food safety %d/5",
           "esd": "antistatic %d/5", "detail": "detail %d/5", "ease": "ease of printing %d/5"},
}

QUALITY_LAYER_HEIGHT = OrderedDict([
    ("high", 0.06),
    ("normal", 0.1),
    ("fast", 0.15),
    ("draft", 0.2),
    ("verydraft", 0.3),
    ("coarse", 0.4),
])


REASONS = {
    "ru": {
        "mode_simple": "флекс/декор/прототип: стандартная 3D-печать",
        "mode_disc": "тело вращения, но плоский диск (длина/диаметр=%.2f < 0.35): в 3D эффективнее",
        "mode_thin": "тонкостенная оболочка (средняя стенка %.1f мм < 2.5): в 3D",
        "mode_long": "длина оси больше рабочей высоты 5D (%.0f мм)",
        "mode_rotary": "тело вращения (симметрия, ось %s, длина/диаметр=%.2f) с требованиями к точности/нагрузке: слои по окружности",
        "mode_shaft": "вал/ось: призматический профиль вдоль оси (боковая поверхность %.0f%%), вращение, нагрузка на скручивание и точный профиль: 5D",
        "mode_none": "нет признаков, требующих 5D",
        "mode_forced": "режим задан явно: %s",
        "orient_axis": "ось симметрии вертикально, по центру стола",
        "orient_goal": "ориентация по цели %s",
        "temp_fail": "не выдерживает %s °C",
        "temp_tight": "запас по температуре менее 10 °C (%d °C)",
        "temp_ok": "запас по температуре %d °C",
        "q_proto": "быстрый прототип: слой 0.2",
        "q_precision": "точность/внешний вид: тонкий слой (%.2f мм)",
        "q_decor": "декор: слой 0.1, слои почти не видны",
        "q_default": "стандартное функциональное качество: слой 0.15",
        "walls_rotating_load": "нагрузка на вращающуюся деталь: 6 периметров, зубья, ступицы и посадочные места становятся почти сплошными",
        "infill_rotating_load": "нагрузка на вращающуюся деталь: заполнение 60%",
        "lim_uv": "стойкость к УФ ограничена (%d/5): защитите деталь покраской или УФ-лаком",
        "lim_moist": "стойкость к влаге ограничена (%d/5): при длительном нагреве и высокой влажности возможна потеря вязкости, избегайте щелочей и аммиака",
        "lim_chem": "химстойкость ограничена (%d/5): проверьте совместимость материала со средой",
        "lim_wear": "износостойкость ограничена (%d/5): возможен ускоренный износ",
        "lim_impact": "ударная вязкость ограничена (%d/5): возможно хрупкое разрушение при ударе",
        "lim_food": "безопасность для контакта с пищей ограничена (%d/5): проверьте допуск материала",
        "walls_load": "нагрузка: 4 периметра",
        "infill_load": "нагрузка: заполнение 40%",
        "pattern_load": "нагрузка: изотропный gyroid",
        "walls_airtight": "герметичность: не менее 4 периметров",
        "walls_decor": "декор: 2 периметра",
        "infill_decor": "декор: заполнение 10%",
        "infill_proto": "прототип: заполнение 10%",
        "speed_flex": "эластичный материал: низкая скорость",
        "infill_flex": "эластичная деталь: заполнение 15%",
        "layers_load": "нагрузка/герметичность: %d верхних и нижних слоёв",
        "no_support": "поддержки запрещены: ориентация с минимумом нависаний",
        "no_support_flex": "эластичная деталь: поддержки из того же материала спекаются с ней и не снимаются; ориентация с минимумом нависаний",
        "infill_thin": "стенка около %.1f мм уже заполняется %d периметрами, заполнение не влияет и не меняется",
        "mat_flex_soft": "эластичная деталь: мягкий термополиуретан для уплотнений (%s); жёсткий Enduse TPU D70 (Шор 70D) не подходит",
        "mat_unavailable": "недоступны на этом принтере и пропущены: %s",
        "mat_profile": "по требованиям: %s",
        "mat_flex_hard": "Enduse TPU D70 имеет твёрдость 70 по Шору D: подходит для жёстких уплотнений, для гибких деталей нужен мягкий TPU",
    },
    "en": {
        "mode_simple": "flexible/decorative/prototype: standard 3D printing",
        "mode_disc": "body of revolution but a flat disc (length/diameter=%.2f < 0.35): more efficient in 3D",
        "mode_thin": "thin-walled shell (mean wall %.1f mm < 2.5): 3D",
        "mode_long": "axis length exceeds the 5D build height (%.0f mm)",
        "mode_rotary": "body of revolution (symmetry, axis %s, length/diameter=%.2f) with precision/load requirements: layers around the circumference",
        "mode_shaft": "shaft/axle: prismatic profile along the axis (lateral surface %.0f%%), rotation, torsion load and precise profile: 5D",
        "mode_none": "nothing requires 5D",
        "mode_forced": "mode set explicitly: %s",
        "orient_axis": "symmetry axis vertical, centered on the plate",
        "orient_goal": "orientation for goal %s",
        "temp_fail": "cannot withstand %s °C",
        "temp_tight": "temperature margin below 10 °C (%d °C)",
        "temp_ok": "temperature margin %d °C",
        "q_proto": "fast prototype: 0.2 layer",
        "q_precision": "precision/appearance: fine layer (%.2f mm)",
        "q_decor": "decorative: 0.1 layer, layers barely visible",
        "q_default": "standard functional quality: 0.15 layer",
        "walls_rotating_load": "load on a rotating part: 6 perimeters, teeth, hubs and mating seats become almost solid",
        "infill_rotating_load": "load on a rotating part: 60% infill",
        "lim_uv": "UV resistance is limited (%d/5): protect the part with paint or UV varnish",
        "lim_moist": "moisture resistance is limited (%d/5): prolonged heat and high humidity may reduce toughness, avoid alkalis and ammonia",
        "lim_chem": "chemical resistance is limited (%d/5): check compatibility with the environment",
        "lim_wear": "wear resistance is limited (%d/5): accelerated wear is possible",
        "lim_impact": "impact toughness is limited (%d/5): brittle failure on impact is possible",
        "lim_food": "food contact safety is limited (%d/5): check the material approval",
        "walls_load": "load: 4 perimeters",
        "infill_load": "load: 40% infill",
        "pattern_load": "load: isotropic gyroid",
        "walls_airtight": "airtight: at least 4 perimeters",
        "walls_decor": "decorative: 2 perimeters",
        "infill_decor": "decorative: 10% infill",
        "infill_proto": "prototype: 10% infill",
        "speed_flex": "elastic material: low speed",
        "infill_flex": "elastic part: 15% infill",
        "layers_load": "load/airtight: %d top and bottom layers",
        "no_support": "supports forbidden: orientation with minimal overhangs",
        "no_support_flex": "elastic part: supports in the same material fuse with it and cannot be removed; orientation with minimal overhangs",
        "infill_thin": "the wall of about %.1f mm is already filled by %d perimeters, infill has no effect and is left unchanged",
        "mat_flex_soft": "elastic part: soft sealing polyurethane (%s); the rigid Enduse TPU D70 (Shore 70D) does not fit",
        "mat_unavailable": "not available on this printer and skipped: %s",
        "mat_profile": "against the requirements: %s",
        "mat_flex_hard": "Enduse TPU D70 is Shore 70D: suitable for rigid seals, flexible parts need a soft TPU",
    },
}


def reason(key, *args):
    from .. import config
    table = REASONS.get(config.effective_language(), REASONS["en"])
    text = table[key]
    return text % args if args else text


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
                reasons.append(reason("temp_fail", max_temp_c))
            elif margin >= 10:
                score += 4.0
                reasons.append(reason("temp_ok", margin))
            else:
                score -= 15.0
                reasons.append(reason("temp_tight", margin))
        if flexibility == "flexible" and props["flex"] < 4:
            score -= 30.0
        if flexibility == "rigid" and props["flex"] >= 4:
            score -= 30.0
        if "flexible" not in tags and flexibility != "flexible" and props["flex"] >= 4:
            score -= 8.0
        ranked.append({"type": name, "score": round(score, 2), "notes": reasons})
    ranked.sort(key=lambda r: -r["score"])
    return ranked


def resolve_material_id(material_type, available_ids, prefer_enduse=False, flexibility=None):
    available = set(available_ids)
    candidates = list(MATERIAL_IDS.get(material_type, []))
    if material_type == "TPU" and flexibility in ELASTIC_TPU_IDS:
        candidates = list(ELASTIC_TPU_IDS[flexibility])
    elif prefer_enduse and material_type in ENDUSE_IDS:
        candidates.insert(0, ENDUSE_IDS[material_type])
    for cid in candidates:
        if cid in available:
            return cid
        if cid + "_175" in available:
            return cid + "_175"
    needle = material_type.lower().replace("_", "")
    for cid in available_ids:
        if cid.startswith(SPECIAL_PREFIXES):
            continue
        if needle in cid.lower().replace("_", ""):
            return cid
    return None


def is_special_material(material_id):
    return material_id.startswith(SPECIAL_PREFIXES)


def is_elastic_sealant(material_id):
    return material_id.startswith("sealant_")


def material_warning(material_id):
    if is_elastic_sealant(material_id):
        return ("%s is a soft sealing elastomer for flexible parts (seals, boots, gaskets). "
                "Do not use it for rigid parts." % material_id)
    if is_special_material(material_id):
        return ("%s is a special material (fiber-reinforced, metal or proto line). "
                "Use it only if the user asked for it; otherwise choose a generic or enduse material." % material_id)
    return None


def material_reason(material_type, material_id, flexibility):
    if material_type != "TPU":
        return ""
    if material_id == "enduse_tpu_d70":
        return reason("mat_flex_hard")
    if flexibility == "flexible":
        return reason("mat_flex_soft", material_id)
    return ""


def material_limitations(material_type, tags):
    props = MATERIAL_TYPES.get(material_type)
    if not props:
        return []
    result = []
    for tag, (prop, key) in LIMITATION_PROPS.items():
        if tag in (tags or []) and props[prop] <= LIMITATION_THRESHOLD:
            result.append(reason(key, props[prop]))
    return result


def material_profile(material_type, tags):
    from .. import config
    props = MATERIAL_TYPES.get(material_type)
    if not props:
        return []
    labels = PROPERTY_LABELS.get(config.effective_language(), PROPERTY_LABELS["en"])
    wanted = ["heat"]
    for tag in tags or []:
        for prop in TAG_WEIGHTS.get(tag, {}):
            if prop in props and prop not in wanted:
                wanted.append(prop)
    return [labels[prop] % props[prop] for prop in wanted if prop in labels]


def infill_matters(mean_wall_mm, walls):
    if not mean_wall_mm:
        return True
    return mean_wall_mm > 2 * walls * LINE_WIDTH_MM + 0.2


def choose_mode(analysis, tags, machine_height_5d=231.1):
    tags = set(tags or [])
    sym = (analysis or {}).get("axisymmetry") or {}
    wall = (analysis or {}).get("mean_wall_mm", 0.0)
    reasons = []
    if "flexible" in tags or "decorative" in tags or "fast_proto" in tags:
        reasons.append(reason("mode_simple"))
        return "classic", reasons
    if sym.get("is_axisymmetric"):
        aspect = sym.get("aspect", 0.0)
        if aspect < 0.35:
            reasons.append(reason("mode_disc", aspect))
            return "classic", reasons
        if wall and wall < 2.5:
            reasons.append(reason("mode_thin", wall))
            return "classic", reasons
        if sym.get("length_mm", 0) > machine_height_5d:
            reasons.append(reason("mode_long", machine_height_5d))
            return "classic", reasons
        if tags & {"precision", "rotating", "wear", "load_bearing", "airtight"}:
            reasons.append(reason("mode_rotary", sym.get("axis"), aspect))
            return "cylindrical_full", reasons
    elif ({"rotating", "load_bearing", "precision"} <= tags and sym.get("aspect", 0) >= 0.5
          and sym.get("lateral_area_ratio", 0) >= 0.5):
        reasons.append(reason("mode_shaft", sym.get("lateral_area_ratio", 0) * 100))
        return "cylindrical_full", reasons
    reasons.append(reason("mode_none"))
    return "classic", reasons


def recommend_settings(tags, mode, mean_wall_mm=None):
    tags = set(tags or [])
    reasons = OrderedDict()
    settings = OrderedDict()
    quality = "fast"
    if "fast_proto" in tags:
        quality = "draft"
        reasons["quality"] = reason("q_proto")
    elif tags & {"precision"} or (tags & {"decorative"} and "thin_features" in tags):
        quality = "high" if "decorative" in tags else "normal"
        reasons["quality"] = reason("q_precision", QUALITY_LAYER_HEIGHT[quality])
    elif "decorative" in tags:
        quality = "normal"
        reasons["quality"] = reason("q_decor")
    else:
        reasons["quality"] = reason("q_default")

    walls = 2
    infill = 20
    pattern = None
    top = None
    if "load_bearing" in tags or "stiff" in tags:
        walls, infill, pattern, top = 4, 40, "gyroid", 6
        reasons["wall_line_count"] = reason("walls_load")
        reasons["infill_sparse_density"] = reason("infill_load")
        reasons["infill_pattern"] = reason("pattern_load")
        if "load_bearing" in tags and tags & {"rotating", "impact"}:
            walls, infill = 6, 60
            reasons["wall_line_count"] = reason("walls_rotating_load")
            reasons["infill_sparse_density"] = reason("infill_rotating_load")
    if "airtight" in tags:
        walls = max(walls, 4)
        infill = max(infill, 40)
        reasons["wall_line_count"] = reason("walls_airtight")
        top = max(top or 0, 6)
    if "decorative" in tags and not tags & {"load_bearing", "stiff"}:
        walls, infill = 2, 10
        reasons["wall_line_count"] = reason("walls_decor")
        reasons["infill_sparse_density"] = reason("infill_decor")
    if "fast_proto" in tags:
        walls, infill = 2, 10
        reasons["infill_sparse_density"] = reason("infill_proto")
    if "flexible" in tags:
        walls, infill, pattern = max(walls, 3) if "airtight" in tags else 3, 15, "gyroid"
        settings["speed_print"] = 25
        reasons["speed_print"] = reason("speed_flex")
        reasons["infill_sparse_density"] = reason("infill_flex")
    settings["wall_line_count"] = walls
    if "flexible" not in tags or infill_matters(mean_wall_mm, walls):
        settings["infill_sparse_density"] = infill
        if pattern:
            settings["infill_pattern"] = pattern
    else:
        reasons.pop("infill_sparse_density", None)
        reasons.pop("infill_pattern", None)
        reasons["note_infill"] = reason("infill_thin", mean_wall_mm, walls)
    if top:
        settings["top_layers"] = top
        settings["bottom_layers"] = top
        reasons["top_layers"] = reason("layers_load", top)
    if "no_supports" in tags:
        settings["support_enable"] = False
        reasons["support_enable"] = reason("no_support")
    elif "flexible" in tags:
        settings["support_enable"] = False
        reasons["support_enable"] = reason("no_support_flex")
    return quality, settings, reasons


def build_prompt_rules():
    lines = []
    lines.append("ПРАВИЛА ВЫБОРА (детерминированные, применяются инструментом recommend_setup):")
    lines.append("- Режим 5D (cylindrical_full) выбирается для тел вращения с отношением длина/диаметр >= 0.35, "
                 "средней стенкой >= 2.5 мм и требованиями точности, вращения, износа, нагрузки или герметичности. "
                 "Плоские диски (<0.35), тонкостенные оболочки, эластичные и декоративные детали, прототипы - 3D (classic).")
    lines.append("- Эластичные детали (пыльники, уплотнения, прокладки; flexibility=flexible): мягкий TPU для уплотнений "
                 "(sealant_tpu93, sealant_tpu, sealant_tpu_A95), а не Enduse TPU D70 - он жёсткий (Шор 70D). "
                 "Поддержки для них не включаются: из того же материала они спекаются с деталью.")
    lines.append("- Теплостойкость материала должна быть не ниже max_temp_c + 10 °C. Эластичность - TPU. "
                 "Влажность/химия - PP, PETG, CPE. Износ/скольжение - PA. Жёсткость и нагрев - PC, CPE+.")
    lines.append("- Нагрузка на вращающуюся деталь или удары: 6 периметров, заполнение 60% gyroid.")
    lines.append("- Если выбранный материал слаб по требованию задачи (УФ, влага, химия, износ), в ответе прямо назови это ограничение "
                 "и дай рекомендацию из поля limitations (покраска, УФ-лак, исключить щёлочи). Недоступные на принтере материалы "
                 "(например, ASA) не предлагай.")
    lines.append("- Нагрузка: 4 периметра, заполнение 40% gyroid. Декор: 2 периметра, заполнение 10%, тонкий слой. "
                 "Прототип: слой 0.2, заполнение 10%.")
    lines.append("- Без поддержек: support_enable=false и ориентация с минимумом нависаний (suggest_orientation, goal=no_supports).")
    lines.append("- Допустимые значения тегов: " + ", ".join(TAGS.keys()))
    return "\n".join(lines)
