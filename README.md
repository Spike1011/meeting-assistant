# Meeting Assistant

Monorepo для сервера обработки встреч и нативного macOS-клиента.

## Структура

```text
apps/server/   FastAPI, транскрибация, LLM и временно legacy CLI-рекордер
apps/macos/    нативный SwiftUI-клиент
contracts/     версионированный OpenAPI-контракт
infra/         Docker Compose и конфигурация reverse proxy
scripts/       общие скрипты разработки
```

Компоненты имеют независимые зависимости и жизненные циклы. Клиент и сервер связывает только контракт из `contracts/openapi.yaml`.

## Сервер

```bash
make server-install
make server-api
```

Swagger UI будет доступен на `http://127.0.0.1:8000/docs`.

Существующий CLI пока сохранён для обратной совместимости:

```bash
make server-run
make server-setup
```

## Docker

Создайте локальную конфигурацию и заполните ключи:

```bash
cp apps/server/.env.example apps/server/.env
```

Затем выполните:

```bash
make infra-up
```

## macOS

Каркас и правила разработки клиента описаны в `apps/macos/README.md`. Xcode-проект будет добавлен на этапе реализации SwiftUI-клиента.

## API-контракт

`contracts/openapi.yaml` фиксирует целевой API v1. Изменения клиент-серверного интерфейса сначала вносятся в контракт, затем реализуются обоими компонентами.
