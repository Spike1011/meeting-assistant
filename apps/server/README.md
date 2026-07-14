# Meeting Assistant Server

Python-сервис транскрибации и суммаризации встреч.

## Запуск из корня monorepo

```bash
make server-install
make server-api
```

`api.py` — текущая FastAPI-точка входа. `main.py` и модули записи временно сохранены как legacy macOS CLI до завершения нативного клиента.

Секреты читаются из `apps/server/.env`. Создайте его из `.env.example`; пример несекретной конфигурации приложения находится в `config.example.json`.
