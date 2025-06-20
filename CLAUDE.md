# Claude Instructions for Love & Law Backend

# LoveAndLaw Conversational API – Backend Implementation

Things to consider:
- I don't have all the data ready in elastisearch, but it will be soon ready, create boilerplate for that only, so that when i prompt you to add the data, you can do it.

- Please innovate and come up with new ideas, and always refer latest documentation online for anything. Use your best judgement and don't be afraid to ask questions.

- Update this document as you go along, and add new sections as you go along. Edit the document as you go along.

- Please use the latest documentation and best practices for anything.

- Please use the latest version of the codebase and best practices for anything.

- If something need to be implentend like elasticsearch, or any other service, please create the boilerplate for that, so that when i prompt you to do that later, you can do it. Make sure you add/update in TODO.md file.

---

## 0 · Executive Goal

Deliver a 24 × 7 family‑law assistant that users willingly return to because it **empowers** them during difficult moments – never because it exploits their emotions. The assistant must:

1. Listen like a therapist – active listening, validation, crisis‑safe.
2. Guide like a paralegal – clear next steps, plain‑language explanations.
3. Match users to attorneys – personalised, local, budget‑aware options.
4. Learn continuously – every turn updates a living user profile that drives deeper personalisation.
5. Protect vulnerable users – ethical safeguards, privacy‑first design, human‑in‑the‑loop for crisis or complex legal needs.

All sizing, performance‑tuning, and other implementation specifics are left to engineering. This document defines *what* must exist and *how* the pieces fit together.

---

## 1 · Design Principles

| Principle          | Rationale                              | Architectural Mechanisms                                                                                     |
| ------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Autonomy**       | Users feel in control                  | Conversation can always be paused / ended; short ‘choice’ line injected each turn by Adaptive Empathy Prompt |
| **Competence**     | Visible progress builds confidence     | Milestone tracker; micro‑win celebrations emitted as front‑end events                                        |
| **Relatedness**    | Feeling understood sustains engagement | AllianceMeter scores (bond/goal/task) feed Adaptive Empathy; emotional timeline persisted                    |
| Transparency       | No hidden persuasion                   | AI disclosure banners; avoid over‑claiming                                                                   |
| Safety‑first       | Crisis overrides everything            | SafetyAgent interrupts flow when distress ≥ 8                                                                |
| Privacy‑by‑default | Legal data is sensitive                | Edge redaction; purpose‑limited data stores; GDPR tooling                                                    |

---

## 2 · High‑Level System Overview

```
   CloudFront (wss / https)
          │
    API Gateway  ← small admin REST
          │
┌────────────────── Chat Edge Service ──────────────────┐
│  • Owns WebSocket session                            │
│  • Redacts PII & stamps turn_id
│  • Streams AI tokens to client                       │
│  • Delegates reasoning to Therapeutic Engine         │
└───────────────────────────────────────────────────────┘
          │
   ──> Therapeutic Engine (LangGraph Orchestrator)
          │
   DynamoDB · OpenSearch · S3 · Metrics stack
```

Front‑end integrations (ElevenLabs, HeyGen, avatar streaming) remain client‑side and are out of scope.

---

## 3 · Therapeutic Engine – LangGraph Blueprint

### 3.1 Core State Schema (per turn)

```json
{
  'turn_id': 'uuid',
  'user_id': 'uuid',
  'stage': 'listening|advising|matching|safety_hold',
  'user_text': '…redacted…',
  'assistant_draft': 'streaming partial',
  'sentiment': 'pos|neu|neg',
  'enhanced_sentiment': 'admiration|amusement|anger|annoyance|approval|caring|confusion|curiosity|desire|disappointment|disapproval|disgust|embarrassment|excitement|fear|gratitude|grief|joy|love|nervousness|optimism|pride|realization|relief|remorse|sadness|surprise|neutral',
  'distress_score': 0-10,
  'engagement_level': 0-10,

  'alliance_bond': 0-10,
  'alliance_goal': 0-10,
  'alliance_task': 0-10,

  'legal_intent': ['divorce','custody',…],
  'facts': {'zip':'19104','budget':'$-$$',…},
  'progress_markers': ['petition_filed'],
  'memory_short': 'vector-id',
  'memory_long': 'profile-snapshot-id'
}
```

