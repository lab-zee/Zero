# CrewDefine → LabZ Handoff Specification

This document defines what [CrewDefine](https://github.com/lab-zee/CrewDefine) must emit so a generated crew loads into LabZ (Zero) with no manual edits. It covers the `crew.yaml` manifest, answer-mode configuration, rich output composition, required CrewDefine code changes, and validation parity with Zero's `crew_validator.py`.

---

## Directory layout

```
<crew-name>/
  crew.yaml                 # crew manifest (required for non-default crews)
  README.md
  agents/
    director.yaml           # required
    synthesizer.yaml        # required
    <specialist-id>.yaml
  tools/                    # optional plugin stubs
    <tool-id>.py
```

Write `crew.yaml` at the **crew root**. Zero also accepts `agents/crew.yaml`; prefer root — `load-crew.sh` copies it to `backend/crews/active/crew.yaml`.

---

## 1. `crew.yaml` schema

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `name` | string | yes | Kebab-case; matches output directory |
| `display_name` | string | yes | UI label (chat header) |
| `description` | string | yes | One-paragraph summary |
| `default_answer_mode` | string | yes | Known mode id; must be in `answer_modes` |
| `answer_modes` | list | yes | Non-empty; crew-specific labels |
| `output_composition` | object | recommended | Drives synthesizer prompt drafting |

Each `answer_modes[]` entry: `id`, `label`, `description` (all required).

### Example — LabZ strategy (full modes)

```yaml
name: labz-strategy
display_name: Business Strategy
description: Multi-agent strategic advisory crew.
default_answer_mode: light
answer_modes:
  - id: summary
    label: Summary
    description: Concise executive briefing
  - id: light
    label: One-Pager
    description: Balanced memo with key evidence
  - id: extended
    label: Report
    description: Comprehensive analysis
  - id: project_plan
    label: 30-60-90
    description: Phased project plan
  - id: roadmap
    label: Roadmap
    description: Framework + implementation roadmap
output_composition:
  tabs: [summary, raw_data, visualizations, references]
  citations: required
  charts: when_quantitative
  tables: when_structured
  images: synthesizer_summary
  synthesizer_tools: [visualizer, extract_citations_structured, swot, generate_recommendations, image_generator]
```

### Example — Dinner planner (subset)

```yaml
name: dinner-planner
display_name: Dinner Planner
description: Meal planning from preferences and constraints.
default_answer_mode: summary
answer_modes:
  - id: summary
    label: Quick Plan
    description: Tonight's menu and prep time
  - id: light
    label: Full Menu
    description: Menu + shopping list + steps
  - id: extended
    label: Party Playbook
    description: Multi-course plan with make-ahead schedule
output_composition:
  tabs: [summary, raw_data]
  citations: optional
  charts: none
  tables: when_structured
  images: none
  synthesizer_tools: [calculator]
```

---

## 2. Answer modes

**Fixed ids** (do not invent new ones):

| `id` | Typical use |
| --- | --- |
| `summary` | Brief briefing |
| `light` | Default balanced memo |
| `extended` | Deep report |
| `project_plan` | 30-60-90 / milestones |
| `roadmap` | Framework + phased roadmap |

CrewDefine interview should **propose** modes by archetype (strategy → all five; lightweight assistant → summary + light). Custom **labels** per domain are encouraged.

Zero: `GET /api/crew` → `AnswerModeSelector` in chat.

---

## 3. Output composition (rich answers)

Zero renders via `TabbedMessageContent` when `content_structure` is set:

| Block | Tab | Source |
| --- | --- | --- |
| Markdown body | Summary | Synthesizer response |
| `visualizations[]` | Visualizations | `visualizer` tool (ECharts JSON) |
| `raw_data[]` | Data | `[DATA_START]...[DATA_END]` JSON blocks via response parser |
| `references[]` | References | `extract_citations_structured` + `## References` section |
| Generated images | Visualizations | `image_generator` → query files |

### Data blocks (`raw_data`)

Synthesizer (or specialists) may emit:

```text
[DATA_START]
{"label": "Shopping List", "type": "table", "value": [{"item": "eggs", "qty": 12}]}
[DATA_END]
```

Also accepted: a list of `{label, value}` objects, or a plain array of row objects (labeled "Data"). Markers are stripped from the summary tab.

### Essential building blocks

| Block | When to use | Synthesizer guidance |
| --- | --- | --- |
| **Summary markdown** | Always | Mode controls length/structure |
| **Citations** | Research, strategy | Inline `[1]` + `## References` |
| **Charts** | Quantitative analysis | `visualizer` + `[VISUALIZATION_START]` markers |
| **Tables** | Comparisons, lists, plans | JSON arrays → `raw_data` |
| **Images** | Strategic summaries | `image_generator` (~optional per crew) |
| **Recommendations** | Strategy crews | `generate_recommendations` tool |
| **SWOT / frameworks** | Strategy crews | `swot` tool |

### `output_composition` authoring fields

```yaml
output_composition:
  tabs: [summary, raw_data, visualizations, references]
  citations: required | optional | none
  charts: none | when_quantitative | always
  tables: none | when_structured | always
  images: none | when_requested | synthesizer_summary
  synthesizer_tools: [...]
```

CrewDefine persona drafter injects synthesizer prompt sections from this block.

---

## 4. CrewDefine changes needed

| File | Change |
| --- | --- |
| `schema.py` | `AnswerModeOption`, `OutputComposition`, manifest on `CrewConfig` |
| `generator.py` | Emit `crew.yaml`; README → `load-crew.sh` |
| `validator.py` | Zero-parity: director/synthesizer, manifest, plugins |
| `interview.py` + `prompts/interviewer.py` | Capture answer modes + output composition |
| `prompts/persona.py` | Synthesizer output sections from manifest |

---

## 5. Validation parity

Zero canonical validator: `backend/src/agents/crew_validator.py`  
CLI: `python3 backend/scripts/validate_crew.py <crew-dir>`  
`load-crew.sh` calls this before copying.

CrewDefine `validate` should match: agent schema, delegation, tools, plugins, `crew.yaml`, infrastructure agents.

**Short-term:** subprocess to Zero's script when `ZERO_BACKEND` env is set.  
**Long-term:** shared `labz-crew-schema` package.

---

## Handoff checklist

1. `crewdefine new` → manifest + agents + tools  
2. `crewdefine validate ./crews/<name>`  
3. `./scripts/load-crew.sh ./crews/<name>`  
4. `docker compose restart backend`  
5. Verify `GET /api/crew` + rich answers in chat
