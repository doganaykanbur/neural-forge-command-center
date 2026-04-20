import httpx
import json
import logging
import time
import os
from typing import List, Dict, Any, Optional

# ═════════════════════════════════════════════
# Configuration & Logging
# ═════════════════════════════════════════════

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("nexus-bridge")

# Silence uvicorn info logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# Brain Mapping (Neural Forge v2.3 Optimized)
ROLE_MODELS = {
    "architect": "llama3:latest",     # Strategic Logic & Planning
    "builder": "qwen2.5-coder:7b",   # Specialized Coding Expert
}

class NexusBridge:
    """
    Bridge between Anthropic API and Local Ollama.
    Manages VRAM by unloading/loading models based on role.
    """
    def __init__(self):
        self.active_role = "builder"
        self.loaded_model = None
        self.role_models = ROLE_MODELS

    async def get_ollama_status(self):
        """Query Ollama for live model and VRAM telemetry."""
        try:
            async with httpx.AsyncClient() as client:
                # Get loaded models
                resp = await client.get(f"{OLLAMA_URL}/api/ps")
                ps_data = resp.json() if resp.status_code == 200 else {}
                
                # Get available models
                tags_resp = await client.get(f"{OLLAMA_URL}/api/tags")
                tags_data = tags_resp.json() if tags_resp.status_code == 200 else {}
                
                loaded = ps_data.get("models", [])
                self.loaded_model = loaded[0].get("name") if loaded else None
                
                # Estimate VRAM usage from ps_data
                vram_used = 0
                if loaded:
                     vram_used = sum(m.get("size_vram", 0) for m in loaded) / (1024**3) # GB
                
                return {
                    "loaded_models": [m.get("name") for m in loaded],
                    "total_models": len(tags_data.get("models", [])),
                    "vram_gb_used": round(vram_used, 2),
                    "status": "online" if resp.status_code == 200 else "offline"
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def switch_model(self, role: str, target_model: str = None):
        """Force a model switch to manage VRAM."""
        if not target_model:
            target_model = self.role_models.get(role, self.role_models["builder"])
        
        status = await self.get_ollama_status()
        current_loaded = status.get("loaded_models", [])
        
        if target_model not in current_loaded:
            # Unload others if VRAM is tight (Assumes 8GB limit)
            for m in current_loaded:
                logger.info(f"[-] Unloading {m} to free VRAM...")
                async with httpx.AsyncClient() as client:
                    await client.post(f"{OLLAMA_URL}/api/generate", json={"model": m, "keep_alive": 0})
            
            logger.info(f"[+] Loading {target_model} for Neural Forge...")
            # Trigger load
            async with httpx.AsyncClient() as client:
                await client.post(f"{OLLAMA_URL}/api/generate", json={"model": target_model, "keep_alive": "5m"})
        
        self.active_role = role
        self.loaded_model = target_model
        return {"role": role, "model": target_model}

    async def chat(self, body: dict):
        """Translates Anthropic -> Ollama Chat."""
        # 1. Detect Role
        system_prompt = body.get("system", "").lower()
        role = "builder"
        if any(keyword in system_prompt for keyword in ["architect", "blueprint", "design", "plan", "xml"]):
            role = "architect"
        
        # 2. Ensure model
        target = await self.switch_model(role)
        model_name = target["model"]
        
        # 3. Translate
        messages = body.get("messages", [])
        ollama_messages = []
        if body.get("system"):
            ollama_messages.append({"role": "system", "content": body["system"]})
        
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                content = "\n".join([p.get("text", "") for p in content if p.get("type") == "text"])
            ollama_messages.append({"role": msg.get("role"), "content": content})

        # 4. Request
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json={
                "model": model_name,
                "messages": ollama_messages,
                "stream": False,
                "options": {"temperature": body.get("temperature", 0.5)}
            })
            resp.raise_for_status()
            data = resp.json()

        # 5. Response
        return {
            "id": f"msg_{int(time.time())}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": data["message"]["content"]}],
            "model": model_name,
            "usage": {
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0)
            }
        }

# --- FastAPI Integration ---
from fastapi import FastAPI, Request

app = FastAPI(title="Nexus Bridge")
_bridge_instance = NexusBridge()

@app.post("/v1/messages")
async def messages_proxy(request: Request):
    body = await request.json()
    return await _bridge_instance.chat(body)

@app.get("/health")
async def health():
    return await _bridge_instance.get_ollama_status()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
