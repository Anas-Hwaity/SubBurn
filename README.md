# SubBurn

SubBurn burns subtitles into video and gives you the tools around that job in one desktop app: subtitle styling, RTL text, font fallback, watermarks, transcription, exact previews, encoder selection, progress reporting, and a persistent queue.

Made by **Anas Al Hwaity**  
Telegram: [@ANAS12RM](https://t.me/ANAS12RM)

## Desktop

![SubBurn desktop interface](docs/assets/subburn-desktop-home.png)

## Browser dashboard

![SubBurn browser dashboard](docs/assets/subburn-dashboard.png)

The dashboard controls the same running SubBurn session as the desktop window. It stays on the local machine.

## Run from source

Python 3.10 to 3.13 is supported.

```bash
python SubBurn.py
```

## What it handles

- External and embedded subtitles
- Arabic, Hebrew, Latin, CJK, and mixed-script text
- Subtitle font fallback and glyph checks
- Text and image watermarks
- Local transcription
- Exact frame and short-clip previews
- Hardware and software encoder selection
- FFmpeg discovery and managed fallback
- Saved projects and persistent batch jobs
- Tkinter and browser controls over the same session

A full help manual is built into **Settings** inside the app.

## License

SubBurn is licensed under Apache-2.0. Third-party components keep their own licenses. See `THIRD_PARTY_NOTICES.md`.
