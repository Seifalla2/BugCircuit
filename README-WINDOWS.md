# BugCircuit on a Windows laptop — no terminal required

**One-time setup**

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/) if you do not already have it. Select **Add Python to PATH**.
2. In **GitHub Desktop**, choose **File → Clone repository → GitHub.com → Seifalla2/BugCircuit**. Select a local folder, then **Clone**. Keep the repo private.
3. In GitHub Desktop choose **Repository → Show in Explorer** and double-click **`Start BugCircuit.cmd`**. On the first launch it creates an isolated `.venv` and installs the Python dependencies, then opens your browser automatically.
4. Your dashboard is **http://127.0.0.1:8765/**. Bookmark the address. Keep the small server window open while using it.

**Afterwards:** Use `Open BugCircuit.cmd` to open the page while the server is already running. To start the server after a restart, double-click `Start BugCircuit.cmd` once.

**Updates:** GitHub Desktop → **Fetch origin** → **Pull origin** when available. The source folder is editable-installed into `.venv`, so normal Python code/UI updates are automatically used at the next start. If dependencies change, delete `.venv/bugcircuit-web-v0.4.ready` to reinstall on next launch (or follow a future documented versioned marker).

**Security:** The server listens on **127.0.0.1** only, not the laptop's public or LAN IP. You cannot open this localhost URL from another device. A public link requires a separate authenticated, secured tunnel; do **not** forward port 8765 directly through your router. Only inspect websites you're authorized to test.

**Storage:** Original JSON/HAR uploads are parsed in memory and are not written to disk. Sanitized reports are stored in `%LOCALAPPDATA%\BugCircuit\reports` outside your GitHub clone. Reports can still contain sensitive metadata and should be reviewed before sharing. No analytics or cloud services are used. The active HTTP inspection feature makes limited GET requests directly from the laptop, by your explicit action.

**Optional dev/CLI:** `bugcircuit serve --open` starts the same local web server, and the original CLI diagnostic commands remain intact.
