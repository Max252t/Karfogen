# Karfogen — AI Assistant для STE Slicer

Плагин для STE Slicer (форк Cura 3.6): чат-бот на базе LLM в нативном окне слайсера
(**Extensions → AI Assistant → Open chat**), который по текстовому описанию задачи, изображениям и 3D-моделям
подбирает режим печати (3D / 5D Spiral / 5D), материал, профиль качества и настройки, ориентирует модель,
запускает слайсинг и сохраняет G-code и проект 3MF.

## Структура

- `plugin/AIAssistant` — исходный код плагина (Python 3.5, без сторонних пакетов).
- `plugin/AIAssistant/ui`, `plugin/AIAssistant/qml` — нативный интерфейс (контроллер на `QObject` и QML-окно).
- `scripts` — проверки (`check_py35.py`, `check_hygiene.py`, `check_qml.py`), упаковка, smoke-тест MCP,
  `preview_native_ui.py` — рендер состояний окна в PNG без слайсера (нужен PyQt5).
- `tests` — тесты логики, контроллера и загрузки QML (QML-тесты пропускаются без PyQt5).
- `docs` — заметки по тестовым моделям, фактам о дистрибутиве и устройству нативного интерфейса (`native_ui.md`).
- `results` — результаты прогонов (`<model_name>/project.3mf`, `result.gcode`, `chat_*.png`).

## Ветвление

Git Flow: `main` — стабильная ветка, `develop` — интеграция, `feature/*` — разработка функций.
Сообщения коммитов следуют Conventional Commits.

## Ключ и адрес LLM

Адрес API, модель и ключ не хранятся в репозитории. Они задаются в настройках плагина
либо переменными окружения `AI_ASSISTANT_BASE_URL`, `AI_ASSISTANT_MODEL`, `AI_ASSISTANT_API_KEY`.

Подробная инструкция по установке и использованию — в `plugin/AIAssistant/README.md`.