### 3.2 Agent Topology

| Phase | Agent                     | Key Responsibilities                                                                                                                           | Implementation Notes                         |
| ----- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| 0     | **SafetyAgent**           | Detect distress\_score & suicide/self‑harm patterns; trigger human hand‑off                                                                    | Highest priority; executes each turn         |
| 0     | **ProfileAgent**          | Fetch last N summaries + user preference sheet from UserProfiles; inject context into state                                                    | Parallel with SafetyAgent                    |
| 1     | **ListenerAgent**         | Llama 4 produces reflective draft; begins token stream after ≈ 30 tokens                                                                        | Tone informed by profile                     |
| 1     | **EmotionGauge**          | Groq Llama‑4 infers sentiment & engagement\_level (1‑10)                                                                                       | Lightweight prompt                           |
| 1     | **SignalExtract**         | Groq Llama‑4 extracts structured facts (zip, dates, relations, etc.) & embeds them                                                             | Replaces regex/spaCy                         |
| 1     | **AllianceMeter**       | Groq Llama‑4 model scoring bond / goal / task from latest exchange; writes to state                                                            | Mean latency ≤ 30 ms p95                     |
| 1     | ResearchAgent             | On‑demand external legal search when needed                                                                                                    | Timeout‑tolerant                             |
| 1     | MatcherAgent              | Elasticsearch (BM25 + dense vector) → up to 5 lawyer cards with match\_score; can trigger Exa or Perplexity research APIs based on user prompt | Skipped if distress > 6                      |
| 1.5   | **ReflectionAgent**       | Checks if reflection is appropriate; generates prompts for journey/emotional/decision reflection; provides progress insights                    | Triggers on milestones, emotional shifts     |
| 2     | **AdvisorAgent**          | Llama 4 composes final reply using: Listener draft + legal guidance + lawyer cards + progress nudges + reflection prompts                       | Uses Adaptive Empathy prompt described below |
| 2     | ProgressTracker           | Updates progress\_markers; schedules event‑based check‑ins via automations                                                                     |                                              |
| 2     | **SuggestionAgent**       | Generates 3–5 context‑aware “Suggested questions” users can click; showcases available tools (e.g., “What forms do I need to file next?”)      | Sends `suggestions` frame to client          |

### 3.3 Adaptive Empathy Prompt (excerpt)

*Inputs*: sentiment, distress\_score, engagement\_level, alliance\_bond/goal/task, user preferences.
*Behaviour*:

* Adjusts warmth, depth, and length in response to distress & engagement.
* **Always ends with an autonomy‑preserving choice line**, e.g. ‘Would you like to look at your next legal step, review lawyer options, or talk more about how you’re feeling?’
* Embeds MI techniques (open questions, reflective statements) when any alliance score ≤ 4.

### 3.4 Adaptive Routing Rules

1. **Crisis** – distress\_score ≥ 8 → SafetyAgent takes over (grounding tips + hotline + human transfer).
2. **Alliance Falter** – if bond ≤ 4 or goal ≤ 4 or task ≤ 4 **for two consecutive turns** → MI‑style re‑engagement:

   * ListenerAgent leads with empathic open question.
   * AdvisorAgent suppresses advice/matching until bond ≥ 6.
3. **Low Engagement** – engagement\_level ≤ 3 triggers extended empathy phase.
4. **Missing Key Facts** – clarifying question before MatcherAgent.

### 3.5 Feedback Loop

* Every turn: `[turn_id, engagement_level, bond, goal, task]` appended to Metrics stream.
* Nightly job highlights downward alliance trends → prompt/RLHF tweaks (never manipulative wording).
* Weekly human audit checks random 1 % conversations for ethical compliance.

### 3.6 Memory Strategy

| Layer             | Lifetime        | Store                                              | Purpose                                     |
| ----------------- | --------------- | -------------------------------------------------- | ------------------------------------------- |
| Short‑term        | Current session | In‑state                                           | Keeps prompts concise, coherent             |
| Rolling Summaries | Last 5‑10 turns | ConversationState → summariser cron → UserProfiles | Personalisation                             |
| Long‑term Profile | Sliding 90 days | UserProfiles                                       | Emotional timeline, preferences, milestones |

