import os, json
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import openai

load_dotenv()
app = Flask(__name__)
CORS(app)

GEMINI_KEY = os.getenv('GEMINI_API_KEY')
OPENAI_KEY = os.getenv('OPENAI_API_KEY')

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
if OPENAI_KEY:
    openai.api_key = OPENAI_KEY

@app.route('/')
def index():
    return render_template('index.html')

def gen(prompt, model):
    try:
        if model == 'gemini':
            for chunk in genai.GenerativeModel('gemini-2.5-flash').generate_content(prompt, stream=True):
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text, 'model': 'Gemini'})}\n\n"
        elif model == 'chatgpt':
            for chunk in openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[{'role': 'user', 'content': prompt}], stream=True):
                if 'choices' in chunk and chunk['choices'][0].get('delta', {}).get('content'):
                    yield f"data: {json.dumps({'text': chunk['choices'][0]['delta']['content'], 'model': 'ChatGPT'})}\n\n"
        elif model == 'both':
            yield f"data: {json.dumps({'text': '[Gemini] ', 'model': 'Gemini'})}\n\n"
            for chunk in genai.GenerativeModel('gemini-2.5-flash').generate_content(prompt, stream=True):
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text, 'model': 'Gemini'})}\n\n"
            yield f"data: {json.dumps({'text': '\n[ChatGPT] ', 'model': 'ChatGPT'})}\n\n"
            for chunk in openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[{'role': 'user', 'content': prompt}], stream=True):
                if 'choices' in chunk and chunk['choices'][0].get('delta', {}).get('content'):
                    yield f"data: {json.dumps({'text': chunk['choices'][0]['delta']['content'], 'model': 'ChatGPT'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    yield "data: [DONE]\n\n"

@app.route('/api/stream', methods=['POST'])
def stream():
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    model = data.get('model', 'gemini')
    if not prompt:
        return jsonify({'error': 'no prompt'}), 400
    return Response(stream_with_context(gen(prompt, model)), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
