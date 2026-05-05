# Model Configuration Guide

## Where Models Are Actually Specified

### 1. Default Model (Environment Variable)

**Location**: `backend/.env` file

```bash
LLM_MODEL=gpt-4o
```

This is the **primary** way to set the default model. All agents will use this model unless overridden.

**Supported Models:**
- OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, etc.
- Gemini: `gemini-3-pro-preview`, `gemini-flash-latest`, `gemini-flash-lite-latest`, etc.

**Code Location**: `backend/src/main.py` lines ~1200 and ~1690
```python
model = os.getenv("LLM_MODEL", "gpt-4o")
llm_client = get_llm_client(model=model)
```

### 2. Per-Agent Model Override (YAML Config)

**Location**: `backend/src/agents/config/*.yaml` files

**Current State**: All model fields are **commented out** by default. To enable per-agent model selection:

1. Open the agent's YAML file (e.g., `backend/src/agents/config/synthesizer.yaml`)
2. Uncomment the `model` line:
   ```yaml
   id: synthesizer
   name: Strategy Synthesizer Agent
   model: gemini-flash-latest  # Uncomment this line
   role: Combines insights...
   ```

**Code Location**: `backend/src/agents/registry.py` lines 60-78
```python
config = AgentConfig(
    ...
    model=config_data.get('model')  # Reads from YAML if present
)

# Priority: agent config model > default model
agent_model = config.model or self.default_model
```

### 3. Model Resolution Flow

```
1. Check agent YAML config for 'model' field
   ↓ (if not found)
2. Use LLM_MODEL environment variable
   ↓ (if not set)
3. Default to "gpt-4o"
```

### 4. Image Generation Model

**Location**: `backend/src/agents/tools/image_generator.py` line 54

The image generator tool uses a **fixed model** that cannot be changed per-agent:
```python
model="gemini-3-pro-image-preview"  # Nano Banana Pro
```

This is intentional - image generation always uses the specialized image model, regardless of which agent calls it.

## Summary

- **Default Model**: Set via `LLM_MODEL` environment variable in `backend/.env`
- **Per-Agent Override**: Uncomment `model:` line in agent YAML files
- **Image Generation**: Fixed to `gemini-3-pro-image-preview` (not configurable)

## Example Configuration

**backend/.env:**
```bash
LLM_MODEL=gemini-flash-latest
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

**backend/src/agents/config/director.yaml:**
```yaml
id: director
model: gemini-3-pro-preview  # Override: use powerful model for director
```

**backend/src/agents/config/synthesizer.yaml:**
```yaml
id: synthesizer
# No model specified - uses LLM_MODEL from .env (gemini-flash-latest)
```

**Result:**
- Director uses: `gemini-3-pro-preview`
- Synthesizer uses: `gemini-flash-latest` (from env)
- All other agents use: `gemini-flash-latest` (from env)

