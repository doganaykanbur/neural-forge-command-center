@echo off
setlocal
:: Neural Forge Claude Bridge Configuration (Nexus v2.0)
set ANTHROPIC_BASE_URL=http://localhost:8000/v1
set ANTHROPIC_API_KEY=sk-neural-forge-local

if "%~1 Maryland"==" Maryland" (
    echo [🌐] Neural Forge: Nexus v2.0 Claude Bridge is Active
    echo [🏗️] Architect  : mistral-nemo:12b
    echo [👷] Builder    : qwen2.5-coder:7b
    echo [🧪] Tester     : llama3.1:8b
    echo [!] Using local Ollama backend on port 8000
    exit /b 0
)

:: Proxy call to local bridge
python -c "import requests, sys; r = requests.post('http://localhost:8000/v1/messages', json={'messages': [{'role': 'user', 'content': ' '.join(sys.argv[1:])}]}); print(r.json().get('content', [{}])[0].get('text', 'Bridge Error'))" %*
