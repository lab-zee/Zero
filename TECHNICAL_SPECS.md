# LabZ Technical Specifications - Next Release

**Version**: 1.0
**Date**: 2026-01-23
**Related**: IMPLEMENTATION_PLAN.md

---

## Table of Contents

1. [API Changes](#api-changes)
2. [Database Schema Changes](#database-schema-changes)
3. [SSE Event Types](#sse-event-types)
4. [Frontend Component Specifications](#frontend-component-specifications)
5. [Backend Tool Specifications](#backend-tool-specifications)
6. [Agent Configuration Changes](#agent-configuration-changes)
7. [Type Definitions](#type-definitions)

---

## API Changes

### New Endpoints

#### 1. Website Scraper Endpoint
```typescript
POST /api/organizations/scrape-website
Request: {
  url: string
}
Response: {
  success: boolean
  data?: {
    name?: string
    description?: string
    industry?: string
    org_type?: string
    purpose?: string
    goals_missions?: string
    website_url: string
    social_media_links?: {
      linkedin?: string
      twitter?: string
      facebook?: string
      instagram?: string
    }
    key_products_services?: string
    target_market?: string
    leadership_info?: string
    confidence_scores: {
      [field: string]: number  // 0-1 confidence for each extracted field
    }
  }
  error?: string
}
```

#### 2. Re-Ask Query Endpoint
```typescript
POST /api/llm/chat/reask
Request: {
  query_id: number
  answer_mode: 'summary' | 'light' | 'extended'
  organization_id: number
  user_id: number
}
Response: {
  query_id: number
  thread_id: number
  // Streams response via SSE like /chat/stream
}
```

#### 3. Update Thread Preferences
```typescript
PATCH /api/threads/{thread_id}/preferences
Request: {
  default_answer_mode?: 'summary' | 'light' | 'extended'
}
Response: {
  success: boolean
  thread: Thread
}
```

### Modified Endpoints

#### 1. Chat Stream Endpoint
```typescript
POST /api/llm/chat/stream
Request: {
  message: string
  organization_id: number
  user_id: number
  thread_id?: number
  file_ids?: number[]
  answer_mode?: 'summary' | 'light' | 'extended'  // NEW
}
Response: SSE Stream (see SSE Event Types section)
```

#### 2. Create Organization
```typescript
POST /api/organizations
Request: {
  name: string
  description?: string
  org_metadata?: OrganizationMetadata  // EXPANDED (see schema)
}
Response: {
  id: number
  name: string
  description: string
  org_metadata: OrganizationMetadata
  created_at: string
}
```

---

## Database Schema Changes

### 1. Organizations Table - New Columns

```sql
ALTER TABLE organizations ADD COLUMN website_url TEXT;
ALTER TABLE organizations ADD COLUMN social_media_links JSONB;
ALTER TABLE organizations ADD COLUMN key_products_services TEXT;
ALTER TABLE organizations ADD COLUMN target_market TEXT;
ALTER TABLE organizations ADD COLUMN leadership_info TEXT;

-- Or embedded in org_metadata JSONB (preferred approach):
-- org_metadata structure:
{
  "industry_name": "string",
  "org_type": "string",
  "purpose": "string",
  "goals_missions": "string",
  "current_limitations": "string",
  "resources_available": "string",
  "website_url": "string",  // NEW
  "social_media_links": {   // NEW
    "linkedin": "string",
    "twitter": "string",
    "facebook": "string",
    "instagram": "string"
  },
  "key_products_services": "string",  // NEW
  "target_market": "string",          // NEW
  "leadership_info": "string"         // NEW
}
```

### 2. Threads Table - New Columns

```sql
ALTER TABLE threads ADD COLUMN default_answer_mode VARCHAR(20) DEFAULT 'light';
ALTER TABLE threads ADD CONSTRAINT check_answer_mode
  CHECK (default_answer_mode IN ('summary', 'light', 'extended'));
```

### 3. Chat Queries Table - New Columns

```sql
ALTER TABLE chat_queries ADD COLUMN answer_mode VARCHAR(20) DEFAULT 'light';
ALTER TABLE chat_queries ADD COLUMN reask_of_query_id INTEGER REFERENCES chat_queries(id);
ALTER TABLE chat_queries ADD COLUMN content_structure JSONB;
ALTER TABLE chat_queries ADD COLUMN followup_questions JSONB;

-- Update citations column to new schema:
-- Old: citations: [{url, title, author, date, type}]
-- New: citations: {
--   "1": {url, title, author, date, type, excerpt},
--   "2": {url, title, author, date, type, excerpt}
-- }
```

### 4. Content Structure JSONB Schema

```typescript
content_structure: {
  summary: string           // Main text response
  raw_data?: string         // Tables, JSON, CSV
  visualizations?: [{       // ECharts configs
    id: string
    type: string
    config: object
  }]
  references?: {            // Numbered citations
    [number: string]: {
      url: string
      title: string
      author?: string
      date?: string
      type: 'web' | 'document' | 'news' | 'knowledge_base'
      excerpt?: string
    }
  }
}
```

### 5. Follow-up Questions JSONB Schema

```typescript
followup_questions: [{
  question: string
  rationale: string
}]
```

---

## SSE Event Types

### Existing Events
- `thread_created`: New thread ID
- `agent_start`: Agent beginning execution
- `trace_update`: Execution trace changes
- `agent_complete`: Agent finished
- `error`: Error messages

### New Events

#### 1. Progress Update Event
```typescript
event: progress_update
data: {
  type: 'progress_update'
  data: {
    agent_name: string
    agent_id: string
    message: string        // Human-readable progress message
    context_type: 'delegation_reasoning' | 'intermediate_finding' | 'tool_result'
  }
  timestamp: string
}
```

#### 2. Clarification Needed Event
```typescript
event: clarification_needed
data: {
  type: 'clarification_needed'
  data: {
    questions: string[]           // Clarifying questions to ask user
    missing_info: string[]        // What information is missing
    can_partially_answer: boolean // Can proceed with disclaimer?
  }
  timestamp: string
}
```

#### 3. Follow-up Suggestions Event
```typescript
event: followup_suggestions
data: {
  type: 'followup_suggestions'
  data: {
    suggestions: [{
      question: string
      rationale: string
    }]
  }
  timestamp: string
}
```

#### 4. Content Structure Event
```typescript
event: content_structure
data: {
  type: 'content_structure'
  data: {
    has_tabs: boolean
    tabs: ('summary' | 'raw_data' | 'visualizations' | 'references')[]
  }
  timestamp: string
}
```

---

## Frontend Component Specifications

### 1. TabbedMessageContent Component

**File**: `frontend/src/components/TabbedMessageContent.tsx`

**Props**:
```typescript
interface TabbedMessageContentProps {
  contentStructure: {
    summary: string
    raw_data?: string
    visualizations?: Visualization[]
    references?: Record<string, Citation>
  }
  isStreaming?: boolean
}
```

**Behavior**:
- Render Chakra UI Tabs
- Default to Summary tab
- Hide tabs with no content
- Show skeleton loaders during streaming
- Parse summary for inline citations `[1]`, `[2]`
- Replace citation markers with InlineCitation components

**Layout**:
```
┌─────────────────────────────────────┐
│ [Summary] [Raw Data] [Visualizations] [References] │
├─────────────────────────────────────┤
│                                     │
│  Content based on selected tab      │
│                                     │
└─────────────────────────────────────┘
```

---

### 2. InlineCitation Component

**File**: `frontend/src/components/InlineCitation.tsx`

**Props**:
```typescript
interface InlineCitationProps {
  citationNumber: number
  citation: Citation
  onClickScroll: (number: number) => void
}
```

**Rendering**:
- Superscript number in blue
- Clickable link
- Tooltip on hover with citation preview
- Example: `Some fact[1]` where `[1]` is InlineCitation

---

### 3. ReferenceList Component

**File**: `frontend/src/components/ReferenceList.tsx`

**Props**:
```typescript
interface ReferenceListProps {
  citations: Record<string, Citation>
  highlightedNumber?: number
}
```

**Rendering**:
```
1. Author, A. (2025). Article Title. Publication. https://url.com
   "Excerpt from the source..."

2. Another Author (2024). Book Title. Publisher.
   Link to document
```

---

### 4. ProgressTimeline Component

**File**: `frontend/src/components/ProgressTimeline.tsx`

**Props**:
```typescript
interface ProgressTimelineProps {
  events: ProgressEvent[]
  isLive?: boolean
}

interface ProgressEvent {
  agent_name: string
  message: string
  timestamp: string
  context_type: string
}
```

**Layout**:
```
┌─────────────────────────────────────┐
│ ● Strategic Director                │
│   "Delegating to Market Research    │
│    to analyze competitor landscape" │
│                                     │
│ ● Market Research Specialist        │
│   "Found 5 key competitors in       │
│    the enterprise SaaS space"       │
│                                     │
│ ● Financial Analyst                 │
│   "Analyzing revenue projections..." │
└─────────────────────────────────────┘
```

---

### 5. ClarificationModal Component

**File**: `frontend/src/components/ClarificationModal.tsx`

**Props**:
```typescript
interface ClarificationModalProps {
  isOpen: boolean
  questions: string[]
  missing_info: string[]
  can_partially_answer: boolean
  onSubmitAnswers: (answers: Record<string, string>) => void
  onSkip: () => void
  onCancel: () => void
}
```

**Layout**:
```
┌─────────────────────────────────────┐
│  More Information Needed            │
├─────────────────────────────────────┤
│  To provide an accurate answer,     │
│  please provide:                    │
│                                     │
│  Q1: What is your target market?    │
│  [ Input field                   ]  │
│                                     │
│  Q2: What is your current revenue?  │
│  [ Input field                   ]  │
│                                     │
│  [Answer & Continue] [Skip] [Cancel]│
└─────────────────────────────────────┘
```

---

### 6. OrganizationWizard Component

**File**: `frontend/src/components/OrganizationWizard.tsx`

**Props**:
```typescript
interface OrganizationWizardProps {
  isOpen: boolean
  onClose: () => void
  onComplete: (org: Organization) => void
}
```

**Steps**:
1. **Website & Name**
   - Input: Website URL
   - Input: Organization name
   - Button: "Next"

2. **Scraping in Progress**
   - Loading spinner
   - "Analyzing website..."
   - Progress messages

3. **Review Scraped Data**
   - Editable form with all org_metadata fields
   - Pre-populated with scraped data
   - Confidence indicators (High/Medium/Low)
   - Button: "Looks good" | "Back"

4. **Confirmation**
   - Summary of org details
   - Button: "Create Organization"

---

### 7. ReAskButton Component

**File**: `frontend/src/components/ReAskButton.tsx`

**Props**:
```typescript
interface ReAskButtonProps {
  queryId: number
  currentMode: 'summary' | 'light' | 'extended'
  onReAsk: (mode: AnswerMode) => void
}
```

**Rendering**:
- Menu button with options
- "Re-ask as Summary" (disabled if current mode)
- "Re-ask as Light" (disabled if current mode)
- "Re-ask as Extended" (disabled if current mode)

---

### 8. FollowUpSuggestions Component

**File**: `frontend/src/components/FollowUpSuggestions.tsx`

**Props**:
```typescript
interface FollowUpSuggestionsProps {
  suggestions: FollowUpQuestion[]
  onSelectQuestion: (question: string) => void
}

interface FollowUpQuestion {
  question: string
  rationale: string
}
```

**Layout**:
```
Suggested next steps:
┌─────────────────────────────────────┐
│ → What are the key risks to this    │
│   strategy?                         │
├─────────────────────────────────────┤
│ → How does this compare to our      │
│   competitors?                      │
├─────────────────────────────────────┤
│ → What resources are needed for     │
│   implementation?                   │
└─────────────────────────────────────┘
```

---

## Backend Tool Specifications

### 1. Website Scraper Tool

**File**: `backend/src/agents/tools/website_scraper.py`

**Function Signature**:
```python
def scrape_website(url: str) -> Dict[str, Any]:
    """
    Scrapes a website to extract organization information.

    Args:
        url: Website URL to scrape

    Returns:
        {
            'name': str,
            'description': str,
            'industry': str,
            'org_type': str,
            'purpose': str,
            'goals_missions': str,
            'social_media_links': dict,
            'key_products_services': str,
            'target_market': str,
            'leadership_info': str,
            'confidence_scores': dict
        }
    """
```

**Implementation Approach**:
1. Fetch HTML content using `requests` or `httpx`
2. Parse HTML with `BeautifulSoup`
3. Extract:
   - Meta tags (description, keywords)
   - About page content
   - Leadership/Team page
   - Social media links from footer/header
   - Product/service descriptions
4. Use LLM to analyze content and structure information
5. Return JSON with confidence scores

**Error Handling**:
- Timeout after 30 seconds
- Handle invalid URLs
- Handle unreachable sites
- Return partial data with low confidence if needed

---

### 2. Information Validator Tool

**File**: `backend/src/agents/tools/information_validator.py`

**Function Signature**:
```python
def validate_information_sufficiency(
    question: str,
    org_metadata: Dict[str, Any],
    conversation_history: List[Dict],
    attached_files: List[Dict]
) -> Dict[str, Any]:
    """
    Validates if sufficient information exists to answer question.

    Returns:
        {
            'status': 'sufficient' | 'insufficient' | 'partial',
            'missing_info': List[str],
            'suggested_questions': List[str],
            'confidence': float
        }
    """
```

**Validation Logic**:
1. Analyze question requirements
2. Check available context:
   - Organization metadata completeness
   - Conversation history relevance
   - Attached files content
3. Identify gaps
4. Generate clarifying questions if needed
5. Return status and recommendations

**Examples**:
- Question: "What's our 2026 revenue forecast?"
  - Check: Historical revenue data, growth metrics, market conditions
  - If missing: Status = 'insufficient', questions = ["What was your revenue in 2023-2025?", "What growth rate are you targeting?"]

---

### 3. Follow-up Generator Tool

**File**: `backend/src/agents/tools/followup_generator.py`

**Function Signature**:
```python
def generate_followup_questions(
    question: str,
    answer: str,
    org_context: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    Generates relevant follow-up questions.

    Returns:
        [
            {
                'question': str,
                'rationale': str
            },
            ...
        ]
    """
```

**Generation Strategy**:
1. Analyze answer content for:
   - Mentioned but unexplored topics
   - Next logical steps
   - Actionable insights that need detail
   - Risks or opportunities highlighted
2. Consider org context for relevance
3. Generate 3-5 specific, actionable questions
4. Provide brief rationale for each

---

## Agent Configuration Changes

### 1. Strategic Director (`director.yaml`)

**Add to Instructions**:
```yaml
instructions: |
  # ... existing instructions ...

  # Information Validation
  - ALWAYS validate information sufficiency before delegating to specialists
  - Use the information_validator tool to check if you have enough context
  - If information is insufficient, ask the user for clarification
  - Do not make assumptions or hallucinate data

  # Progress Communication
  - Before delegating to a specialist, briefly explain your reasoning
  - Example: "I'm delegating to Market Research Specialist to analyze the competitive landscape"
  - Share key insights as you gather them from specialists

  # Answer Mode Awareness
  - Adjust your delegation strategy based on the requested answer_mode
  - Summary mode: Focus on high-level insights, minimal delegation
  - Light mode: Balanced approach, key specialists only
  - Extended mode: Comprehensive analysis, all relevant specialists
```

**Add to Tools**:
```yaml
tools:
  # ... existing tools ...
  - information_validator
```

---

### 2. Strategy Synthesizer (`synthesizer.yaml`)

**Update Instructions**:
```yaml
instructions: |
  # ... existing instructions ...

  # Text-First Responses
  - Prioritize clear, comprehensive text summaries
  - Only generate visualizations when they add significant value
  - Do NOT generate images for every response (costly)
  - Use visualizations for: comparisons, trends, complex data relationships

  # Citations Required
  - Use inline citations for all factual claims: [1], [2], etc.
  - Include complete reference list at the end
  - Format: [number] Author (Date). Title. Source URL
  - Every citation must be traceable to a source

  # Answer Mode Formatting
  - Summary mode: 2-3 paragraphs maximum, executive-level insights
  - Light mode: Balanced detail with key evidence and recommendations
  - Extended mode: Comprehensive analysis with full context, multiple perspectives

  # Follow-up Questions
  - After synthesizing, consider what logical next questions the user might ask
  - Call followup_generator tool with your final response
```

**Add to Tools**:
```yaml
tools:
  # ... existing tools ...
  - followup_generator
```

---

### 3. Image Generator Tool Prompt Update

**Update `image_generator.py`**:
```python
base_prompt = """
Generate a professional, corporate-style strategic visualization.

Design Guidelines:
- Use clean, professional design aesthetic similar to Atlassian Design System or Material Design
- Professional color palettes (blues, grays, muted tones)
- Minimal decorative elements
- Data-focused charts and diagrams
- Suitable for executive presentations
- Avoid overly playful or casual elements
- Infographic style acceptable for strategic concepts
- Clear typography and hierarchy

Context: {context}
"""
```

---

## Type Definitions

### Frontend Types (`frontend/src/services/api.ts`)

```typescript
export type AnswerMode = 'summary' | 'light' | 'extended'

export interface OrganizationMetadata {
  industry_name?: string
  org_type?: string
  purpose?: string
  goals_missions?: string
  current_limitations?: string
  resources_available?: string
  website_url?: string
  social_media_links?: {
    linkedin?: string
    twitter?: string
    facebook?: string
    instagram?: string
  }
  key_products_services?: string
  target_market?: string
  leadership_info?: string
}

export interface ContentStructure {
  summary: string
  raw_data?: string
  visualizations?: Visualization[]
  references?: Record<string, Citation>
}

export interface Citation {
  url: string
  title: string
  author?: string
  date?: string
  type: 'web' | 'document' | 'news' | 'knowledge_base'
  excerpt?: string
}

export interface FollowUpQuestion {
  question: string
  rationale: string
}

export interface ChatQueryResponse {
  id: number
  message: string
  response: string
  content_structure?: ContentStructure
  citations?: Record<string, Citation>
  followup_questions?: FollowUpQuestion[]
  answer_mode: AnswerMode
  reask_of_query_id?: number
  execution_trace?: ExecutionTrace
  created_at: string
}

export interface Thread {
  id: number
  name: string
  organization_id: number
  default_answer_mode: AnswerMode
  created_at: string
}
```

### Backend Types (`backend/src/models.py`)

```python
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, Enum as SQLEnum

class AnswerMode(str, Enum):
    SUMMARY = "summary"
    LIGHT = "light"
    EXTENDED = "extended"

class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    default_answer_mode = Column(SQLEnum(AnswerMode), default=AnswerMode.LIGHT)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatQuery(Base):
    __tablename__ = "chat_queries"

    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)
    response = Column(Text)
    answer_mode = Column(SQLEnum(AnswerMode), default=AnswerMode.LIGHT)
    reask_of_query_id = Column(Integer, ForeignKey("chat_queries.id"), nullable=True)
    content_structure = Column(JSON, nullable=True)
    citations = Column(JSON, nullable=True)  # Schema: {"1": {...}, "2": {...}}
    followup_questions = Column(JSON, nullable=True)  # Schema: [{"question": "...", "rationale": "..."}]
    execution_trace = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Configuration & Environment Variables

### New Environment Variables (Optional)

```bash
# Website Scraper
SCRAPER_TIMEOUT=30  # Seconds before timeout
SCRAPER_MAX_PAGES=5  # Max pages to scrape per domain

# Information Validator
VALIDATOR_CONFIDENCE_THRESHOLD=0.7  # Minimum confidence to proceed without clarification

# Image Generation
IMAGE_GEN_DEFAULT_DISABLED=false  # Set true to require explicit image generation requests
```

---

## Error Handling Patterns

### Frontend Error States

1. **Website Scraping Failure**:
   - Show error message: "Unable to scrape website. Please enter details manually."
   - Allow wizard to proceed with manual entry
   - Log error for debugging

2. **Clarification Timeout**:
   - If user doesn't respond to clarification in 5 minutes, allow proceeding with disclaimer
   - Show banner: "Answer provided with limited information. Results may be less accurate."

3. **Re-Ask Failure**:
   - If re-ask fails, show original answer
   - Error toast: "Unable to regenerate answer. Please try again."

### Backend Error Handling

1. **Tool Execution Errors**:
   - Catch exceptions in tool execution
   - Return error to agent with context
   - Agent decides whether to retry or fail gracefully

2. **LLM Rate Limits**:
   - Implement exponential backoff
   - Queue requests if necessary
   - Show "High demand, please wait" message to user

3. **Database Errors**:
   - Transaction rollback on failure
   - Log error details
   - Return user-friendly error message

---

## Performance Optimization Notes

### 1. Lazy Loading
- Load ProgressTimeline only when expanded
- Load ReferenceList only when References tab selected
- Defer follow-up question generation until after response complete

### 2. Caching
- Cache website scraping results for 24 hours (Redis or in-memory)
- Cache organization metadata in frontend state
- Cache common validation results

### 3. Streaming Optimization
- Send content_structure event early to prepare tabs
- Stream summary content progressively
- Load visualizations after text complete

---

## Testing Checklist

### Unit Tests
- [ ] website_scraper: Valid URLs, invalid URLs, timeouts
- [ ] information_validator: Sufficient, insufficient, partial cases
- [ ] followup_generator: Question quality and relevance
- [ ] Response parser: Citation extraction, content structuring
- [ ] InlineCitation: Rendering and click behavior
- [ ] TabbedMessageContent: Tab visibility logic

### Integration Tests
- [ ] Complete onboarding wizard flow
- [ ] Answer validation → clarification → re-run
- [ ] Re-ask with different modes
- [ ] Citation flow: tool → agent → response → display
- [ ] Progress updates during execution

### E2E Tests
- [ ] New organization with website scraping
- [ ] Ask question → receive clarification → provide answer → get response
- [ ] Click follow-up suggestion → get answer
- [ ] Change answer mode → see difference in response length
- [ ] View inline citation → scroll to reference

---

**Document Version**: 1.0
**Last Updated**: 2026-01-23
**Status**: Ready for Development