---

## 4 · Data Stores

| Store                            | Partition Key        | TTL      | Notes                                                |
| -------------------------------- | -------------------- | -------- | ---------------------------------------------------- |
| **ConversationState** (DynamoDB) | (user\_id, turn\_id) | 90 days  | Raw redacted text + assistant JSON + metrics         |
| **UserProfiles** (DynamoDB)      | user\_id             | 180 days | Summary blob, mood timeline, preferences, milestones |
| **lawyers\_v1** (OpenSearch)     | lawyer\_id           |  —       | BM25 fields + dense vector (Ada‑3 or in‑house)       |
| **S3**                           | path‑like            |  —       | Immutable logs, CSV uploads, nightly backups         |

---

## 5 · Turn Lifecycle (Happy Path)

1. **Client → API Gateway**: `{type:'user_msg', cid, text}`
2. **Chat Edge**

   * PII detection (Groq Llama‑4) & masking
   * turn\_id stamped; skeleton row written to ConversationState
   * Therapeutic Engine invoked
3. **Therapeutic Engine** runs Phases 0‑2 (Sections 3.1‑3.4)
4. **Chat Edge → Client**

   * Streams `ai_chunk` frames as soon as ListenerAgent tokens arrive
   * Sends `cards` frame once AdvisorAgent completes
5. **Async Post‑Turn Jobs**

   * Summariser cron updates UserProfiles if convo > 10 turns
   * Metrics & traces emitted to observability stack

Edge cases (safety\_hold, clarify, timeout) follow same handshake minus certain agents.

---

## 6 · API Contract

### 6.1 WebSocket Frames

| Direction     | Type                    | Payload                                       |
| ------------- | ----------------------- | --------------------------------------------- |
| client→server | `user_msg`              | `{cid, text}`                                 |
| server→client | `ai_chunk`              | `{cid, text_fragment}`                        |
| server→client | `cards`                 | `[ {id,name,firm,match_score,blurb,link} … ]` |
| server→client | `reflection`            | `{cid, reflection_type, reflection_insights}` |
| server→client | `suggestions`           | `{cid, suggestions:[text,…]}`                 |
| either        | `heartbeat`             | `{}`                                          |
| server→client | `error` / `session_end` | `{code, message}`                             |

### 6.2 REST Endpoints

| Method & Route            | Body                              | Result          |
| ------------------------- | --------------------------------- | --------------- |
| `POST /v1/match`          | `{facts:{zip, practice_area, …}}` | `{cards:[…]}`   |
| `POST /v1/lawyers/upload` | multipart/form‑data (CSV)         | `202 accepted`  |
| `GET  /v1/profile/:id`    | —                                 | `{profile:{…}}` |
| `PUT  /v1/profile/:id`    | `{name, email, preferences, …}`   | `{profile:{…}}` |
---

## 8 · Observability & Continuous Learning

* **Metrics** – p95 latency, distress distribution, engagement\_level, alliance\_bond/goal/task, match click‑through, retention cohorts.
* **Tracing** – AWS X‑Ray spans keyed by turn\_id.
* **Quality Audits** – weekly human review of 1 % randomly sampled conversations.
* **Model Refinement** – offline analysis of legal outcomes (form completion, lawyer contact) guides prompt/routing updates – *never* vanity engagement metrics alone.


---

## 10 · Handoff Checklist

* CloudFront & API Gateway stacks provisioned
* Chat Edge container with PII redaction live in staging
* LangGraph Therapeutic Engine (with AllianceMeter, Groq Llama‑4) deployed
* Dynamo tables & OpenSearch seeded
* Safety hotline flow approved by counsel
* Security & privacy review signed‑off
* Observability dashboards (Alliance Health panel) operational

---

## 11 · Success Metrics

*Primary*: Real‑world legal progress & self‑reported stress reduction.
*Secondary*: Alliance scores (bond/goal/task) stay stable or improve; no unexplained retention spikes.

*An engaging assistant empowers – it never entraps.*

---

## 12 · Implementation Status

### ✅ BACKEND IS FULLY FUNCTIONAL AND READY TO RUN!

