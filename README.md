# todoist-reminder-migrate
A utility to migrate Todoist data to Apple Reminders

# todoist_migrate

Small script to copy active Todoist tasks into Apple Reminders.

Usage

- Run once with a token via env:

```bash
export TODOIST_TOKEN="your_token_here"
python3 todoist_migrate.py
```

- Or pass token via CLI (no prompt):

```bash
python3 todoist_migrate.py --token YOUR_TOKEN
```

- Useful flags:
  - `--debug` — print debug dumps of projects/tasks
  - `--dry-run` — don't create reminders; prints what would be done

Example:

```bash
python3 todoist_migrate.py --token "$TODOIST_TOKEN" --debug --dry-run
```

Notes

- The script uses `osascript` to create reminders on macOS.
- If you want to persist the token, set the `TODOIST_TOKEN` environment variable in your shell.
- For debugging, set `TODOIST_MIGRATE_DEBUG=1` or use `--debug`.

**Prerequisites (macOS)**

- **Terminal:** Open the Terminal app (Applications → Utilities → Terminal).
- **Homebrew:** Install Homebrew (a macOS package manager) if you don't have it. In Terminal copy-paste and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

- **Python 3:** Install Python 3 using Homebrew and verify the installation:

```bash
brew install python
python3 --version
pip3 --version
```

- **Virtual environment (recommended for non-programmers):** Use a virtual environment to keep dependencies separate.

```bash
python3 -m venv todoist-venv
source todoist-venv/bin/activate
pip install --upgrade pip
```

- **Install required Python package:** With the virtualenv active (or system Python if you skipped venv), install the Todoist client library:

```bash
pip install todoist-api-python
```

- **Allow access to Reminders:** The script uses AppleScript (`osascript`) to create Reminders. The first time you run the script or run the following command you may be prompted to grant Terminal (or Python) access to Reminders in System Settings/Preferences.

```bash
osascript -e 'tell application "Reminders" to get name of lists'
```

If a permission prompt appears, approve access. If you need to review permissions later, open System Settings → Privacy & Security (or System Preferences → Security & Privacy) → Reminders, and allow access for Terminal (or the app you used).

**Getting your Todoist API token**

- Sign in to Todoist at https://todoist.com and open Settings → Integrations (or Settings → Account → API token). Copy the API token.
- You can either export it into your shell for the current session:

```bash
export TODOIST_TOKEN="your_token_here"
```

or pass it to the script directly with the `--token` flag:

```bash
python3 todoist_migrate.py --token "your_token_here"
```

**Quick example (recommended)**

1. Open Terminal.
2. Create and activate a virtualenv, then install the dependency:

```bash
python3 -m venv todoist-venv
source todoist-venv/bin/activate
pip install --upgrade pip
pip install todoist-api-python
```

3. Run the script with a dry run first (no reminders created):

```bash
python3 todoist_migrate.py --token "YOUR_TOKEN" --debug --dry-run
```

4. If output looks correct, run without `--dry-run` to actually create reminders:

```bash
python3 todoist_migrate.py --token "YOUR_TOKEN"
```
