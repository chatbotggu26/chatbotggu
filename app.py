"""
Production-Ready Multimodal AI Chatbot Backend
Powered by Flask, Flask-Session, Werkzeug, and the official google-genai SDK.
Supports Multi-Session Conversation Memory, History Sidebar, and Multimodal File Uploads.
"""

import os
import time
import random
import uuid
import logging
import mimetypes
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Application Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "ggu-secret-session-key-ai-2026")
# Detect Vercel or Serverless environment (where only /tmp is writable)
IS_VERCEL = bool(os.getenv("VERCEL"))
if IS_VERCEL:
    app.config["SESSION_FILE_DIR"] = "/tmp/flask_session"
    app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
else:
    app.config["SESSION_FILE_DIR"] = os.path.join(app.root_path, "flask_session")
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB max file size

# Ensure upload and session directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

# Initialize Server-Side Session
Session(app)

# Allowed file upload extensions (multimodal: images, documents, audio)
ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "webp", "pdf",
    "webm", "wav", "mp3", "ogg", "m4a"
}

# Attempt importing official google-genai SDK
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
except ImportError:
    genai = None
    types = None
    APIError = Exception
    logger.warning("google-genai SDK is not yet installed.")

# Import GGU Institutional Knowledge Base module
import knowledge_base


def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def sanitize_output(text: str) -> str:
    """
    Sanitizes output strings to ensure sensitive API keys
    or credentials are never exposed in responses or logs.
    """
    if not text:
        return ""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key and len(api_key) >= 8 and api_key in text:
        text = text.replace(api_key, "[REDACTED_KEY]")
    return text


def get_gemini_client():
    """
    Safely retrieves the Gemini client instance using the environment API key.
    Returns:
        tuple: (client_instance, error_message)
    """
    if genai is None:
        return None, "The 'google-genai' SDK is not installed on the server."

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return None, (
            "Gemini API key is missing or not configured. "
            "Please obtain a key from https://aistudio.google.com/ and set GEMINI_API_KEY in your .env file."
        )

    try:
        client = genai.Client(api_key=api_key)
        return client, None
    except Exception as exc:
        sanitized_err = sanitize_output(str(exc))
        logger.error(f"Failed to initialize google-genai client: {sanitized_err}")
        return None, f"Failed to initialize Gemini client: {sanitized_err}"


def get_or_create_sessions():
    """
    Retrieves or initializes the multi-session registry from Flask session.
    Returns:
        tuple: (sessions_dict, active_session_id)
    """
    sessions_map = session.get("sessions")
    if not isinstance(sessions_map, dict):
        sessions_map = {}
        session["sessions"] = sessions_map

    current_id = session.get("current_session_id")
    if not current_id or current_id not in sessions_map:
        new_id = uuid.uuid4().hex[:8]
        sessions_map[new_id] = {
            "id": new_id,
            "title": "New Conversation",
            "created_at": time.time(),
            "history": []
        }
        session["current_session_id"] = new_id
        session.modified = True

    return sessions_map, session["current_session_id"]


@app.route("/")
def index():
    """Serves the Single-Page Application (SPA) HTML frontend."""
    return render_template("index.html")


# ==============================================================================
# Multi-Session Chat Management APIs (For Sidebar)
# ==============================================================================

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """
    Lists all saved conversations for the current user session.
    """
    sessions_map, active_id = get_or_create_sessions()
    session_list = []
    for sid, sdata in sessions_map.items():
        session_list.append({
            "id": sid,
            "title": sdata.get("title", "Conversation"),
            "created_at": sdata.get("created_at", 0),
            "turn_count": len(sdata.get("history", [])) // 2
        })

    # Sort descending by creation / update timestamp
    session_list.sort(key=lambda s: s["created_at"], reverse=True)

    return jsonify({
        "sessions": session_list,
        "active_session_id": active_id
    }), 200


