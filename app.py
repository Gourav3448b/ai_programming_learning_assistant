"""Flask application for CodeSathi, an AI-based programming learning assistant."""

from __future__ import annotations

import os
import secrets
import sys
import threading
from copy import deepcopy
from typing import Any

import bleach
import markdown
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from markupsafe import Markup

from gemini_service import GeminiServiceError, call_gemini
from tutor_engine import APP_NAME, build_prompt, parse_quiz_json

load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
LANGUAGES = ["Python", "C++", "C", "Java", "JavaScript", "SQL", "C#", "Other / not sure"]
LEVELS = ["Beginner", "Intermediate", "Advanced"]
LEARNING_STYLES = [
    "Hint-first (help me reason it out)",
    "Explain step by step",
    "Direct and practical",
    "Exam preparation",
]

DEFAULT_STATE: dict[str, Any] = {
    "profile": {
        "level": "Beginner",
        "language": "Python",
        "learning_style": LEARNING_STYLES[0],
    },
    "api_key_override": "",
    "model_name": DEFAULT_MODEL,
    "chat_messages": [],
    "quiz_data": None,
    "quiz_answers": {},
    "quiz_graded": False,
    "quiz_id": "",
    "quiz_raw_response": None,
    "roadmap_output": None,
    "outputs": {},
}

