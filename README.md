# Moul El Hanout 🛒🇲🇦

A fully playable, bilingual (Arabic & French) web game running locally entirely in the browser using HTML/CSS and **Brython** (Python).

## Features
- 🇲🇦 **Bilingual**: Instant switching between Arabic (RTL) and French (LTR).
- 🐍 **Python Powered**: Core logic runs via Brython in `main.py`.
- 🧠 **Mental Math**: Serve customers by quickly calculating change or multiplication.
- 🦹 **Thief Events**: Click the thief quickly and answer math to protect your Hanout!
- 💾 **Auto-Save**: Uses `localStorage` to save your money and stock.

## How to Play Locally
Since the project uses an XHR request to load the `.json` language files, opening `index.html` directly from the file system (`file:///...`) will cause a CORS error in modern browsers.

To play locally, serve the directory via Python:
```bash
python -m http.server 8000
```
Then open your browser to: `http://localhost:8000`

## Deployment

### Deploy to Vercel (Free)
1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in this directory.
3. Accept the default static project settings.

### Deploy to Netlify (Free)
1. Install Netlify CLI: `npm i -g netlify-cli`
2. Run `netlify deploy` in this directory.
3. Select the folder `.` as the publish directory.

## Credits
Game concept: Hicham Hiri
Developed with ❤️
