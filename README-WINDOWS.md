# BugCircuit on Windows — one-click local dashboard + safe automatic updates

## One-time setup

1. Install Python 3.10+ and sign in to **GitHub Desktop**.
2. In GitHub Desktop, clone the private `Seifalla2/BugCircuit` repository.
3. Choose **Repository → Show in Explorer**. Double-click **`Start BugCircuit.cmd`**.
4. The setup uses a local `.venv`, then opens `http://127.0.0.1:8765/` in your browser. Leave the little server window open, or run **`Enable Auto-start.cmd`** once to launch it at Windows sign-in.

## Important one-time transition from v0.4.0

If you're currently running BugCircuit v0.4.0, the old launcher **does not** contain auto-update support. In GitHub Desktop, click **Fetch origin → Pull origin** **one last time**, close the current BugCircuit server window, and double-click the newly updated `Start BugCircuit.cmd` to activate automatic updates.

## How updates work after that

- The local supervisor checks GitHub `main` every **five minutes** while BugCircuit is running, and performs an **ordinary fast-forward update only**. The server restarts if a new commit is installed. Normal Python and frontend changes require no manual reinstall. Dependency changes trigger `pip install -e .`.
- **Settings & safety → GitHub auto-updates** displays status, current commit and last check. Click **Check for updates now** if you don't want to wait. The browser automatically reloads after detecting a new app version when it's safe to do so (not during a new analysis or on a report screen).
- The updater **never** uses `git reset --hard`, force-push, rebase, or writes to unrelated repositories. It pauses when the local Git checkout has tracked modifications, `main` diverges, `origin` points somewhere unexpected, or access to the private GitHub repo is unavailable.
- GitHub Desktop is the fallback if the private repository requires login or Git isn't found. The Git executable is detected from Git PATH, common Windows installs, or GitHub Desktop's bundled Git. You may need to authenticate Git separately if private fetch fails. GitHub Desktop itself does **not** push new commits automatically and is not a continuous deployment service.
- If the laptop is off, there is no update process. Next time it starts, it checks again. If the application is closed, just double-click the launcher.
- If update check or dependency installation fails, the local dashboard remains available when possible; see the status in Settings. Don't delete `.venv` or overwrite local changes to fix a sync error.

## Using BugCircuit

- **Overview → Try a demo:** a fully synthetic OAuth error diagnosis, safe to run offline.
- **New analysis → HTTP:** enter an owned or explicitly authorized public website URL, check the authorization box, then Analyze. Current live scan checks limited HTTP GET responses only; it does not crawl the entire website.
- **New analysis → HAR:** capture a browser HAR using Developer Tools → Network → Export HAR, then upload it locally. HAR exports may contain secrets—remove them before sharing anywhere.
- **New analysis → Workflow / OTel:** import compatible JSON execution or OpenTelemetry exports. Examples are in `examples/`. Not a direct n8n account integration yet.
- **Reports:** inspect findings with evidence IDs, suggested verification steps, event timeline, HTML export and JSON download. Findings are evidence-backed indicators, **not guaranteed root causes**.
- **Settings & safety:** local server and GitHub update status. You can switch to Arabic from the top-right button.

## Privacy and safety

Reports are stored under `%LOCALAPPDATA%\BugCircuit\reports`, outside the GitHub checkout. Your original uploaded files are processed in memory and not saved as raw uploads. Update checks contact **GitHub**, but do not upload report contents. HTTP scans contact the website explicitly selected by you. The dashboard listens on **127.0.0.1** only; it is not reachable from other devices or the public internet. Never forward port 8765 to the internet without an authenticated, reviewed access layer.

**Troubleshooting:** If **Settings** says `Git not found`, install Git for Windows (or use Desktop for manual updates). If it says `GitHub not reachable or private login required`, use GitHub Desktop to sign in, Fetch/Pull, and restart BugCircuit if needed. If it says `Local changes`, review them in GitHub Desktop; no files are overwritten automatically.
