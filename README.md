# Karfogen — AI Assistant для STE Slicer

Плагин для STE Slicer (форк Cura 3.6): чат-бот на базе LLM в нативном окне слайсера
(**Extensions → AI Assistant → Open chat**), который по текстовому описанию задачи, изображениям и 3D-моделям
подбирает режим печати (3D / 5D Spiral / 5D), материал, профиль качества и настройки, ориентирует модель,
запускает слайсинг и сохраняет G-code и проект 3MF.

LLM управляет слайсером через 41 MCP-инструмент, а режим, материал и настройки подбирают правила в коде.
Те же инструменты доступны внешним MCP-клиентам по адресу `POST /mcp`.

## Структура

- `plugin/AIAssistant` — исходный код плагина (Python 3.5, без сторонних пакетов).
- `plugin/AIAssistant/ui`, `plugin/AIAssistant/qml` — нативный интерфейс (контроллер на `QObject` и QML-окно).
- `scripts` — проверки (`check_py35.py`, `check_hygiene.py`, `check_qml.py`, `check_commits.py`), упаковка (`pack.py`),
  smoke-тест MCP, `preview_native_ui.py` — рендер состояний окна в PNG без слайсера (нужен PyQt5).
- `tests` — тесты логики, контроллера и загрузки QML (QML-тесты пропускаются без PyQt5).
- `docs` — документация (список ниже).
- `results` — результаты прогонов (`<model_name>/project.3mf`, `result.gcode`, `chat_*.png`).
- `.github/workflows/ci.yml` — CI.

## Документация

| Файл | О чём |
|---|---|
| `plugin/AIAssistant/README.md` | установка, запуск, настройка, использование, типичные проблемы |
| `docs/ARCHITECTURE.md` | устройство плагина: модули, потоки, правила подбора, проекты |
| `docs/DEVELOPMENT.md` | ветвление, коммиты, проверки, CI, установка и сдача |
| `docs/native_ui.md`, `docs/native_ui_design.md`, `docs/native_ui_review.md` | нативный интерфейс: сценарии, дизайн, ревью |
| `docs/FACTS.md` | факты о дистрибутиве слайсера и гипотезы базы знаний |
| `docs/test_parts_tz.md` | технические задания семи тестовых деталей |

## Ветвление

Git Flow: `main` — стабильная ветка, `develop` — интеграция, `feature/*` и `fix/*` — отдельные изменения.
Сообщения коммитов следуют Conventional Commits. Подробности и список проверок — в `docs/DEVELOPMENT.md`.

## Ключ и адрес LLM

Адрес API, модель и ключ не хранятся в репозитории. Они задаются в настройках плагина
либо переменными окружения `AI_ASSISTANT_BASE_URL`, `AI_ASSISTANT_MODEL`, `AI_ASSISTANT_API_KEY`.

Подробная инструкция по установке и использованию — в `plugin/AIAssistant/README.md`.

## Лицензия

MIT, см. файл `LICENSE`.
