# Infrastructure

Текущий Compose запускает существующий API и локальный HTTP reverse proxy. PostgreSQL, Redis, worker и production HTTPS будут добавлены вместе с фоновой моделью встреч; до этого момента конфигурация не заявляет несуществующие зависимости.

Для production замените `:80` в `Caddyfile` на доменное имя — Caddy автоматически выпустит TLS-сертификат.
