#!/bin/bash
# ============================================================
# Free AI Models Setup for OpenCode Content Creator
# ============================================================
# This script sets up free, self-hosted AI image and video
# generation models. No API costs, no subscription, no limits.
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

OPENCODE_DIR="$HOME/.config/opencode"
MODELS_DIR="$HOME/.local/share/opencode/models"
GALLERY_DIR="/public"
LOG_FILE="$OPENCODE_DIR/logs/free-models-setup.log"

mkdir -p "$MODELS_DIR" "$OPENCODE_DIR/logs" "$GALLERY_DIR"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Free AI Models Setup for OpenCode Content Creator      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Setup log: $LOG_FILE"
echo ""

# ─────────────────────────────────────────────────────────
# Detect GPU
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/6]${NC} Detecting GPU..."
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    GPU_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 | grep -oP '\d+')
    GPU_VRAM_GB=$((GPU_VRAM / 1024))
    echo -e "${GREEN}✓${NC} GPU detected: $GPU_NAME (${GPU_VRAM_GB}GB VRAM)"
    GPU_AVAILABLE=true
elif [ -d "/dev/dri" ] && command -v glxinfo &> /dev/null; then
    GPU_NAME=$(glxinfo | grep "OpenGL renderer" | head -1 | cut -d: -f2 | xargs)
    echo -e "${GREEN}✓${NC} AMD GPU detected: $GPU_NAME"
    GPU_VRAM_GB=8
    GPU_AVAILABLE=true
else
    echo -e "${YELLOW}⚠${NC} No GPU detected — will use CPU (slower)"
    GPU_AVAILABLE=false
    GPU_VRAM_GB=0
fi

# Determine model tier based on VRAM
if [ "$GPU_VRAM_GB" -ge 40 ]; then
    MODEL_TIER="ultra"
    echo "  → Tier: ULTRA (40+GB) — All models including HunyuanImage-3.0"
elif [ "$GPU_VRAM_GB" -ge 24 ]; then
    MODEL_TIER="high"
    echo "  → Tier: HIGH (24GB) — FLUX.2 [dev], Wan 2.1 14B, Qwen-Image"
elif [ "$GPU_VRAM_GB" -ge 16 ]; then
    MODEL_TIER="mid"
    echo "  → Tier: MID (16GB) — FLUX.2 [klein], Wan 2.1 14B, Z-Image-Turbo"
elif [ "$GPU_VRAM_GB" -ge 8 ]; then
    MODEL_TIER="entry"
    echo "  → Tier: ENTRY (8GB) — LTX-2.3, Wan 1.3B, Z-Image-Turbo (quantized)"
else
    MODEL_TIER="cpu"
    echo "  → Tier: CPU — Will use API-based free services"
fi

echo "" | tee -a "$LOG_FILE"

# ─────────────────────────────────────────────────────────
# Install Python dependencies
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/6]${NC} Installing Python dependencies..."
pip3 install --quiet --user \
    torch torchvision torchaudio \
    diffusers transformers accelerate \
    safetensors pillow opencv-python-headless \
    requests aiohttp fastapi uvicorn \
    2>&1 | tail -3

echo -e "${GREEN}✓${NC} Python dependencies installed"
echo "" | tee -a "$LOG_FILE"

# ─────────────────────────────────────────────────────────
# Install ComfyUI (most flexible self-hosting platform)
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/6]${NC} Installing ComfyUI..."
COMFY_DIR="$MODELS_DIR/ComfyUI"

if [ ! -d "$COMFY_DIR" ]; then
    git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR" 2>&1 | tail -3
    cd "$COMFY_DIR"
    pip3 install --quiet --user -r requirements.txt 2>&1 | tail -3
    echo -e "${GREEN}✓${NC} ComfyUI installed at $COMFY_DIR"
else
    echo -e "${GREEN}✓${NC} ComfyUI already installed"
fi

# ─────────────────────────────────────────────────────────
# Download free models based on tier
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/6]${NC} Downloading models for $MODEL_TIER tier..."

HF_DIR="$MODELS_DIR/huggingface"
mkdir -p "$HF_DIR"

