import os
import tempfile
import subprocess
import sys
import platform
from pathlib import Path
import logging
from flask import Flask, render_template, request, jsonify
import requests

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
N8N_WEBHOOK_URL_AUDIO = "https://laboratorio-n8n.nu7ixt.easypanel.host/webhook-test/audio"
N8N_WEBHOOK_URL_TRANSCRICAO = "https://laboratorio-n8n.nu7ixt.easypanel.host/webhook-test/trancricao"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB

ALLOWED_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "webm", "m4v", "mp3", "wav", "m4a"}

def check_ffmpeg():
    """Verifica se o ffmpeg está disponível"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def allowed_file(filename: str) -> bool:
    """Verifica se o arquivo tem extensão permitida"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def is_audio_file(filename: str) -> bool:
    """Verifica se é um arquivo de áudio"""
    audio_extensions = {"mp3", "wav", "m4a", "aac", "flac"}
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    return ext in audio_extensions

def extract_audio_from_video(input_path: str, output_path: str) -> tuple[bool, str]:
    """Extrai áudio do vídeo usando ffmpeg"""
    try:
        cmd = [
            "ffmpeg", "-i", input_path,
            "-vn", "-acodec", "libmp3lame",
            "-ar", "44100", "-ac", "2", "-b:a", "128k",
            output_path, "-y"
        ]
        
        logger.info(f"Executando: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600
        )
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, ""
        else:
            return False, "Arquivo de áudio não foi gerado"
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else "Erro desconhecido"
        return False, f"Erro na conversão: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, "Timeout na conversão"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/health", methods=["GET"])
def health():
    """Endpoint de diagnóstico"""
    return jsonify({
        "status": "ok",
        "ffmpeg_available": check_ffmpeg(),
        "platform": platform.system(),
        "max_file_size": "500MB"
    })

