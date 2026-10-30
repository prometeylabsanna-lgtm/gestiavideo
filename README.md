# Gestia Home — coming soon

Статична сторінка «скоро» для Gestia Home: відео-фон, логотип і форма збору e-mail перед стартом продажів святкових боксів.

## Структура

```
.
├── index.html          # розмітка сторінки
├── styles.css          # стилі та адаптив
├── script.js           # форма + обробка video / reduced-motion
├── SPEC.md             # технічна специфікація
├── README.md
├── .gitignore
└── assets/
    ├── img/            # логотип, favicon, OG, роздільники
    └── video/          # bg.mp4, bg.webm, poster.jpg, poster.webp
```

## Локальний запуск

Потрібен лише статичний сервер (через `file://` відео може не грати в деяких браузерах):

```bash
python3 -m http.server
```

Відкрийте у браузері: http://localhost:8000

## Форма e-mail

У `script.js` на початку файлу:

```js
const FORM_ENDPOINT = ""; // TODO: set email collection endpoint (POST JSON {email}). Empty = no backend, only local success message.
```

- Якщо `FORM_ENDPOINT` порожній — запит нікуди не йде, показується локальне повідомлення про успіх. **E-mail зараз ніде не зберігаються.**
- Якщо вказати URL — на submit йде `POST` з JSON `{ "email": "..." }`.

## Ассети

Походження макету: Figma, node `5:1560` («Головна»), файл `dVjiuXFknESrOGvKPX4Wh4`.  
Відео оптимізовано через `ffmpeg` (H.264 / VP9, без звуку).

## Деплой

Будь-який статичний хостинг: GitHub Pages, Netlify, Cloudflare Pages, nginx тощо. Білд-крок не потрібен — достатньо викласти вміст кореня репозиторію.