The LoveAndLaw backend has been completely implemented with all core features working. You can start using it immediately by following the STARTUP_GUIDE.md.

### Recent Fixes (January 2025)
- **WebSocket Deployment Fix**: Resolved Terraform duplicate resource conflicts
  - Created consolidated WebSocket fix in `terraform/fixes/fix-websocket-consolidated.tf`
  - Implements Lambda-based WebSocket proxy for API Gateway integration
  - Includes ALB target group with sticky sessions for WebSocket support
  - All conflicting fix files renamed to `.backup` to prevent conflicts
  - Run `./scripts/aws/fix-websocket.sh` to apply the fix

### Completed Components ✅

#### Core Infrastructure
- **Project Structure**: Python-based backend with FastAPI and WebSockets
- **Core Models**: TurnState, ConversationState, UserProfile, LawyerCard with full schema validation
- **Database Services**: 
  - Elasticsearch for lawyer search (required)
  - DynamoDB for user profiles (optional with graceful fallback)
  - Redis for caching (optional with graceful fallback)
- **PII Redaction**: Presidio + LLM-based redaction service
- **WebSocket Handler**: Full duplex communication with streaming, reflection data, and suggestions
- **REST API**: Complete endpoints for lawyer matching, CSV upload, and profile management
- **Authentication**: JWT framework ready (currently in development mode for testing)

#### All Therapeutic Agents (Complete) ✅
- **SafetyAgent**: Crisis detection with keyword/pattern matching + LLM
- **ListenerAgent**: Llama 4 empathetic response generation with streaming
- **EmotionGauge**: Enhanced sentiment (28 emotions) and engagement analysis
- **AllianceMeter**: Bond/Goal/Task measurement for therapeutic alliance
- **SignalExtractAgent**: Structured data extraction from conversations
- **AdvisorAgent**: Adaptive response composition with integrated suggestions
- **ProfileAgent**: User profile management with caching and emotional timeline
- **ResearchAgent**: Context-aware legal research with synthesis
- **MatcherAgent**: Advanced lawyer matching with semantic search and personalization
- **ReflectionAgent**: Journey, emotional, and decision reflection prompts
- **ProgressTracker**: Milestone tracking with case-specific progress updates

#### All Legal Specialist Agents (Complete) ✅
- **CaseGeneralAgent**: Initial intake and intelligent routing to specialists
- **FamilyLawAgent**: General family law intake with comprehensive question flow
- **DivorceAndSeparationAgent**: Handles divorce/separation with child custody routing
- **ChildCustodyAgent**: Comprehensive custody information gathering
- **ChildSupportAgent**: Support role and financial information collection
- **PropertyDivisionAgent**: Asset and debt division specialist
- **SpousalSupportAgent**: Income and support factor assessment
- **DomesticViolenceAgent**: High-priority safety-first approach with resources
- **AdoptionAgent**: Complete adoption specialist with ICWA compliance
- **ChildAbuseAgent**: Safety-first with mandatory reporting reminders
- **GuardianshipAgent**: Handles both minor and adult guardianship
- **JuvenileDelinquencyAgent**: Youth justice with rehabilitation focus
- **PaternityPracticeAgent**: Time-sensitive parentage establishment
- **RestrainingOrdersAgent**: Immediate safety assessment and protection

#### System Integration
- **Therapeutic Engine**: LangGraph orchestration with all agents integrated
- **Legal Routing**: Intelligent routing from general intake to specialists
- **State Management**: Complete turn lifecycle with metrics and logging
- **Error Handling**: Graceful degradation when services unavailable
- **Development Tools**: Minimal startup scripts and test utilities

### Architecture Decisions  
- **Language**: Python 3.8+ for async support and ML ecosystem
- **Framework**: FastAPI for REST API and WebSocket handling
- **AI Model**: Groq Llama 4 (meta-llama/llama-4-maverick-17b-128e-instruct) for all agents
- **State Management**: LangGraph for conversation orchestration
- **Data Storage**: Elasticsearch (required), DynamoDB/Redis (optional with fallback)

### Ready for Production Features
- Graceful service degradation
- Development mode with auth bypass
- Comprehensive error handling
- Structured logging throughout
- WebSocket heartbeat and reconnection
- PII redaction on all user input
- Extensible agent architecture

