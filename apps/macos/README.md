# Meeting Assistant for macOS

Здесь будет находиться независимый SwiftUI-клиент (`MeetingAssistant.xcodeproj`).

Границы клиента:

- запись системного звука через ScreenCaptureKit и микрофона через AVAudioEngine;
- локальная история и очередь загрузок;
- доступ к серверу только через API из `contracts/openapi.yaml`;
- хранение серверного токена в Keychain;
- отсутствие ключей Deepgram и LLM.

Минимальная поддерживаемая версия — macOS 13.