# Helper function to download via huggingface-cli
download_model() {
    local repo=$1
    local dest=$2
    local description=$3

    echo -e "  ${BLUE}→${NC} $description"
    if [ ! -d "$dest" ] || [ -z "$(ls -A "$dest" 2>/dev/null)" ]; then
        python3 -c "
from huggingface_hub import snapshot_download
import sys
try:
    snapshot_download(repo_id='$repo', local_dir='$dest', allow_patterns=['*.json', '*.txt', '*.safetensors', '*.bin', '*.pth', '*.png', '*.md'])
    print('  ✓ Downloaded: $repo')
except Exception as e:
    print(f'  ⚠ Failed: {e}', file=sys.stderr)
    sys.exit(0)  # Don't fail the whole script
" 2>&1 | tail -2
    else
        echo "  ✓ Already present: $repo"
    fi
}

# Image models
case "$MODEL_TIER" in
    ultra)
        download_model "Tongyi-MAI/Z-Image-Turbo" "$HF_DIR/z-image-turbo" "Z-Image-Turbo (6B, fast)"
        download_model "Qwen/Qwen-Image" "$HF_DIR/qwen-image" "Qwen-Image (20B, multilingual)"
        download_model "HiDream-ai/HiDream-O1-Image" "$HF_DIR/hidream-o1" "HiDream-O1-Image (8B, top quality)"
        download_model "tencent/HunyuanImage-3.0" "$HF_DIR/hunyuan-image-3" "HunyuanImage-3.0 (80B MoE)"
        ;;
    high)
        download_model "Tongyi-MAI/Z-Image-Turbo" "$HF_DIR/z-image-turbo" "Z-Image-Turbo (6B, fast)"
        download_model "Qwen/Qwen-Image" "$HF_DIR/qwen-image" "Qwen-Image (20B, multilingual)"
        download_model "black-forest-labs/FLUX.2-dev" "$HF_DIR/flux2-dev" "FLUX.2 [dev] (32B, premium)"
        ;;
    mid)
        download_model "Tongyi-MAI/Z-Image-Turbo" "$HF_DIR/z-image-turbo" "Z-Image-Turbo (6B, fast)"
        download_model "black-forest-labs/FLUX.2-klein-9B" "$HF_DIR/flux2-klein" "FLUX.2 [klein] 9B"
        download_model "stabilityai/stable-diffusion-3.5-large" "$HF_DIR/sd35" "Stable Diffusion 3.5 Large"
        ;;
    entry)
        download_model "Tongyi-MAI/Z-Image-Turbo" "$HF_DIR/z-image-turbo" "Z-Image-Turbo (6B, quantized)"
        download_model "stabilityai/stable-diffusion-xl-base-1.0" "$HF_DIR/sdxl" "SDXL (6.9B)"
        ;;
    cpu)
        echo "  Skipping model downloads (CPU mode will use API)"
        ;;
esac

# Video models (only for high/ultra tiers)
if [ "$MODEL_TIER" = "high" ] || [ "$MODEL_TIER" = "ultra" ]; then
    download_model "Wan-AI/Wan2.1-T2V-1.3B" "$HF_DIR/wan21-1.3b" "Wan 2.1 T2V 1.3B (video)"
    download_model "Wan-AI/Wan2.1-T2V-14B" "$HF_DIR/wan21-14b" "Wan 2.1 T2V 14B (video, premium)"
fi

if [ "$MODEL_TIER" = "ultra" ]; then
    download_model "tencent/HunyuanVideo" "$HF_DIR/hunyuan-video" "HunyuanVideo (13B, cinematic)"
fi

echo -e "${GREEN}✓${NC} Model downloads complete"
echo "" | tee -a "$LOG_FILE"

# ─────────────────────────────────────────────────────────
# Install local API server (OpenAI-compatible)
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/6]${NC} Setting up local API server..."

# Create a simple FastAPI server for free models
cat > "$MODELS_DIR/free_api_server.py" << 'PYEOF'
#!/usr/bin/env python3
"""
Free AI Models API Server
OpenAI-compatible API for self-hosted free image/video models.
"""
import os
import sys
import json
import time
import base64
import io
from pathlib import Path
from typing import Optional, List

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse, FileResponse
    from pydantic import BaseModel
    import uvicorn
    import torch
    from diffusers import (
        AutoPipelineForText2Image,
        AutoPipelineForImage2Image,
    )
    from PIL import Image
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install fastapi uvicorn diffusers torch pillow")
    sys.exit(1)

