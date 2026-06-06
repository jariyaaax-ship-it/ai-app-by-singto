# Gemising

PySide6 chat app for Windows and Linux using the Gemini API with `gemini-3.1-flash-lite`.

## Features

- API key settings screen
- Local chat history persistence
- Background Gemini requests so the UI stays responsive

## Run

```bash
python3 app.py
```

## Storage

- Windows settings: `%APPDATA%/Gemising/Config/settings.json`
- Windows history: `%LOCALAPPDATA%/Gemising/Data/chat_history.json`
- Linux settings: `~/.config/Gemising/settings.json`
- Linux history: `~/.local/share/Gemising/chat_history.json`