# The cookie contains only a random session identifier. Learner data and any
# session-only Gemini key stay in this process rather than in the browser cookie.
SESSION_STORE: dict[str, dict[str, Any]] = {}
SESSION_LOCK = threading.RLock()


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0").lower() in {"1", "true", "yes"},
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    def get_state() -> dict[str, Any]:
        sid = session.get("sid")
        if not sid:
            sid = secrets.token_urlsafe(24)
            session["sid"] = sid
        with SESSION_LOCK:
            if sid not in SESSION_STORE:
                SESSION_STORE[sid] = deepcopy(DEFAULT_STATE)
            return SESSION_STORE[sid]

    def api_key_for(state: dict[str, Any]) -> str:
        return (state.get("api_key_override") or os.getenv("GEMINI_API_KEY", "")).strip()

    def model_for(state: dict[str, Any]) -> str:
        return (state.get("model_name") or DEFAULT_MODEL).strip() or DEFAULT_MODEL

    def markdown_to_safe_html(content: str) -> Markup:
        rendered = markdown.markdown(
            content or "",
            extensions=["fenced_code", "tables", "nl2br"],
            output_format="html5",
        )
        allowed_tags = {
            "a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3", "h4",
            "hr", "li", "ol", "p", "pre", "strong", "table", "tbody", "td", "th",
            "thead", "tr", "ul",
        }
        safe_html = bleach.clean(
            rendered,
            tags=allowed_tags,
            attributes={"a": ["href", "title"], "code": ["class"]},
            protocols={"http", "https", "mailto"},
            strip=True,
        )
        return Markup(safe_html)

    def render_page(template: str, active_page: str, **context: Any):
        state = get_state()
        profile = state["profile"]
        return render_template(
            template,
            app_name=APP_NAME,
            active_page=active_page,
            level=profile["level"],
            language=profile["language"],
            learning_style=profile["learning_style"],
            languages=LANGUAGES,
            levels=LEVELS,
            learning_styles=LEARNING_STYLES,
            api_key_is_set=bool(api_key_for(state)),
            current_model=model_for(state),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            **context,
        )

    def run_ai(
        state: dict[str, Any],
        prompt: str,
        *,
        json_mode: bool = False,
        temperature: float = 0.45,
        max_output_tokens: int = 4096,
    ) -> str | None:
        api_key = api_key_for(state)
        if not api_key:
            flash("Add your Gemini API key in the settings panel or in your .env file first.", "error")
            return None
        try:
            return call_gemini(
                prompt,
                api_key=api_key,
                model=model_for(state),
                json_mode=json_mode,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except GeminiServiceError as exc:
            flash(str(exc), "error")
            lowered = str(exc).lower()
            if any(token in lowered for token in ("api key", "unauthenticated", "permission_denied", "403")):
                flash("Check that your Gemini API key is valid and that the Gemini API is enabled for its project.", "info")
            elif any(token in lowered for token in ("429", "resource_exhausted", "quota", "rate limit")):
                flash("You may have reached a usage limit. Check your Gemini API usage and try again later.", "info")
            elif "404" in lowered or "not found" in lowered or "model" in lowered:
                flash(f"Check the configured model name ({model_for(state)}). You can change it in settings.", "info")
            elif "timeout" in lowered or "unavailable" in lowered or "503" in lowered:
                flash("Gemini may be temporarily unavailable. Please retry in a moment.", "info")
            return None
        except Exception as exc:  # Defensive fallback for unexpected SDK errors.
            flash(f"Gemini request failed: {exc}", "error")
            return None

    def build_for_state(task: str, user_input: str, state: dict[str, Any], history=None) -> str:
        profile = state["profile"]
        return build_prompt(
            task,
            user_input,
            history=history,
            learner_level=profile["level"],
            language=profile["language"],
            learning_style=profile["learning_style"],
        )

    @app.context_processor
    def inject_navigation():
        return {
            "navigation": [
                ("home", "Home", "⌂", "index"),
                ("chat", "AI Tutor Chat", "◌", "chat"),
                ("explain", "Explain a Concept", "✳", "explain"),
                ("debug", "Debug Code", "⌘", "debug"),
                ("hints", "Step-by-Step Hint", "↗", "hints"),
                ("quiz", "Quiz Lab", "✓", "quiz"),
                ("roadmap", "Learning Roadmap", "▤", "roadmap"),
            ]
        }

    @app.get("/")
    def index():
        state = get_state()
        return render_page("index.html", "home", state=state)

    @app.route("/settings", methods=["POST"])
    def settings():
        state = get_state()
        state["profile"] = {
            "level": request.form.get("level", "Beginner"),
            "language": request.form.get("language", "Python"),
            "learning_style": request.form.get("learning_style", LEARNING_STYLES[0]),
        }
        if state["profile"]["level"] not in LEVELS:
            state["profile"]["level"] = "Beginner"
        if state["profile"]["language"] not in LANGUAGES:
            state["profile"]["language"] = "Python"
        if state["profile"]["learning_style"] not in LEARNING_STYLES:
            state["profile"]["learning_style"] = LEARNING_STYLES[0]
        state["model_name"] = request.form.get("model_name", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        new_key = request.form.get("api_key", "").strip()
        if new_key:
            state["api_key_override"] = new_key
        if request.form.get("clear_api_key") == "1":
            state["api_key_override"] = ""
        flash("Settings saved for this browser session.", "success")
        destination = request.form.get("next", "/")
        safe_destinations = {
            "/": url_for("index"),
            "/chat": url_for("chat"),
            "/explain": url_for("explain"),
            "/debug": url_for("debug"),
            "/hints": url_for("hints"),
            "/quiz": url_for("quiz"),
            "/roadmap": url_for("roadmap"),
        }
        return redirect(safe_destinations.get(destination, url_for("index")))

    @app.route("/chat", methods=["GET", "POST"])
    def chat():
        state = get_state()
        if request.method == "POST":
            action = request.form.get("action", "send")
            if action == "clear":
                state["chat_messages"] = []
                flash("Chat history cleared.", "success")
            else:
                question = request.form.get("question", "").strip()
                if not question:
                    flash("Type a question before sending.", "error")
                else:
                    history = list(state["chat_messages"])
                    prompt = build_for_state(
                        "Act as a conversational programming tutor. Answer the learner's question and keep the explanation at the right level. For debugging or algorithm problems, explain the reasoning and use a small dry run when helpful. Follow the selected teaching style.",
                        question,
                        state,
                        history=history,
                    )
                    answer = run_ai(state, prompt)
                    if answer:
                        state["chat_messages"].extend(
                            [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
                        )
            return redirect(url_for("chat"))

        messages = [
            {"role": item["role"], "content": item["content"], "html": markdown_to_safe_html(item["content"]) if item["role"] == "assistant" else None}
            for item in state["chat_messages"]
        ]
        return render_page("chat.html", "chat", messages=messages)

    @app.route("/explain", methods=["GET", "POST"])
    def explain():
        state = get_state()
        if request.method == "POST":
            topic = request.form.get("topic", "").strip()
            familiarity = request.form.get("familiarity", "Brand new")
            include_example = request.form.get("include_example") == "on"
            if not topic:
                flash("Enter a concept first.", "error")
            else:
                language = state["profile"]["language"]
                task = (
                    f"Explain the concept '{topic}'. The learner's familiarity is: {familiarity}. Programming language: {language}. "
                    "Include: (1) a plain-English definition, (2) why it matters, (3) an analogy, (4) a step-by-step explanation, "
                    "(5) common mistakes, and (6) three quick self-check questions. "
                    f"{'Include a small worked code example.' if include_example else 'Avoid a long code example; focus on intuition.'} "
                    "End with one small practice task without immediately giving its answer."
                )
                prompt = build_for_state(task, f"Please teach me: {topic}", state)
                result = run_ai(state, prompt, temperature=0.4)
                if result:
                    state["outputs"]["explain"] = {"title": f"Let's learn: {topic}", "content": result}
            return redirect(url_for("explain"))
        output = state["outputs"].get("explain")
        return render_page("explain.html", "explain", output=output, output_html=markdown_to_safe_html(output["content"]) if output else None)

    @app.route("/debug", methods=["GET", "POST"])
    def debug():
        state = get_state()
        if request.method == "POST":
            code = request.form.get("code", "")
            error = request.form.get("error", "").strip()
            expected = request.form.get("expected", "").strip()
            debug_mode = request.form.get("debug_mode", "Explain the bug first")
            if not code.strip():
                flash("Paste some code first.", "error")
            else:
                language = state["profile"]["language"]
                extra_instruction = (
                    "Then provide a minimal corrected version and explain the changes."
                    if debug_mode == "Show a corrected version too"
                    else "Do not rewrite the whole program unless a small fix cannot be demonstrated."
                    if debug_mode == "Explain the bug first"
                    else "Also discuss relevant edge cases, time complexity, and space complexity."
                )
                task = f"""Debug and teach from the supplied code.
Language: {language}. Selected approach: {debug_mode}. Learner level: {state['profile']['level']}.
Expected behavior: {expected or '(not provided)'}.
Error/actual output: {error or '(not provided)'}.
First identify the most likely cause and quote the relevant line or pattern. Explain why it behaves that way with a concise dry run if useful. {extra_instruction}
Do not claim to have executed the code. If the error cannot be determined, list the top likely causes and ask for the missing detail.

CODE:
```{language}
{code}
```"""
                prompt = build_for_state(task, "Help me understand and fix this issue.", state)
                result = run_ai(state, prompt, temperature=0.25)
                if result:
                    state["outputs"]["debug"] = {"title": "Debugging analysis", "content": result}
            return redirect(url_for("debug"))
        output = state["outputs"].get("debug")
        return render_page("debug.html", "debug", output=output, output_html=markdown_to_safe_html(output["content"]) if output else None)

    @app.route("/hints", methods=["GET", "POST"])
    def hints():
        state = get_state()
        if request.method == "POST":
            problem = request.form.get("problem", "").strip()
            attempt = request.form.get("attempt", "").strip()
            hint_strength = request.form.get("hint_strength", "Useful hint")
            if not problem:
                flash("Add the problem statement first.", "error")
            else:
                instructions = {
                    "Tiny nudge": "Give one small clue only. Do not reveal the algorithm or code. End with a guiding question.",
                    "Useful hint": "Give one or two targeted hints, point to the key observation, and stop before providing the full solution.",
                    "Detailed approach": "Explain the algorithmic idea and a small dry run, but do not provide the complete implementation.",
                    "Full explanation": "Give a complete explanation, correctness reasoning, complexity, and an illustrative implementation in the selected language.",
                }
                if hint_strength not in instructions:
                    hint_strength = "Useful hint"
                language = state["profile"]["language"]
                task = (
                    f"Help the learner solve the programming problem. Language: {language}. Learner level: {state['profile']['level']}. "
                    f"Help preference: {hint_strength}. {instructions[hint_strength]} Use their attempt when provided, and do not repeat approaches they have already disproved. "
                    f"Problem:\n{problem}\n\nCurrent attempt:\n{attempt or '(No attempt provided yet.)'}"
                )
                prompt = build_for_state(task, "Help me take the next step.", state)
                result = run_ai(state, prompt, temperature=0.35)
                if result:
                    state["outputs"]["hints"] = {"title": f"Your hint · {hint_strength}", "content": result}
            return redirect(url_for("hints"))
        output = state["outputs"].get("hints")
        return render_page("hints.html", "hints", output=output, output_html=markdown_to_safe_html(output["content"]) if output else None)

    @app.route("/quiz", methods=["GET", "POST"])
    def quiz():
        state = get_state()
        if request.method == "POST":
            action = request.form.get("action", "generate")
            if action == "grade":
                quiz_data = state.get("quiz_data")
                if quiz_data:
                    answers = {}
                    for index in range(len(quiz_data["questions"])):
                        selected = request.form.get(f"answer_{index}", "")
                        answers[str(index)] = selected if selected in {"A", "B", "C", "D"} else ""
                    state["quiz_answers"] = answers
                    state["quiz_graded"] = True
                return redirect(url_for("quiz"))

            topic = request.form.get("quiz_topic", "").strip()
            try:
                quiz_count = max(3, min(10, int(request.form.get("quiz_count", "5"))))
            except ValueError:
                quiz_count = 5
            difficulty = request.form.get("quiz_difficulty", "Medium")
            scope = request.form.get("quiz_scope", "").strip()
            if not topic:
                flash("Enter a topic first.", "error")
            else:
                language = state["profile"]["language"]
                quiz_prompt = f"""Create exactly {quiz_count} original multiple-choice programming-learning questions on: {topic}.
Language: {language}. Difficulty: {difficulty}. Learner level: {state['profile']['level']}. Extra scope: {scope or 'Cover the core topic and common misconceptions'}.
Return ONLY a valid JSON object with this schema:
{{"questions":[{{"question":"question text","options":{{"A":"option","B":"option","C":"option","D":"option"}},"answer":"A","explanation":"short explanation"}}]}}
Rules: one unambiguously correct answer per question; exactly four options A/B/C/D; answer must be one letter A-D; explanations should teach the concept; do not use markdown fences or add text outside JSON; do not include trick wording that depends on unstated assumptions."""
                raw = run_ai(state, quiz_prompt, json_mode=True, temperature=0.25, max_output_tokens=6000)
                if raw:
                    try:
                        questions = parse_quiz_json(raw)
                        state["quiz_data"] = {"topic": topic, "difficulty": difficulty, "questions": questions}
                        state["quiz_answers"] = {}
                        state["quiz_graded"] = False
                        state["quiz_id"] = secrets.token_hex(4)
                        state["quiz_raw_response"] = None
                        if len(questions) != quiz_count:
                            flash(f"The model returned {len(questions)} valid questions instead of {quiz_count}; you can still use this quiz.", "info")
                    except ValueError as exc:
                        state["quiz_raw_response"] = raw
                        flash(str(exc), "error")
            return redirect(url_for("quiz"))

        quiz_data = state.get("quiz_data")
        score = None
        if quiz_data and state.get("quiz_graded"):
            answers = state.get("quiz_answers", {})
            score = sum(answers.get(str(i), "") == question["answer"] for i, question in enumerate(quiz_data["questions"]))
        return render_page(
            "quiz.html", "quiz", quiz_data=quiz_data,
            quiz_answers=state.get("quiz_answers", {}), quiz_graded=state.get("quiz_graded", False), score=score,
            quiz_raw_response=state.get("quiz_raw_response"),
        )

    @app.post("/quiz/reset")
    def quiz_reset():
        state = get_state()
        state["quiz_data"] = None
        state["quiz_answers"] = {}
        state["quiz_graded"] = False
        state["quiz_id"] = ""
        state["quiz_raw_response"] = None
        flash("Quiz cleared. Generate another when you are ready.", "success")
        return redirect(url_for("quiz"))

    @app.route("/roadmap", methods=["GET", "POST"])
    def roadmap():
        state = get_state()
        if request.method == "POST":
            goal = request.form.get("goal", "").strip()
            duration = request.form.get("duration", "1 month")
            try:
                hours = max(1, min(30, int(request.form.get("hours", "7"))))
            except ValueError:
                hours = 7
            current_knowledge = request.form.get("current_knowledge", "").strip()
            constraints = request.form.get("constraints", "").strip()
            if not goal:
                flash("Enter your learning goal first.", "error")
            else:
                language = state["profile"]["language"]
                task = (
                    f"Design a practical learning roadmap for this goal: {goal}. Time horizon: {duration}. Available time: about {hours} hours each week. "
                    f"Learner level: {state['profile']['level']}. Preferred programming language: {language}. Current knowledge: {current_knowledge or 'Not specified'}. "
                    f"Constraints: {constraints or 'None specified'}. Include: prerequisites, weekly milestones, a repeatable study rhythm that fits the time budget, "
                    "hands-on exercises, a small portfolio/project outcome, checkpoints to verify learning, and what to skip for now. "
                    "Make the workload realistic and clearly label optional work. Use a table where useful."
                )
                prompt = build_for_state(task, "Create my learning roadmap.", state)
                result = run_ai(state, prompt, temperature=0.4, max_output_tokens=5000)
                if result:
                    state["roadmap_output"] = result
            return redirect(url_for("roadmap"))
        output = state.get("roadmap_output")
        return render_page("roadmap.html", "roadmap", output=output, output_html=markdown_to_safe_html(output) if output else None)

    @app.errorhandler(413)
    def request_too_large(_error):
        flash("That submission is too large. Please shorten the code or text and try again.", "error")
        return redirect(request.referrer or url_for("index"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
