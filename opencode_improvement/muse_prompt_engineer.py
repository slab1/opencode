#!/usr/bin/env python3
"""
Muse Prompt Engineering for Agent Training
Uses Muse (via DeepSeek proxy) to optimize agent prompts
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.home() / ".config/opencode"
AGENTS_DIR = BASE_DIR / "agents"
PROXY_URL = "http://127.0.0.1:8765/responses"

def call_muse(prompt, max_tokens=1000):
    """Call Muse via proxy (or direct OpenRouter fallback)"""
    import urllib.request
    
    key = os.environ.get("OPENROUTER_API_KEY", "")
    
    # Try proxy first
    try:
        data = {
            "model": "muse-spark-1.2-contributor",
            "input": [{"type": "message", "role": "user", "content": prompt}],
            "stream": False,
            "max_output_tokens": max_tokens
        }
        req = urllib.request.Request(
            PROXY_URL,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            j = json.loads(resp.read().decode())
            output = j.get("output", [])
            for item in output:
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            return c.get("text", "")
                elif item.get("type") == "function_call":
                    return item.get("arguments", "")
            return json.dumps(j)[:1000]
    except Exception as e:
        # Fallback to direct OpenRouter
        try:
            data = {
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "https://github.com/opencode-prompt-train",
                "X-Title": "Muse Prompt Engineer"
            }
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(data).encode(),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                j = json.loads(resp.read().decode())
                return j["choices"][0]["message"]["content"]
        except Exception as e2:
            return f"Error: {e} / {e2}"

def analyze_agent(agent_name):
    """Analyze an agent's current prompt"""
    path = AGENTS_DIR / f"{agent_name}.md"
    if not path.exists():
        return None
    content = path.read_text()
    return {
        "name": agent_name,
        "content": content,
        "length": len(content),
        "has_role": "<role>" in content,
        "has_rules": "<rules>" in content,
        "has_capabilities": "<capabilities>" in content
    }

def optimize_prompt(agent_name, analysis):
    """Use Muse to optimize the agent prompt"""
    prompt = f"""You are a prompt engineering expert. Optimize this agent prompt.

Agent: {agent_name}
Prompt (first 1200 chars):
{analysis['content'][:1200]}

Provide: 1) Strengths 2) Weaknesses 3) Optimized version (code block) 4) Key improvements. Focus on clarity and specificity."""

    result = call_muse(prompt, max_tokens=2000)
    return result

def train_all_agents(limit=3):
    """Train a batch of agents"""
    agents = sorted([p.stem for p in AGENTS_DIR.glob("*.md")])
    print(f"Found {len(agents)} agents, training {limit}...")
    
    results = []
    for agent in agents[:limit]:
        print(f"\n=== Training {agent} ===")
        analysis = analyze_agent(agent)
        if not analysis:
            continue
        
        print(f"  Length: {analysis['length']}, Has role: {analysis['has_role']}")
        
        optimized = optimize_prompt(agent, analysis)
        print(f"  Optimized: {optimized[:200]}...")
        
        results.append({
            "agent": agent,
            "original_length": analysis["length"],
            "optimized": optimized[:1000],
            "timestamp": datetime.now().isoformat()
        })
    
    # Save results
    out_path = BASE_DIR / "shared" / "muse_prompt_training.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\n✓ Saved to {out_path}")
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Muse Prompt Engineering for Agents")
    parser.add_argument("--agent", help="Single agent to optimize")
    parser.add_argument("--all", action="store_true", help="Train all agents")
    parser.add_argument("--limit", type=int, default=3, help="Limit for --all")
    parser.add_argument("--test", action="store_true", help="Test Muse connection")
    
    args = parser.parse_args()
    
    if args.test:
        result = call_muse("Say hi in one sentence and explain what makes a good prompt.")
        print(f"Muse: {result[:500]}")
    elif args.agent:
        analysis = analyze_agent(args.agent)
        if analysis:
            print(f"Analyzing {args.agent}...")
            result = optimize_prompt(args.agent, analysis)
            print(result)
        else:
            print(f"Agent {args.agent} not found")
    elif args.all:
        train_all_agents(limit=args.limit)
    else:
        parser.print_help()
