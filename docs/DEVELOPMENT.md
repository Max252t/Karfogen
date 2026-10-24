# Разработка

## Ветвление и коммиты

- Модель Git Flow: `main` — стабильная ветка, `develop` — интеграция, `feature/*` и `fix/*` — отдельные изменения.
  Изменения сливаются в `develop` через pull request или `--no-ff`; в `main` — перед сдачей.
- Сообщения коммитов — Conventional Commits: `тип(область): описание`, где тип — `feat`, `fix`, `docs`, `style`,
  `refactor`, `perf`, `test`, `build`, `ci`, `chore`. Строки соавторства (`Co-Authored-By`) не допускаются.
  Язык сообщений выбирается один на репозиторий (сейчас английский).
- Комментарии в коде не пишутся: код должен читаться сам, пояснения идут в документацию.
- Проверку сообщений выполняет `scripts/check_commits.py`. Известные коммиты, не соответствующие формату,
  перечислены в `scripts/commit_check_ignore.txt`; переписывать общую историю не нужно.

## Ограничения кода

- Python 3.5: без f-строк, аннотаций переменных, `dataclasses`, `asyncio.run`; запятая после `*args` не допускается;
  `json.loads` принимает только `str`.
- Только стандартная библиотека и модули дистрибутива.
- Обращения к слайсеру только через `run_on_main`; запись G-code и 3MF — только вне главного потока.
- QML ограничен импортами Qt 5.10 (`scripts/check_qml.py` проверяет это).
- Ключи, адреса API и личные пути в репозиторий не попадают (`scripts/check_hygiene.py` ищет секреты).

## Запуск проверок

```bash
python scripts/check_py35.py
python scripts/check_hygiene.py
python scripts/check_qml.py
python -m unittest discover -s tests
python scripts/check_commits.py "origin/develop..HEAD"
```

Для тестов нужен numpy. Тесты нативного интерфейса (`test_native_*`) требуют PyQt5 и без него пропускаются;
на Windows CI они запускаются с `QT_QUICK_BACKEND=software`. Тесты с образцами деталей используют папку из переменной
`KARFOGEN_SAMPLE_PARTS` и пропускаются, если её нет.

`scripts/preview_native_ui.py` рисует состояния окна в PNG без слайсера (нужен PyQt5).
`scripts/mcp_smoke.sh [порт]` отправляет в `/mcp` запросы `initialize`, `tools/list` и вызовы инструментов.

## CI (`.github/workflows/ci.yml`)

Запускается на push в `main`, `develop`, `feature/**` и на pull request в `main` и `develop`.

| Задача | Что проверяет |
|---|---|
| Python 3.9, Python 3.12 | синтаксис Python 3.5, гигиену репозитория, QML, все тесты |
| Legacy web interface | `node --check` для JavaScript в `web/` |
| Native QML and controller | тесты нативного интерфейса на Windows с PyQt5 |
| Commit messages | формат Conventional Commits для новых коммитов |

## Установка в слайсер для проверки

```powershell
Copy-Item -Recurse -Force "plugin\AIAssistant" "$env:APPDATA\steslicer\7.10\plugins\"
```

Слайсер нужно перезапустить: Python-код и QML загружаются при старте. Журнал плагина — строки `AIAssistant:`
в `stderr.log` и `steslicer.log` в папке конфигурации (`%APPDATA%\steslicer\7.10`).
Проверка MCP без LLM: `sh scripts/mcp_smoke.sh <порт>`, порт выводится в журнале строкой `server listening on`.

## Сдача

`python scripts/pack.py <имя_команды>` проверяет `results/<модель>/` (`project.3mf`, `result.gcode`, `chat_*.png`,
строки времени и расхода в G-code, валидность zip), ищет утечки ключа и лишние файлы в `plugin/`,
затем собирает `<имя_команды>.zip` с папками `plugin/` и `results/`.
Перед сдачей скопируйте нужные результаты из папки результатов плагина в `results/` репозитория.

## Лицензия

MIT, файл `LICENSE` в корне.
