# 08 · Running Nitro on Windows, macOS and Linux

Nitro is plain Node.js with no build step and no native modules of its own, so the same commands work on all three. CI runs the type check and all tests on **Ubuntu, Windows and macOS** with Node 22 on every push ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)).

## Requirements

| | Windows 10/11 | macOS 13+ | Linux (Ubuntu 22.04+ or similar) |
| --- | --- | --- | --- |
| Node.js 22+ | Installer from nodejs.org, or `winget install OpenJS.NodeJS.LTS` | Installer, or `brew install node@22` | Your package manager, or nvm |
| Git | Git for Windows | Xcode command line tools or `brew install git` | Your package manager |
| Browser for the agents | `npx playwright install chromium`, or an installed Chrome via `CHROMIUM_PATH` | Same | Same; on a fresh server also `npx playwright install-deps chromium` |
| Browser to view the app | Chrome or Edge (recommended), Firefox 121+, Safari 17+ | | |

## Install and run (every platform)

```bash
git clone https://github.com/manishpaul26/digithon-2026.git
cd digithon-2026
npm install
npx playwright install chromium
npm start            # then open http://localhost:3000
npm test             # 60+ tests, no browser or key needed
```

The npm scripts use no shell features (no `&&`, quotes or environment prefixes), so they behave the same in PowerShell, Command Prompt, bash and zsh.

## Settings: use the `.env` file

The simplest way to set options on any platform is a `.env` file in the project folder (copy `.env.example`). It is git-ignored. If you prefer environment variables, the syntax differs by shell:

| Shell | Example |
| --- | --- |
| PowerShell | `$env:PORT = "3001"; npm start` |
| Command Prompt | `set PORT=3001` then `npm start` |
| bash, zsh (macOS, Linux, Git Bash) | `PORT=3001 npm start` |

## Using an installed Chrome instead of downloading one

On a locked-down or corporate laptop where `npx playwright install` is blocked, point Nitro at a browser that is already installed:

| OS | Typical `CHROMIUM_PATH` |
| --- | --- |
| Windows | `C:\Program Files\Google\Chrome\Application\chrome.exe` or `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` |
| macOS | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` |
| Linux | `/usr/bin/google-chrome` or `/usr/bin/chromium` |

Without `CHROMIUM_PATH`, Nitro first tries Playwright's own browser, then the newest Chromium in Playwright's cache folder for the platform (`%LOCALAPPDATA%\ms-playwright` on Windows, `~/Library/Caches/ms-playwright` on macOS, `~/.cache/ms-playwright` on Linux, or `PLAYWRIGHT_BROWSERS_PATH` when set). See `playwrightCacheDirs` in [`src/tools/browser.ts`](../src/tools/browser.ts).

## Restricted laptops (no admin rights, no API access, strict proxy)

- **No admin rights:** Node.js can be installed per user (the Windows installer's "just for me" option, the macOS `.pkg` into your home folder, or nvm/fnm on any OS). Nothing in Nitro needs admin rights; the server listens on 127.0.0.1 only, so Windows does not ask to open the firewall.
- **No model access:** leave `ANTHROPIC_API_KEY` empty. The app runs in offline mode with rule-based fallbacks, and the measurements stay real.
- **No internet for the target site, or a proxy that breaks TLS:** use **Replay**. Saved runs in `runs/` replay with no browser, model or network, so the full demo works anywhere.

## Line endings and paths

- `.gitattributes` keeps text files in LF, so diffs look the same on Windows.
- Code builds every path with `path.join` or `fileURLToPath`, never by joining strings with `/`, so paths work with Windows drive letters.
- Run folders and file names use only letters, digits, `-`, `_` and `.`, which are valid on every file system.

## Known platform differences

- Lighthouse (the Speed Tester) needs a local Chrome or Chromium; when it cannot start, the Speed Tester falls back to Playwright timings and says so in the feed (`NITRO_LIGHTHOUSE=0` forces this).
- The presentation's animations are built and checked in Chromium. Firefox and Safari show the same content; a few transitions are simpler.
- LibreOffice is only needed to render the PowerPoint to images for review, never to run the app.
