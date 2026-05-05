# Per-Agent Model Selection

## Overview

The system supports per-agent model selection, allowing you to optimize for cost and performance by assigning different LLM models to different agents based on their needs.

**Important**: The `image_generator` is a **TOOL**, not an agent. It automatically uses `gemini-3-pro-image-preview` (Nano Banana Pro) for image generation. You don't configure its model - it's handled separately.

## How It Works

### Model Resolution Priority

1. **Agent YAML Config** - If an agent specifies a `model` field in its YAML config, that model is used
2. **Default Model** - Falls back to the default model (from organization settings, environment variables, or system default)

### Configuration

#### In Agent YAML Files

Add an optional `model` field to any agent's YAML configuration:

```yaml
id: director
name: Strategic Director
model: gemini-3-pro-preview  # Use powerful model for complex orchestration
role: C-level orchestrator...
tools: []
can_delegate_to:
  - business_sme
  # ...
```

#### Recommended Cost Optimization Strategy (Based on Latest Models - Jan 2025)

```yaml
# High-complexity agents - use powerful models
director:
  model: gemini-3-pro-preview  # $2/$12 - Best reasoning for orchestration

# Medium-complexity agents - use balanced models  
synthesizer:
  model: gemini-flash-latest  # $0.30/$2.50 - Good synthesis, much cheaper than pro
  # Note: Synthesizer calls image_generator tool (which uses gemini-3-pro-image-preview separately)

financial:
  model: gemini-flash-latest  # $0.30/$2.50 - Good at math and reasoning

risk:
  model: gemini-flash-latest  # $0.30/$2.50 - Needs analytical capabilities

market_research:
  model: gemini-flash-latest  # $0.30/$2.50 - Balanced for research

competitive_intel:
  model: gemini-flash-latest  # $0.30/$2.50 - Balanced for analysis

customer_intel:
  model: gemini-flash-latest  # $0.30/$2.50 - Balanced for analysis

# Simple agents - use cheapest models
business_sme:
  model: gemini-flash-lite-latest  # $0.10/$0.40 - Simple retrieval, doesn't need power

research_librarian:
  model: gemini-flash-lite-latest  # $0.10/$0.40 - Simple search and citation extraction
```

### Latest Model Pricing (Jan 2025)

#### Gemini Models
- **gemini-3-pro-preview**: $2.00/$12.00 (input/output per 1M tokens) - Most powerful, best reasoning
- **gemini-3-pro-image-preview** (Nano Banana Pro): $2.00/$0.134 per image - Used by image_generator tool
- **gemini-flash-latest**: $0.30/$2.50 - Balanced performance/cost
- **gemini-flash-lite-latest**: $0.10/$0.40 - Cheapest, good for simple tasks

#### OpenAI Models
- **gpt-4o**: ~$2.50/$10.00 (approximate) - Powerful, good alternative
- **gpt-4o-mini**: ~$0.15/$0.60 (approximate) - Cheaper option

### Image Generation

The `image_generator` tool is **NOT an agent** - it's a tool that agents (like the Synthesizer) call. It automatically uses:
- **Model**: `gemini-3-pro-image-preview` (Nano Banana Pro)
- **Cost**: $2.00 input / $0.134 per generated image
- **No configuration needed** - it's handled automatically

### Benefits

1. **Cost Optimization**: Use cheaper models (e.g., `gemini-flash-lite-latest` at $0.10/$0.40) for simple tasks
2. **Performance Optimization**: Use powerful models (e.g., `gemini-3-pro-preview` at $2/$12) for complex reasoning
3. **Flexibility**: Mix and match models based on agent requirements
4. **Backward Compatible**: Agents without `model` specified use the default

### Implementation Details

- Each agent gets its own `LLMClient` instance if it specifies a different model
- Agents sharing the same model share the same client instance (efficient)
- Model selection happens at agent initialization time
- No runtime overhead - models are determined once when agents are loaded
- Image generation uses separate Gemini image model (not configurable per agent)