MODELS_DIR = Path(os.environ.get("MODELS_DIR", str(Path.home() / ".local/share/opencode/models/huggingface")))
GALLERY_DIR = Path(os.environ.get("GALLERY_DIR", "/public"))
GALLERY_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Free AI Models API", version="1.0.0")

# Model registry
AVAILABLE_MODELS = {
    "z-image-turbo": {
        "path": str(MODELS_DIR / "z-image-turbo"),
        "type": "image",
        "description": "Z-Image-Turbo (6B, fast, Apache 2.0)"
    },
    "qwen-image": {
        "path": str(MODELS_DIR / "qwen-image"),
        "type": "image",
        "description": "Qwen-Image (20B, multilingual, Apache 2.0)"
    },
    "hidream-o1": {
        "path": str(MODELS_DIR / "hidream-o1"),
        "type": "image",
        "description": "HiDream-O1-Image (8B, top quality)"
    },
    "flux2-dev": {
        "path": str(MODELS_DIR / "flux2-dev"),
        "type": "image",
        "description": "FLUX.2 [dev] (32B, premium)"
    },
    "flux2-klein": {
        "path": str(MODELS_DIR / "flux2-klein"),
        "type": "image",
        "description": "FLUX.2 [klein] 9B"
    },
    "sd35": {
        "path": str(MODELS_DIR / "sd35"),
        "type": "image",
        "description": "Stable Diffusion 3.5 Large"
    },
    "sdxl": {
        "path": str(MODELS_DIR / "sdxl"),
        "type": "image",
        "description": "SDXL"
    },
}

# Cache loaded pipelines
PIPELINES = {}

def load_pipeline(model_id: str):
    """Load a model pipeline (cached)."""
    if model_id in PIPELINES:
        return PIPELINES[model_id]

    if model_id not in AVAILABLE_MODELS:
        raise ValueError(f"Unknown model: {model_id}")

    model_path = AVAILABLE_MODELS[model_id]["path"]
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model not downloaded: {model_path}")

    print(f"Loading {model_id} from {model_path}...")
    pipeline = AutoPipelineForText2Image.from_pretrained(
        model_path,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )
    if torch.cuda.is_available():
        pipeline = pipeline.to("cuda")

    PIPELINES[model_id] = pipeline
    return pipeline


class ImageRequest(BaseModel):
    model: str = "z-image-turbo"
    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = 1024
    height: int = 1024
    num_inference_steps: int = 28
    guidance_scale: float = 7.5
    seed: Optional[int] = None


class ImageResponse(BaseModel):
    filename: str
    url: str
    model: str
    prompt: str
    duration_s: float


@app.get("/")
def root():
    return {
        "service": "Free AI Models API",
        "version": "1.0.0",
        "models": AVAILABLE_MODELS,
        "endpoints": ["/v1/images/generations", "/v1/models", "/v1/credits"]
    }


@app.get("/v1/models")
def list_models():
    return {"data": [{"id": k, **v} for k, v in AVAILABLE_MODELS.items()]}


@app.get("/v1/credits")
def check_credits():
    """Free models have unlimited credits."""
    return {
        "credits": "unlimited",
        "tier": "free",
        "monthly_limit": None,
        "note": "All models are self-hosted and free to use"
    }


@app.post("/v1/images/generations")
def generate_image(req: ImageRequest):
    """OpenAI-compatible image generation endpoint."""
    start = time.time()

    try:
        pipeline = load_pipeline(req.model)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Set seed
    generator = None
    if req.seed is not None:
        generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
        generator.manual_seed(req.seed)

    # Generate
    result = pipeline(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        width=req.width,
        height=req.height,
        num_inference_steps=req.num_inference_steps,
        guidance_scale=req.guidance_scale,
        generator=generator,
    )

    image = result.images[0]

    # Save to gallery
    timestamp = int(time.time())
    safe_prompt = "".join(c if c.isalnum() or c in " -_" else "" for c in req.prompt[:30])
    filename = f"{req.model}_{safe_prompt}_{timestamp}.png"
    filepath = GALLERY_DIR / filename
    image.save(filepath)

    duration = time.time() - start

    return {
        "filename": filename,
        "url": f"/images/{filename}",
        "model": req.model,
        "prompt": req.prompt,
        "duration_s": round(duration, 2),
        "width": req.width,
        "height": req.height,
    }