### Recently Implemented ✅
- **Semantic Search with ELSER Model**: 
  - Index name updated to "love-and-law-001" as specified
  - Elasticsearch mapping includes semantic_text fields for profile, specialties, experience, and reviews
  - New upload script `scripts/upload_semantic_data.py` processes lawyer data with semantic fields
  - Enhanced search service with `advanced_semantic_search` method using ELSER queries
  - MatcherAgent intelligently chooses between standard and semantic search based on query complexity
  - Test script `test_semantic_search.py` to verify semantic search functionality

- **WebSocket Lambda Integration Fix**:
  - Lambda handler updated to use correct internal API endpoints (`/internal/websocket/message`)
  - Function renamed from `handler` to `lambda_handler` for AWS compatibility
  - Added support for multiple response messages with proper ordering
  - Created deployment script `deploy_lambda.sh` for easy updates
  - Test scripts: `test_lambda_websocket.py` (local), `test_production_websocket.py` (production)

### Not Yet Implemented (Future Enhancements)
- **Human mediator loop**: For complex custody disputes
- **Voice integration**: Client-side responsibility
- **Full authentication flow**: Framework exists, needs user registration
- **Production AWS deployment**: Currently optimized for local/development
- **Monitoring dashboards**: Metrics collection ready, needs visualization
- **RLHF integration**: For continuous improvement

### Known Issues & Solutions

#### WebSocket 502 Error in Production
The current deployment shows WebSocket connections failing with HTTP 502 error. This is because API Gateway WebSocket APIs cannot use HTTP_PROXY integration type with an Application Load Balancer (ALB).

**Three solution options available:**

1. **Lambda Proxy Solution** (Recommended for scalability)
   - Uses Lambda function to proxy WebSocket connections to ECS
   - Includes connection management via DynamoDB
   - Apply with: `./scripts/aws/fix-websocket.sh`
   - Files: `lambda_websocket_handler.py`, `src/api/websocket_internal.py`

2. **Network Load Balancer Solution** (Best for direct connections)
   - Creates NLB specifically for WebSocket traffic
   - Direct TCP connection to ECS containers
   - Apply with: `terraform apply -target=terraform/fixes/fix-websocket-integration.tf`

3. **ALB Sticky Sessions Solution** (Quick fix)
   - Adds sticky sessions to ALB for WebSocket persistence
   - Creates dedicated target group for `/ws` path
   - Apply with: `terraform apply -target=terraform/fixes/fix-alb-websocket.tf`

### Next Steps

See TODO.md for detailed implementation roadmap. Key priorities:

1. ✅ Elasticsearch data loading infrastructure ready
   - Run `./start-elasticsearch.sh` to start Elasticsearch in Docker
   - Run `python scripts/load_lawyer_data.py` to load data
   - Test with `python test_data_loading.py`
2. AWS deployment configuration
3. Complete authentication flow implementation
4. Add monitoring and metrics
5. Extract SuggestionAgent from AdvisorAgent if needed as separate component

### Data Setup

- **Data Directory**: `.data/` contains all CSV files (merged lawyers, reviews, scorecards, etc.)
- **Elasticsearch Setup**: 
  - **Elastic Cloud Configuration**:
    - URL: `https://b202eece25af4ba8a7cc89b05922ac28.us-east-2.aws.elastic-cloud.com:443`
    - API Key: Configured in `.env` as `ELASTICSEARCH_API_KEY`
    - Test connection: `python test_elasticsearch_connection.py`
  - **Local Development** (alternative):
    - Start with: `./start-elasticsearch.sh` (requires Docker)
    - URL: `http://localhost:9200`
  - Load data with: `source venv/bin/activate && python scripts/load_lawyer_data.py`
- **Testing**: Run `python test_data_loading.py` to verify setup

### AWS Deployment

- **Deployment Guide**: See `DEPLOYMENT_GUIDE.md` for complete AWS setup
- **Architecture**: See `ARCHITECTURE.md` for system design details
- **Infrastructure**: Terraform configuration in `terraform/` directory
- **Automation**: `deploy.sh` for one-command deployment with testing
