# CodeSathi — AI-Based Programming Learning Assistant Using LLMs

CodeSathi is a Flask web application that uses Google's Gemini API to help learners understand programming concepts, debug code, practice problem-solving, and create a study plan.

The project uses a separated structure:

- **Flask** for Python routes and backend logic.
- **Jinja2 templates** for HTML pages in `templates/`.
- **CSS** for the interface in `static/css/`.
- **JavaScript** for small browser interactions in `static/js/`.
- **Google Gen AI Python SDK** for Gemini requests.

## Features

All six original learning workspaces are retained:

1. **AI Tutor Chat:** Ask follow-up questions with recent conversation context retained for the current browser session.
2. **Explain a Concept:** Learn a topic with a plain-English definition, analogy, example, common mistakes, and practice questions.
3. **Debug Code:** Share code, actual output/errors, and expected behavior to receive a diagnosis and suggested fix.
4. **Step-by-Step Hint:** Choose how much help to receive, from a tiny nudge to a full explanation.
5. **Quiz Lab:** Generate multiple-choice quizzes, submit answers, see your score, and review explanations.
6. **Learning Roadmap:** Build a week-by-week plan based on your goal, available time, current knowledge, and constraints.

Other retained capabilities include configurable learner level, programming language, teaching style, Gemini model, and a session-only API key override. The interface has been redesigned with a minimal, responsive layout.

> **Privacy and safety:** Prompts and code entered in the app are sent to Google's Gemini API. Do not paste passwords, API secrets, or confidential source code. The application does not execute submitted code. Session-only API-key overrides are held in the Flask server process and are not stored in browser cookies or project files.

## Requirements

- Python 3.11 or newer (Python 3.13 is suitable)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- Internet access for Gemini requests and first-time dependency installation

## Windows setup (recommended)

1. Extract the ZIP file.
2. Open the extracted `ai_programming_learning_assistant` folder in VS Code.
3. Open the VS Code terminal and create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run `\.venv\Scripts\activate.bat`, or use `.venv\Scripts\python.exe` directly for commands.

4. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and open `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

   Set the Gemini key and (optionally) a long random Flask secret:

   ```text
   GEMINI_API_KEY=your_real_key_here
   GEMINI_MODEL=gemini-3.8-flash
   FLASK_SECRET_KEY=your_long_random_secret
   ```

   Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey). Keep `.env` private and do not commit or share it.

6. Start the Flask app:

   ```powershell
   python app.py
   ```

7. Open **http://127.0.0.1:5000** in your browser.

### One-click helper for Windows

Run `run_windows.bat`. It creates a virtual environment if needed, installs dependencies, and starts Flask. On first run, it creates `.env` and opens it so you can add your Gemini key. Run the file again after saving the key.

## macOS / Linux setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Gemini API key.
python app.py
```

Or run `./run_unix.sh` to create the environment and install dependencies.

## Using CodeSathi

1. Start Flask and open `http://127.0.0.1:5000`.
2. Expand **Learning settings** in the left sidebar.
3. Set your level, main language, and preferred teaching style.
4. Add a session-only API key in settings, or configure `GEMINI_API_KEY` in `.env`.
5. Open one of the six workspaces and submit your topic, code, problem, quiz request, or learning goal.

A session-only key entered in the settings panel is stored in the running Flask server's memory for that browser session. It is not written to `.env` or the browser cookie. A key supplied through `.env` is read from the environment when the app starts.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API credential | Not set |
| `GEMINI_MODEL` | Gemini model ID | `gemini-3.8-flash` |
| `FLASK_SECRET_KEY` | Signs Flask session cookies | Random per app process if omitted |
| `COOKIE_SECURE` | Mark cookies Secure (HTTPS only) | `0` |
| `PORT` | Local Flask port | `5000` |
| `FLASK_DEBUG` | Enable Flask debug mode | `0` |

The Gemini model is configurable because model availability can depend on the Google project and API key. If the configured model is unavailable, choose a currently enabled model in the sidebar or update `GEMINI_MODEL` in `.env`, then restart the app. The app defaults to `gemini-3.8-flash`, which is used in Google's current Gemini API examples at the time this project was prepared.

For a local demo, the built-in Flask development server is sufficient. Before deploying publicly, use a production WSGI server, configure a stable `FLASK_SECRET_KEY`, enable HTTPS and `COOKIE_SECURE=1`, and add suitable CSRF protection and persistent session storage. Session state (including session-only API-key overrides) is held in process memory, so it is cleared when the server restarts and is not shared between multiple worker processes.

## Project structure

```text
ai_programming_learning_assistant/
├── app.py                         # Flask app factory, routes, state, and page handlers
├── gemini_service.py               # Google Gen AI SDK wrapper
├── tutor_engine.py                 # Prompt construction and quiz response validation
├── requirements.txt                # Python dependencies
├── .env.example                    # Safe environment-variable template
├── .gitignore                      # Excludes .env and generated files
├── run_windows.bat                 # Windows setup/launch helper
├── run_unix.sh                     # macOS/Linux setup/launch helper
├── templates/                      # Jinja2 HTML pages
│   ├── base.html                   # Shared shell, navigation, and settings
│   ├── index.html                  # Home dashboard
│   ├── chat.html                   # AI Tutor Chat
│   ├── explain.html                # Concept explainer
│   ├── debug.html                  # Code debugging
│   ├── hints.html                  # Step-by-step hints
│   ├── quiz.html                   # Quiz generation and grading
│   ├── roadmap.html                # Learning roadmap
│   └── _output.html                # Shared AI output component
├── static/
│   ├── css/styles.css              # Minimal responsive UI styles
│   └── js/app.js                   # Browser interactions
└── tests/
    ├── test_tutor_engine.py        # Offline prompt and quiz parsing tests
    └── test_flask_app.py           # Flask route and template smoke tests
```

## Run tests

The tests do not call Gemini and do not require an API key. After installing the project dependencies, run:

```bash
python -m unittest discover -s tests -v
```

Syntax-check the Python files with:

```bash
python -m py_compile app.py gemini_service.py tutor_engine.py
```

## How it works

- Flask renders the pages from the `templates/` directory and serves CSS/JavaScript from `static/`.
- The browser submits form data to Flask routes.
- Flask builds a task-specific prompt using `tutor_engine.py` and passes it to `gemini_service.py`.
- The Google Gen AI Python SDK sends the prompt to the selected Gemini model.
- Markdown responses are rendered and sanitized before appearing in the page.
- Quiz mode requests JSON and validates each question before rendering answer choices and calculating the score.
- Submitted source code is analyzed as text only; CodeSathi does not execute it.

## Troubleshooting

- **Invalid API key / permission error:** Verify the key in `.env`, confirm the Gemini API is enabled for the Google project, and restart the app after editing `.env`.
- **Quota or rate-limit error:** Check API usage and limits in Google AI Studio. Wait or adjust usage as appropriate.
- **Model not found:** Set `GEMINI_MODEL` to a model currently enabled for your API key, or change the model in the sidebar settings.
- **`ModuleNotFoundError: flask` or another package:** Activate the correct virtual environment and run `pip install -r requirements.txt` again.
- **Port already in use:** Change `PORT=5001` in `.env` and restart Flask, then visit `http://127.0.0.1:5001`.
- **Settings lost after restart:** Session-only settings are stored in memory. Add the Gemini key and default model to `.env` if you want them loaded each time the app starts.

## References

- [Gemini API documentation](https://ai.google.dev/gemini-api/docs)
- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
- [Flask documentation](https://flask.palletsprojects.com/)
- [Jinja documentation](https://jinja.palletsprojects.com/)