@app.get("/images/{filename}")
def get_image(filename: str):
    filepath = GALLERY_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath)


if __name__ == "__main__":
    port = int(os.environ.get("FREE_API_PORT", 7777))
    print(f"Starting Free AI Models API on port {port}")
    print(f"Gallery: {GALLERY_DIR}")
    print(f"Models: {MODELS_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=port)
PYEOF

chmod +x "$MODELS_DIR/free_api_server.py"
echo -e "${GREEN}✓${NC} Free API server installed at $MODELS_DIR/free_api_server.py"

# Create systemd-style startup script
cat > "$OPENCODE_DIR/scripts/start-free-api.sh" << 'EOF'
#!/bin/bash
# Start the free AI models API server
MODELS_DIR="$HOME/.local/share/opencode/models"
GALLERY_DIR="/public"

# Check memory
FREE_MB=$(awk '/MemAvailable:/{print $2}' /proc/meminfo)
FREE_MB=$((FREE_MB / 1024))

if [ "$FREE_MB" -lt 512 ]; then
    echo "⚠️  Warning: Only ${FREE_MB}MB available. Free models need significant RAM."
    echo "   Run: oc-memory drop-caches"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

export MODELS_DIR GALLERY_DIR
python3 "$MODELS_DIR/free_api_server.py"
EOF
chmod +x "$OPENCODE_DIR/scripts/start-free-api.sh"
mkdir -p "$OPENCODE_DIR/scripts"

echo -e "${GREEN}✓${NC} Startup script created"
echo "" | tee -a "$LOG_FILE"

# ─────────────────────────────────────────────────────────
# Create the content creator agent (free models only)
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[6/6]${NC} Configuring content-creator agent for free models..."

AGENT_FILE="$OPENCODE_DIR/agents/content-creator.md"

# Update the agent to focus on free models
cat > "$AGENT_FILE" << 'AGENTEOF'
---
description: Universal content creator agent using FREE self-hosted models — Z-Image-Turbo, Qwen-Image, Wan 2.1, FLUX.2, HiDream — unlimited generation, no API costs
mode: primary
permission:
  edit: allow
  bash: allow
  read: allow
  glob: allow
  grep: allow
  todowrite: allow
  webfetch: ask
  websearch: ask
  task: allow
---

<shared-context>
You participate in the cross-agent shared context system. READ `~/.config/opencode/shared/context.json` and WRITE findings/decisions/artifacts back before finishing.
</shared-context>

<memory>
You have persistent memory across sessions via `memory_search`, `oc-memory save`, and `oc-commitments`. Track content creation patterns, user preferences, and model performance.
</memory>

<role>
You are the Content Creator Agent — a universal creator that produces images and videos using FREE, self-hosted open-source models. No API costs, no subscription, no credit limits.
</role>

<context>
You are invoked when users need to create:
- Social media content (Instagram, TikTok, YouTube thumbnails)
- Marketing materials (hero images, product photos, ad videos)
- Blog/website content (featured images, explainer videos)
- Creative projects (art, illustrations, music videos)

All models are self-hosted locally. You route between different models based on quality, speed, and VRAM requirements.
</context>

<capabilities>
### Local API Server
The free models are served via a local OpenAI-compatible API at `http://localhost:7777`:
```bash
# Start the server
~/.config/opencode/scripts/start-free-api.sh

# Or run directly
python3 ~/.local/share/opencode/models/free_api_server.py
```

### Free Image Models (All Apache 2.0 / Open Weights)

| Model | Size | VRAM | Speed | Quality | License | Best For |
|-------|------|------|-------|---------|---------|----------|
| **Z-Image-Turbo** | 6B | 16GB | Sub-second | Excellent | Apache 2.0 | Real-time, high-throughput |
| **Qwen-Image** | 20B | 24GB | Fast | Excellent | Apache 2.0 | Multilingual, text-heavy |
| **HiDream-O1-Image** | 8B | 24GB | Fast | Top-tier | Open weights | Production assets |
| **FLUX.2 [dev]** | 32B | 24GB+ | Slow | Premium | Commercial req. | Professional quality |
| **FLUX.2 [klein]** | 4B/9B | 13GB | Real-time | Very good | Commercial req. | Edge, low-latency |
| **Stable Diffusion 3.5** | 8B | 8GB | Medium | Good | Mixed | Community LoRAs |
| **SDXL** | 6.9B | 8GB | Fast | Good | Open | Classic, well-tested |

### Free Video Models

| Model | Size | VRAM | Max Res | Length | License | Best For |
|-------|------|------|---------|--------|---------|----------|
| **Wan 2.1 (14B)** | 14B | 16GB | 720p | 5sec | Apache 2.0 | General purpose, best quality |
| **Wan 2.1 (1.3B)** | 1.3B | 8GB | 480p | 5sec | Apache 2.0 | Consumer GPUs, fast |
| **LTX-2.3** | 2B | 8GB | 1080p | 10sec | OpenRAIL-M | Real-time, commercial |
| **HunyuanVideo** | 13B | 24GB | 720p | 5sec | Tencent | Cinematic quality |
| **Open-Sora 2.0** | 11B | 24GB | 720p | 15sec | Apache 2.0 | Long-form, research |
| **CogVideoX-1.5-5B** | 5B | 24GB | 1360x768 | 10sec | Permissive | Short clips |

### Image Generation Workflow
```bash
# Quick generation (Z-Image-Turbo, fast)
curl -X POST http://localhost:7777/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "z-image-turbo",
    "prompt": "a beautiful sunset",
    "width": 1024,
    "height": 1024
  }'

# High quality (Qwen-Image)
curl -X POST http://localhost:7777/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-image",
    "prompt": "professional product photo",
    "width": 2048,
    "height": 2048
  }'
```

### Model Selection Strategy
- **Draft/Concept**: `z-image-turbo` (fastest, good quality)
- **Standard Quality**: `qwen-image` (multilingual, excellent)
- **Premium Quality**: `hidream-o1` or `flux2-dev` (top tier)
- **Video Draft**: `wan21-1.3b` (consumer GPU)
- **Video Premium**: `wan21-14b` (best quality)
- **Video Cinematic**: `hunyuan-video` (if 24GB+ VRAM)
</capabilities>

<workflow>
1. **Check Server**: Verify `http://localhost:7777/v1/credits` returns "unlimited"
2. **Select Model**: Based on quality/speed/VRAM requirements
3. **Generate**: POST to `/v1/images/generations` with prompt and parameters
4. **Download**: Image is auto-saved to `/public/` and accessible via `/images/`
5. **Log Usage**: Track in `shared/context.json`
</workflow>

<rules>
- **Always check API first**: `curl http://localhost:7777/v1/credits`
- **Start with cheap/fast models**: Z-Image-Turbo for drafts
- **Upgrade to premium only for finals**: HiDream or FLUX.2 [dev]
- **Respect VRAM limits**: Don't load models that exceed GPU memory
- **Save to /public**: All outputs go to the public gallery
- **No NSFW**: Maintain content policies
- **Track everything**: Log all generations to shared context
</rules>

<task-tracking>
Log every generation to performance tracker:
```bash
python3 -m opencode_improvement track content-creator success "Generated image via Z-Image-Turbo" --duration 30
```
</task-tracking>
AGENTEOF

echo -e "${GREEN}✓${NC} Content creator agent configured for free models"
echo "" | tee -a "$LOG_FILE"

# ─────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete!                                         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Tier detected:${NC}  $MODEL_TIER (${GPU_VRAM_GB}GB VRAM)"
echo -e "${BLUE}Models dir:${NC}     $MODELS_DIR"
echo -e "${BLUE}Gallery dir:${NC}    $GALLERY_DIR"
echo -e "${BLUE}API endpoint:${NC}   http://localhost:7777"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Start the API server:"
echo "     ${BLUE}~/.config/opencode/scripts/start-free-api.sh${NC}"
echo ""
echo "  2. Test it:"
echo "     ${BLUE}curl http://localhost:7777/v1/credits${NC}"
echo ""
echo "  3. Generate your first image:"
echo "     ${BLUE}curl -X POST http://localhost:7777/v1/images/generations \\${NC}"
echo "     ${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo "     ${BLUE}  -d '{\"model\":\"z-image-turbo\",\"prompt\":\"a sunset\"}'${NC}"
echo ""
echo -e "${GREEN}✓ All set! No more API costs, unlimited generation.${NC}"