@app.route("/processar", methods=["POST"])
def processar():
    # Log detalhado da requisição
    logger.info(f"Método: {request.method}")
    logger.info(f"Content-Type: {request.content_type}")
    logger.info(f"Arquivos recebidos: {list(request.files.keys())}")
    logger.info(f"Form data: {list(request.form.keys())}")
    
    # Verificar se é multipart/form-data
    if not request.content_type or not request.content_type.startswith('multipart/form-data'):
        return jsonify({
            "error": "Requisição deve ser multipart/form-data",
            "received_content_type": request.content_type
        }), 400
    
    # Verificar se tem arquivos
    if not request.files:
        return jsonify({
            "error": "Nenhum arquivo foi enviado",
            "help": "Certifique-se de que o campo file está preenchido"
        }), 400
    
    # Verificar campo 'file' especificamente
    if "file" not in request.files:
        available_fields = list(request.files.keys())
        return jsonify({
            "error": "Campo 'file' é obrigatório",
            "available_fields": available_fields,
            "help": "O campo deve ter o name='file'"
        }), 400

    file = request.files["file"]
    
    # Verificar se arquivo foi selecionado
    if not file or file.filename == "" or file.filename is None:
        return jsonify({
            "error": "Nenhum arquivo foi selecionado",
            "help": "Selecione um arquivo antes de enviar"
        }), 400

    # Verificar extensão
    if not allowed_file(file.filename):
        return jsonify({
            "error": f"Formato não suportado: {file.filename}",
            "supported_formats": list(ALLOWED_EXTENSIONS)
        }), 400

    # Criar diretório temporário
    temp_dir = tempfile.mkdtemp()
    temp_input_path = None
    temp_audio_path = None
    
    try:
        # Salvar arquivo enviado
        file_ext = file.filename.rsplit(".", 1)[1].lower()
        temp_input_path = os.path.join(temp_dir, f"input.{file_ext}")
        temp_audio_path = os.path.join(temp_dir, "audio.mp3")
        
        logger.info(f"Salvando arquivo: {file.filename}")
        file.save(temp_input_path)
        
        if not os.path.exists(temp_input_path):
            return jsonify({"error": "Falha ao salvar arquivo no servidor"}), 500
            
        file_size = os.path.getsize(temp_input_path)
        if file_size == 0:
            return jsonify({"error": "Arquivo está vazio"}), 400
        
        logger.info(f"Arquivo salvo: {file_size} bytes")
        
        # Processar arquivo
        if is_audio_file(file.filename):
            logger.info("Arquivo já é áudio")
            if file_ext == "mp3":
                temp_audio_path = temp_input_path
            else:
                if not check_ffmpeg():
                    return jsonify({
                        "error": "FFmpeg não disponível para converter áudio",
                        "solution": "Instale FFmpeg ou use arquivo MP3"
                    }), 500
                
                success, error = extract_audio_from_video(temp_input_path, temp_audio_path)
                if not success:
                    return jsonify({"error": f"Falha na conversão: {error}"}), 500
        else:
            # É vídeo
            if not check_ffmpeg():
                return jsonify({
                    "error": "FFmpeg não está disponível",
                    "solution": "Instale FFmpeg para processar vídeos",
                    "install_commands": {
                        "ubuntu": "sudo apt-get install ffmpeg",
                        "centos": "sudo yum install ffmpeg",
                        "macos": "brew install ffmpeg"
                    }
                }), 500
            
            logger.info("Extraindo áudio do vídeo...")
            success, error = extract_audio_from_video(temp_input_path, temp_audio_path)
            if not success:
                return jsonify({"error": f"Falha na extração: {error}"}), 500
        
        # Verificar áudio gerado
        if not os.path.exists(temp_audio_path) or os.path.getsize(temp_audio_path) == 0:
            return jsonify({"error": "Arquivo de áudio não foi gerado corretamente"}), 500
        
        audio_size = os.path.getsize(temp_audio_path)
        logger.info(f"Áudio preparado: {audio_size} bytes")
        
        # Enviar para N8N
        try:
            with open(temp_audio_path, "rb") as audio_file:
                files = {
                    "file": ("audio.mp3", audio_file, "audio/mpeg")
                }
                data = {
                    "video_filename": file.filename,
                    "audio_size": str(audio_size)
                }
                
                logger.info(f"Enviando para N8N: {audio_size} bytes")
                
                response = requests.post(
                    N8N_WEBHOOK_URL_AUDIO,
                    files=files,
                    data=data,
                    timeout=125
                )
                
                if response.status_code != 200:
                    return jsonify({
                        "error": f"Erro N8N (status: {response.status_code})",
                        "details": response.text[:300]
                    }), 502
                
                try:
                    result = response.json()
                except ValueError:
                    return jsonify({"error": "Resposta inválida do N8N"}), 502
                
                # Extrair utterances
                if isinstance(result, list) and result:
                    utterances = result[0].get("utterances", [])
                else:
                    utterances = result.get("utterances", []) if isinstance(result, dict) else []
                
                return jsonify({
                    "success": True,
                    "utterances": utterances,
                    "audio_size": audio_size,
                    "original_filename": file.filename
                })
                
        except requests.exceptions.Timeout:
            return jsonify({"error": "Timeout na comunicação com N8N"}), 504
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "Erro de conexão com N8N"}), 503
        except Exception as e:
            return jsonify({"error": f"Erro na comunicação: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Erro geral: {str(e)}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500
        
    finally:
        # Limpar arquivos temporários
        try:
            import shutil
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Erro ao limpar: {str(e)}")

@app.route("/enviar_solar", methods=["POST"])
def enviar_solar():
    """Endpoint para enviar transcrição"""
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "JSON requerido"}), 400
        
        transcricao = payload.get("transcricao", [])
        if not transcricao:
            return jsonify({"error": "Campo 'transcricao' obrigatório"}), 400
        
        response = requests.post(
            N8N_WEBHOOK_URL_TRANSCRICAO,
            json={"transcricao": transcricao},
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return jsonify({"ok": True})
        else:
            return jsonify({
                "ok": False,
                "status": response.status_code,
                "error": response.text[:300]
            }), 502
            
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    logger.info("🚀 Iniciando aplicação...")
    
    if check_ffmpeg():
        logger.info("✅ FFmpeg disponível")
    else:
        logger.warning("⚠️  FFmpeg não encontrado - apenas arquivos MP3 serão aceitos")
    
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