@app.route("/api/sessions", methods=["POST"])
def create_session():
    """
    Creates a new empty chat session and sets it as the active conversation.
    """
    sessions_map, _ = get_or_create_sessions()
    new_id = uuid.uuid4().hex[:8]
    sessions_map[new_id] = {
        "id": new_id,
        "title": "New Conversation",
        "created_at": time.time(),
        "history": []
    }
    session["current_session_id"] = new_id
    session.modified = True

    logger.info(f"Created new conversation session: {new_id}")
    return jsonify({
        "id": new_id,
        "title": "New Conversation",
        "created_at": sessions_map[new_id]["created_at"]
    }), 201


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """
    Retrieves the full conversation history for a specific session.
    """
    sessions_map, _ = get_or_create_sessions()
    if session_id not in sessions_map:
        return jsonify({"error": "Session not found."}), 404

    session["current_session_id"] = session_id
    session.modified = True

    sdata = sessions_map[session_id]

    # Convert internal history format for frontend rendering
    client_history = []
    for turn in sdata.get("history", []):
        role = turn.get("role", "user")
        text = ""
        filename = None
        for part in turn.get("parts", []):
            if "text" in part:
                text = part["text"]
            elif "file_data" in part:
                filename = part["file_data"].get("file_uri", "").split("/")[-1]

        client_history.append({
            "role": "bot" if role == "model" else "user",
            "text": text,
            "filename": filename
        })

    return jsonify({
        "id": session_id,
        "title": sdata.get("title", "Conversation"),
        "history": client_history
    }), 200


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """
    Deletes a specific conversation session.
    """
    sessions_map, active_id = get_or_create_sessions()
    if session_id in sessions_map:
        del sessions_map[session_id]
        logger.info(f"Deleted conversation session: {session_id}")

    # If the active session was deleted, select another or create new
    if active_id == session_id:
        if sessions_map:
            session["current_session_id"] = next(iter(sessions_map.keys()))
        else:
            new_id = uuid.uuid4().hex[:8]
            sessions_map[new_id] = {
                "id": new_id,
                "title": "New Conversation",
                "created_at": time.time(),
                "history": []
            }
            session["current_session_id"] = new_id

    session.modified = True
    return jsonify({
        "status": "deleted",
        "active_session_id": session["current_session_id"]
    }), 200


@app.route("/reset", methods=["POST"])
def reset():
    """
    Clears the active conversation history or starts a fresh session.
    """
    sessions_map, active_id = get_or_create_sessions()
    if active_id in sessions_map:
        sessions_map[active_id]["history"] = []
        sessions_map[active_id]["title"] = "New Conversation"
        session.modified = True

    logger.info(f"Reset history for active session: {active_id}")
    return jsonify({
        "status": "success",
        "message": "Conversation history reset successfully.",
        "active_session_id": active_id
    }), 200


@app.route("/api/knowledge", methods=["GET"])
def get_knowledge():
    """
    Returns the loaded Godavari Global University (GGU) institutional knowledge data.
    """
    data = knowledge_base.load_knowledge_data()
    return jsonify(data), 200


# ==============================================================================
# Multimodal Chat Endpoint
# ==============================================================================

