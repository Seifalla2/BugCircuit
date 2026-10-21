# BugCircuit on a Windows laptop — no terminal required

**One-time setup**

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/) if you do not already have it. Select **Add Python to PATH**.
2. In **GitHub Desktop**, choose **File → Clone repository → GitHub.com → Seifalla2/BugCircuit**. Select a local folder, then **Clone**. Keep the repo private.
3. In GitHub Desktop choose **Repository → Show in Explorer** and double-click **`Start BugCircuit.cmd`**. On the first launch it creates an isolated `.venv` and installs the Python dependencies, then opens your browser automatically.
4. Your dashboard is **http://127.0.0.1:8765/**. Bookmark the address. Keep the small server window open while using it.

**Optional:** Double-click `Enable Auto-start.cmd` once to start the server each time you sign in to Windows; `Disable Auto-start.cmd` removes this startup entry.

**Afterwards:** Use `Open BugCircuit.cmd` to open the page while the server is already running. To start the server after a restart, double-click `Start BugCircuit.cmd` once.

**Updates:** GitHub Desktop → **Fetch origin** → **Pull origin** when available. The source folder is editable-installed into `.venv`, so normal Python code/UI updates are automatically used at the next start. If dependencies change, delete `.venv/bugcircuit-web-v0.4.ready` to reinstall on next launch (or follow a future documented versioned marker).

**Security:** The server listens on **127.0.0.1** only, not the laptop's public or LAN IP. You cannot open this localhost URL from another device. A public link requires a separate authenticated, secured tunnel; do **not** forward port 8765 directly through your router. Only inspect websites you're authorized to test.

**Storage:** Original JSON/HAR uploads are parsed in memory and are not written to disk. Sanitized reports are stored in `%LOCALAPPDATA%\BugCircuit\reports` outside your GitHub clone. Reports can still contain sensitive metadata and should be reviewed before sharing. No analytics or cloud services are used. The active HTTP inspection feature makes limited GET requests directly from the laptop, by your explicit action.

**Optional dev/CLI:** `bugcircuit serve --open` starts the same local web server, and the original CLI diagnostic commands remain intact.

## Connect any user's repositories (v0.5)

1. In your browser open **Projects → Local folder** for private GitHub repositories.
2. In GitHub Desktop, clone a repository you own or are authorized to inspect. Use **Repository → Show in Explorer** and copy the clone folder path (the directory containing `.git`), or click **Browse folders…** in BugCircuit to select it.
3. Click **Connect project**, then **Analyze code**. The report appears in **Reports**. The scanner does not run any code from the repository or modify files.
4. For a **public GitHub** repository, select **Public GitHub URL**, paste `https://github.com/owner/repo` and click **Connect project**. BugCircuit clones it into its application data directory (requires Git installed). Private repositories *cannot* be connected merely by pasting a URL; clone them first with GitHub Desktop.
5. Select **Disconnect** to remove a project from BugCircuit's list. Cloned files are **never deleted automatically**, to avoid accidental loss.

**Important:** A GitHub repo is the source code, not necessarily the running website. Repository analysis detects selected code/configuration smells; HTTP/HAR capture separately collects website runtime evidence. Don't assume a 403 from a probe means the site's login is broken: an edge/WAF policy may block automated requests. No changes are pushed to user repositories.

### Optional local AI

Install [Ollama](https://ollama.com/download/windows) on Windows and start it. Install a suitable local model such as [Qwen2.5-Coder 3B](https://ollama.com/library/qwen2.5-coder) via Ollama. In any report, use **Find models**, choose an installed model, then **Explain report**. No API key or cloud account is needed. BugCircuit calls **127.0.0.1:11434 only**, and sends *summaries of findings*, not source files, raw HAR or tokens. Ollama/model installation and local model inference require their own resources; absence of Ollama leaves all deterministic analysis features usable.

**Privacy:** Connecting a local clone grants this single-user, loopback-only BugCircuit process read access to *tracked, selected* files in that clone. Restrict physical access to the laptop and review generated reports before sharing. A repository URL cannot grant access to someone else's private GitHub repository. A tokenless private clone requires that user to authenticate through GitHub Desktop outside BugCircuit.

### One-click model setup (v0.5.1)

After installing and running Ollama, open a saved report in BugCircuit. In **Local AI**, choose either **Qwen Coder 1.5B (~986 MB)** or **Qwen Coder 3B (~1.9 GB)** and click **Install model through Ollama**. Confirm the disk/network notice. The download runs locally via Ollama and the panel displays progress. When complete, choose the installed model in the report and click **Explain report**. This optional download is not started without your click and confirmation; it requires internet access and adequate disk/RAM. There is no silent bundled model download and no command line required after Ollama itself is installed.
