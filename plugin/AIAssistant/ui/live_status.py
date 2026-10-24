import random

MIN_INTERVAL = 6.0
MAX_INTERVAL = 10.0
HUMOR_GAP = 3
HUMOR_CHANCE = 0.3

PHRASES = {
    "ru": {
        "unknown": ["Оцениваю задачу…", "Разбираюсь, с чего лучше начать…"],
        "prepare": ["Читаю задачу и собираю контекст…", "Смотрю, что уже есть в сцене и настройках…"],
        "scene": ["Загружаю модель в сцену…", "Осматриваю модель со всех сторон…"],
        "geometry": ["Проверяю геометрию — здесь есть над чем подумать.", "Измеряю габариты и ищу нависания…",
                     "Проверяю, нет ли у детали оси симметрии…"],
        "recommend": ["Подбираю материал под задачу…", "Сверяю требования с правилами выбора режима…"],
        "settings": ["Раскладываю параметры по полочкам…", "Меняю только те настройки, которые действительно нужны…"],
        "orientation": ["Ищу устойчивое положение на столе…", "Прикидываю, где понадобятся поддержки…"],
        "slicing": ["Слайсер считает траектории. Самая математическая часть.",
                    "Слой за слоем прокладываю путь сопла…"],
        "export": ["Почти готово — осталось упаковать результат.", "Сохраняю G-code и проект…"],
        "answer": ["Проверяю результат, чтобы ничего не забыть…", "Собираю короткий итог…"],
    },
    "en": {
        "unknown": ["Sizing up the task…", "Working out where to start…"],
        "prepare": ["Reading the task and gathering context…", "Checking what is already in the scene and settings…"],
        "scene": ["Loading the model into the scene…", "Looking at the model from every side…"],
        "geometry": ["Checking the geometry — there is something to think about here.",
                     "Measuring the size and looking for overhangs…", "Checking whether the part has a symmetry axis…"],
        "recommend": ["Choosing a material for the job…", "Matching the requirements against the mode rules…"],
        "settings": ["Putting the parameters in order…", "Changing only the settings that really matter…"],
        "orientation": ["Looking for a stable position on the bed…", "Working out where supports would be needed…"],
        "slicing": ["The slicer is computing toolpaths. The most mathematical part.",
                    "Laying out the nozzle path layer by layer…"],
        "export": ["Almost there — just packing up the result.", "Saving the G-code and the project…"],
        "answer": ["Double-checking the result so nothing is missed…", "Putting together a short summary…"],
    },
}

HUMOR = {
    "ru": {
        "settings": ["Подбираю параметры — раскладываю слои по полочкам…"],
        "slicing": ["Завариваю виртуальный кофе, пока слайсер считает слои…"],
    },
    "en": {
        "settings": ["Tuning parameters — sorting the layers onto shelves…"],
        "slicing": ["Brewing a virtual coffee while the slicer counts layers…"],
    },
}


def phrases(language, stage, humor=False):
    table = (HUMOR if humor else PHRASES).get(language) or (HUMOR if humor else PHRASES)["en"]
    return list(table.get(stage or "unknown") or ([] if humor else table["unknown"]))


class LiveStatus(object):
    def __init__(self, language="ru", seed=None):
        self.language = language
        self._random = random.Random(seed)
        self.reset()

    def reset(self):
        self.text = ""
        self.humorous = False
        self._next_at = 0.0
        self._since_humor = HUMOR_GAP

    def update(self, stage, state, now, enabled=True, serious=False):
        previous = self.text
        if not enabled or state != "running":
            self.reset()
            return previous != self.text
        if serious and self.humorous:
            self._next_at = 0.0
        if self.text and now < self._next_at:
            return False
        self.text = self._pick(stage, serious)
        self._next_at = now + self._random.uniform(MIN_INTERVAL, MAX_INTERVAL)
        return previous != self.text

    def _pick(self, stage, serious):
        funny = [] if serious else phrases(self.language, stage, humor=True)
        use_humor = bool(funny) and self._since_humor >= HUMOR_GAP and self._random.random() < HUMOR_CHANCE
        pool = funny if use_humor else phrases(self.language, stage)
        choices = [p for p in pool if p != self.text] or [p for p in phrases(self.language, stage) if p != self.text]
        if not choices:
            return self.text
        choice = self._random.choice(choices)
        self.humorous = choice in funny
        self._since_humor = 0 if self.humorous else self._since_humor + 1
        return choice