@app.route("/chat", methods=["POST"])
def chat():
    """
    Multimodal Chat endpoint supporting multi-session conversation memory.
    Accepts: multipart/form-data containing:
        - message (optional text)
        - file (optional image or PDF file)
        - session_id (optional target session ID)
    Returns: JSON payload {"response": "bot text", "filename": "...", "session_id": "...", "title": "..."}
    """
    client, error_message = get_gemini_client()
    if error_message:
        logger.warning(f"Configuration check failed: {error_message}")
        return jsonify({"error": error_message}), 500

    # 1. Determine active chat session
    sessions_map, default_active_id = get_or_create_sessions()
    target_session_id = request.form.get("session_id", "").strip() or default_active_id

    if target_session_id not in sessions_map:
        target_session_id = default_active_id

    session["current_session_id"] = target_session_id
    active_session_data = sessions_map[target_session_id]

    # 2. Extract user message & file (supports images, pdfs, and voice recordings)
    user_message = request.form.get("message", "").strip()
    uploaded_file = request.files.get("file") or request.files.get("audio")
    local_path = None
    original_filename = None
    uploaded_google_file = None
    is_audio = False

    try:
        if uploaded_file and uploaded_file.filename.strip():
            filename = uploaded_file.filename.strip()
            if not allowed_file(filename):
                return jsonify({
                    "error": f"Unsupported file format. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                }), 400

            original_filename = secure_filename(filename)
            unique_filename = f"{uuid.uuid4().hex[:10]}_{original_filename}"
            local_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)

            # Determine if this upload is an audio voice note
            ext_lower = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
            is_audio = ext_lower in {"webm", "wav", "mp3", "ogg", "m4a"}

            # Save file securely to uploads folder
            uploaded_file.save(local_path)
            logger.info(f"Saved upload locally to {local_path} ({os.path.getsize(local_path)} bytes, is_audio={is_audio})")

            # Upload to Google's GenAI File Service with correct MIME type
            try:
                inferred_mime, _ = mimetypes.guess_type(local_path)
                upload_mime = uploaded_file.mimetype or inferred_mime
                if upload_mime and ";" in upload_mime:
                    upload_mime = upload_mime.split(";")[0].strip()

                # Normalize audio MIME types for Gemini File API
                if ext_lower == "webm":
                    upload_mime = "audio/webm"
                elif ext_lower == "wav":
                    upload_mime = "audio/wav"
                elif ext_lower == "mp3":
                    upload_mime = "audio/mpeg"
                elif ext_lower == "ogg":
                    upload_mime = "audio/ogg"
                elif ext_lower == "m4a":
                    upload_mime = "audio/mp4"

                upload_kwargs = {"file": local_path}
                if upload_mime:
                    upload_kwargs["config"] = {"mime_type": upload_mime}

                uploaded_google_file = client.files.upload(**upload_kwargs)
                logger.info(f"Uploaded file to Google: {uploaded_google_file.name} ({uploaded_google_file.mime_type})")
            except Exception as upload_err:
                sanitized_err = sanitize_output(str(upload_err))
                logger.error(f"Failed to upload file to Google GenAI: {sanitized_err}")
                return jsonify({
                    "error": f"Failed to upload file to AI service: {sanitized_err}"
                }), 502

        if not user_message and not uploaded_google_file:
            return jsonify({"error": "Please enter a message, record voice, or attach a file."}), 400

        # Auto-generate a clean session title from the first prompt
        if active_session_data.get("title") == "New Conversation" or not active_session_data.get("title"):
            if user_message:
                snippet = user_message[:36].strip()
                if len(user_message) > 36:
                    snippet += "..."
                active_session_data["title"] = snippet
            elif is_audio:
                active_session_data["title"] = "🎙️ Voice Conversation"
            else:
                active_session_data["title"] = f"📎 {original_filename[:24]}"

        # 3. Working copy of history for resilience
        existing_history = active_session_data.get("history", [])
        working_history = [dict(turn) for turn in existing_history]

        # 4. Construct current user turn parts
        current_turn_parts = []
        if uploaded_google_file:
            current_turn_parts.append({
                "file_data": {
                    "file_uri": uploaded_google_file.uri,
                    "mime_type": uploaded_google_file.mime_type
                }
            })

        if user_message:
            current_turn_parts.append({"text": user_message})
        else:
            if is_audio:
                current_turn_parts.append({
                    "text": "Please listen carefully to this voice message from the user and respond with a helpful, clear, and comprehensive answer."
                })
            else:
                current_turn_parts.append({"text": "Please analyze and explain the contents of this uploaded file."})

        working_history.append({
            "role": "user",
            "parts": current_turn_parts
        })

        # 5. Candidate models with automated backoff and fallback
        configured_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        candidate_models = [
            configured_model,
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-flash-latest"
        ]
        candidate_models = list(dict.fromkeys(candidate_models))

        # 5.1 Construct GGU Institutional Knowledge Grounding Config
        system_instruction = knowledge_base.build_system_instruction()
        gen_config = None
        if types is not None:
            try:
                gen_config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            except Exception as cfg_err:
                logger.warning(f"Could not build GenerateContentConfig: {cfg_err}")
                gen_config = None

        bot_text = None
        last_error = None
        MAX_RETRIES_PER_MODEL = 2

        for model_name in candidate_models:
            for attempt in range(MAX_RETRIES_PER_MODEL + 1):
                try:
                    logger.info(
                        f"Attempting generation with {model_name} "
                        f"(attempt {attempt + 1}/{MAX_RETRIES_PER_MODEL + 1}, history turns: {len(working_history)})"
                    )
                    gen_kwargs = {
                        "model": model_name,
                        "contents": working_history
                    }
                    if gen_config is not None:
                        gen_kwargs["config"] = gen_config

                    response = client.models.generate_content(**gen_kwargs)
                    if response and response.text:
                        bot_text = response.text
                        logger.info(f"Successfully generated response using {model_name}")
                        break
                except APIError as api_err:
                    last_error = api_err
                    err_str = str(api_err).lower()

                    if "404" in err_str or "not found" in err_str or "no longer available" in err_str:
                        logger.warning(f"Model {model_name} unavailable/retired (404). Switching model...")
                        break

                    is_transient = any(needle in err_str for needle in [
                        "503", "unavailable", "high demand", "capacity",
                        "429", "resource_exhausted", "quota", "rate limit",
                        "500", "502", "504", "timeout"
                    ])

                    if is_transient:
                        if attempt < MAX_RETRIES_PER_MODEL:
                            backoff = (0.8 * (2 ** attempt)) + random.uniform(0.1, 0.4)
                            logger.warning(f"Model {model_name} busy. Retrying in {backoff:.2f}s...")
                            time.sleep(backoff)
                            continue
                        else:
                            logger.warning(f"Model {model_name} transient retries exhausted; switching to fallback...")
                            break

                    logger.error(f"Non-transient error on {model_name}: {api_err}")
                    break

                except Exception as gen_exc:
                    last_error = gen_exc
                    logger.warning(f"Network error on {model_name}: {gen_exc}")
                    if attempt < MAX_RETRIES_PER_MODEL:
                        time.sleep(1.0)
                        continue
                    break

            if bot_text:
                break

        if not bot_text:
            if last_error:
                sanitized_err = sanitize_output(str(last_error))
                logger.error(f"All candidate models exhausted. Last error: {sanitized_err}")
                return jsonify({
                    "error": (
                        "The AI service is experiencing high traffic across servers. "
                        "Please tap 'Retry' below or try again in a few seconds."
                    ),
                    "details": sanitized_err
                }), 503

            bot_text = "I received an empty response from the AI model. Please try rephrasing your message."

        # 6. Commit successful interaction to active session history
        working_history.append({
            "role": "model",
            "parts": [{"text": bot_text}]
        })
        active_session_data["history"] = working_history
        active_session_data["created_at"] = time.time()  # Bump last active timestamp
        session.modified = True

        return jsonify({
            "response": bot_text,
            "filename": original_filename,
            "session_id": target_session_id,
            "title": active_session_data.get("title", "Conversation")
        }), 200

    except APIError as api_err:
        sanitized_err = sanitize_output(str(api_err))
        logger.error(f"Gemini API Error: {sanitized_err}")
        return jsonify({"error": f"Gemini API Error: {sanitized_err}"}), 502

    except Exception as exc:
        sanitized_err = sanitize_output(str(exc))
        logger.error(f"Unexpected error: {sanitized_err}", exc_info=True)
        return jsonify({"error": f"An error occurred: {sanitized_err}"}), 500

    finally:
        # Clean up local temporary upload file
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"Cleaned up local file: {local_path}")
            except Exception as rm_err:
                logger.warning(f"Failed to delete temporary file {local_path}: {rm_err}")


@app.route("/<path:path>")
def block_sensitive_files(path):
    """Blocks direct access to sensitive configuration files."""
    lower_path = path.lower()
    if lower_path.startswith(".env") or ".env" in lower_path or lower_path.startswith(".git"):
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    print("\n" + "=" * 60)
    print("🤖 Multimodal AI Chatbot (Full-Page + Liquid Glass + Sidebar History)")
    print(f"📍 Local access: http://localhost:{port} (or http://127.0.0.1:{port})")
    print(f"🌐 Server network binding: http://{host}:{port}")
    print("=" * 60 + "\n")

    app.run(host=host, port=port, debug=debug)
