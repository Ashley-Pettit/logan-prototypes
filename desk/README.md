# My Desk

A simple, free to-do list and quick-links page with two tabs (Work and Personal by default).

**Use it:** https://ashley-pettit.github.io/logan-prototypes/desk/

## Features

- Two tabs you can rename, each with to-dos and a links list
- Group to-dos and links, mark items urgent, tick them off, clear done items
- Settings: your name, initials badge, tagline, tab names, colour and light or dark theme
- Backup and restore to a JSON file, so you can move your list between computers
- Works on phones; add it to your home screen

## Privacy

Everything is saved in your own browser (`localStorage`). Nothing is sent anywhere, and there is no sign-in.
Your list doesn't sync between devices or browsers. Use **Settings > Save backup file** to move it.

## Make a copy for someone

Each copy has a `PRESET` block near the top of the script in `index.html`. Change it to set the name, tagline, tab names, colour and starter examples.
Give each copy its own `id` so copies on the same site keep separate lists.

Example: a copy set up for Anna, live at https://ashley-pettit.github.io/logan-prototypes/desk/anna/

## Tests

End-to-end tests cover adding, ticking, urgent flags, removing, links (including unsafe addresses), filtering, tabs, settings, dark mode, backup and restore, delete everything, blocked storage, two open tabs, and the Anna copy. They run on desktop and on iPhone SE, 15, 16 Pro Max and 15 landscape screen profiles.

```bash
npm i -D playwright && npx playwright install chromium
node tests/e2e.js
```

## Run it yourself

It's one HTML file with no build step. Open `index.html` in a browser, or host the folder on GitHub Pages or any static host.

## Licence

MIT
