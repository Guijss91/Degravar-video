import os
import tempfile
import subprocess
from flask import Flask, render_template, request, jsonify
import requests

# Config
N8N_WEBHOOK_URL_AUDIO = "https://laboratorio-n8n.nu7ixt.easypanel.host/webhook/audio"
N8N_WEBHOOK_URL_TRANSCRICAO = "https://laboratorio-n8n.nu7ixt.easypanel.host/webhook/trancricao"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1GB
ALLOWED_EXTENSIONS = {"mp4", "mkv", "avi", "mov"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/processar", methods=["POST"])
def processar():
    if "file" not in request.files:
        return jsonify({"error": "Arquivo não enviado (campo file)."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nome de arquivo vazio."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Formato não suportado."}), 400

    suffix = "." + file.filename.rsplit(".", 1)[1].lower()
    tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_video_path = tmp_video.name
    file.save(tmp_video_path)

    tmp_audio_path = tmp_video_path.rsplit(".", 1)[0] + ".mp3"

    try:
        subprocess.run(
            ["ffmpeg", "-i", tmp_video_path, "-q:a", "0", "-map", "a", tmp_audio_path, "-y"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        with open(tmp_audio_path, "rb") as f:
            files = {"file": (os.path.basename(tmp_audio_path), f, "audio/mpeg")}
            data = {"video_filename": file.filename}
            r = requests.post(N8N_WEBHOOK_URL_AUDIO, files=files, data=data, timeout=120)

        if r.status_code != 200:
            return jsonify({"error": f"Erro no n8n audio: {r.status_code}", "body": r.text}), 502

        result = r.json()
        if isinstance(result, list) and result:
            utterances = result[0].get("utterances", [])
        else:
            utterances = result.get("utterances", []) if isinstance(result, dict) else []

        return jsonify({"utterances": utterances})

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "Falha na conversão ffmpeg", "stderr": e.stderr.decode(errors="ignore")}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            if os.path.exists(tmp_video_path):
                os.remove(tmp_video_path)
            if os.path.exists(tmp_audio_path):
                os.remove(tmp_audio_path)
        except Exception:
            pass


@app.route("/enviar_solar", methods=["POST"])
def enviar_solar():
    payload = request.get_json(silent=True) or {}
    transcricao = payload.get("transcricao", [])
    try:
        r = requests.post(N8N_WEBHOOK_URL_TRANSCRICAO, json={"transcricao": transcricao}, timeout=120)
        if r.status_code == 200:
            return jsonify({"ok": True})
        return jsonify({"ok": False, "status": r.status_code, "body": r.text}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=False)
