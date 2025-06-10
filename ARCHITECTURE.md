# LoveAndLaw Backend Architecture

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Infrastructure Architecture](#infrastructure-architecture)
4. [Application Architecture](#application-architecture)
5. [Data Architecture](#data-architecture)
6. [Security Architecture](#security-architecture)
7. [Integration Architecture](#integration-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Monitoring & Observability](#monitoring--observability)
10. [Development & Maintenance](#development--maintenance)

## Overview

LoveAndLaw is an AI-powered therapeutic conversational support system for family law issues. The system provides empathetic listening, legal guidance, and lawyer matching services through a WebSocket-based real-time interface.

### Key Features
- **Therapeutic Conversations**: AI agents providing empathetic support
- **Legal Guidance**: Specialized agents for different family law areas
- **Lawyer Matching**: Semantic search with personalized recommendations
- **Real-time Communication**: WebSocket streaming for natural conversations
- **Safety First**: Crisis detection and human handoff capabilities

### Technology Stack
- **Backend**: Python 3.8+, FastAPI, LangGraph
- **AI/ML**: Groq Llama 4, Anthropic Claude, ELSER semantic search
- **Infrastructure**: AWS (ECS, Lambda, API Gateway, DynamoDB, ElastiCache)
- **Search**: Elasticsearch with semantic capabilities
- **Monitoring**: CloudWatch, X-Ray

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CloudFront CDN                           │
│                    (wss://websocket & https://api)              │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│  ┌─────────────────┐        ┌──────────────────────────┐       │
│  │ WebSocket API   │        │      REST API            │       │
│  │ ($connect, etc) │        │  (/health, /match, etc)  │       │
│  └────────┬────────┘        └──────────┬───────────────┘       │
│           │                             │                        │
│           ▼                             ▼                        │
│  ┌─────────────────┐        ┌──────────────────────────┐       │
│  │ Lambda Handler  │        │   VPC Link to ALB        │       │
│  │ (WebSocket)     │        │                          │       │
│  └────────┬────────┘        └──────────┬───────────────┘       │
└───────────┼─────────────────────────────┼───────────────────────┘
            │                             │
            ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Load Balancer                     │
│                         (Internal ALB)                           │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ECS Fargate Service                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                  FastAPI Application                    │    │
│  │  ┌──────────┐  ┌─────────────┐  ┌────────────────┐   │    │
│  │  │   API    │  │  WebSocket  │  │  Therapeutic   │   │    │
│  │  │ Handlers │  │   Handler   │  │    Engine      │   │    │
│  │  └──────────┘  └─────────────┘  └────────────────┘   │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
         ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
         │ Elasticsearch│ │   DynamoDB   │ │    Redis     │
         │   (Search)   │ │  (Profiles)  │ │   (Cache)    │
         └──────────────┘ └──────────────┘ └──────────────┘
```

### Component Interactions

1. **REST API Flow**:
   ```
   Client → CloudFront → API Gateway → ALB → ECS → Backend Services
   ```

2. **WebSocket Flow** (Lambda Proxy Architecture):
   ```
   Client → API Gateway WebSocket → Lambda Handler → DynamoDB (connection state)
                                         ↓
                                   HTTP to ALB/ECS
                                         ↓
                                   Therapeutic Engine
                                         ↓
                                   Lambda Callback
                                         ↓
                                   API Gateway → Client
   ```

3. **Message Processing Flow**:
   ```
   User Message → PII Redaction → Therapeutic Engine → Agent Orchestration → Response Generation → Streaming Response
   ```

4. **Data Flow**:
   ```
   User Input → Signal Extraction → Profile Update → Context Building → AI Processing → Response
   ```

## Infrastructure Architecture

### AWS Services Used

#### Compute
- **ECS Fargate**: Serverless container hosting for main API
  - Cluster: `loveandlaw-production-cluster`
  - Service: `loveandlaw-api`
  - Task Definition: Auto-scaling enabled
  - Platform: ARM64 Linux (cost-optimized)
  - Current Revision: 24

- **Lambda**: WebSocket proxy handler
  - Function: `loveandlaw-production-websocket-handler`
  - Runtime: Python 3.11
  - Memory: 256MB
  - Timeout: 30 seconds
  - VPC: Connected to ECS VPC for internal communication

#### Networking
- **VPC**: Custom VPC with public/private subnets
  - CIDR: 10.0.0.0/16
  - Availability Zones: 2 for HA
  - NAT Gateway for private subnet internet access

- **Application Load Balancer**: Internal ALB for ECS
  - Target Group: ECS tasks
  - Health Check: `/health` endpoint
  - Port: 80

- **API Gateway**: Public-facing API endpoints
  - REST API: HTTP integration via VPC Link
  - WebSocket API: Lambda integration

#### Storage & Database
- **DynamoDB**: User profiles and conversation state
  - Tables: 
    - `loveandlaw-production-profiles`
    - `loveandlaw-production-conversations`
    - `loveandlaw-websocket-connections`
  - Global Secondary Indexes for queries
  - TTL enabled for data retention

- **Elasticsearch**: Lawyer search and matching
  - Managed Elasticsearch/OpenSearch
  - Semantic search with ELSER
  - Index: `love-and-law-001`

- **Redis/ElastiCache**: Session and response caching
  - Cluster mode disabled
  - Node type: cache.t3.micro

- **S3**: Static assets and logs
  - Buckets: logs, backups, uploads

#### Security & Secrets
- **Secrets Manager**: API keys and credentials
  - Secret: `loveandlaw/production/api-keys`
  - Auto-rotation disabled

- **IAM Roles**: Least-privilege access
  - ECS Task Execution Role
  - ECS Task Role
  - Lambda Execution Role

#### Monitoring
- **CloudWatch**: Logs, metrics, and alarms
  - Log Groups: `/ecs/loveandlaw`, `/aws/lambda/loveandlaw`
  - Custom metrics for business KPIs
  - Alarms for error rates and latency

- **X-Ray**: Distributed tracing
  - Service map visualization
  - Request flow analysis

### Network Architecture

```
Internet
    │
    ▼
CloudFront (Edge)
    │
    ▼
API Gateway (Public Subnet)
    │
    ├─────────────┐
    ▼             ▼
Lambda        VPC Link
    │             │
    │             ▼
    │         ALB (Private Subnet)
    │             │
    │             ▼
    │         ECS Tasks (Private Subnet)
    │             │
    └─────────────┴────────────┐
                               ▼
                    Data Layer (Private Subnet)
                    - DynamoDB (VPC Endpoint)
                    - Elasticsearch
                    - Redis
```

## Application Architecture

### Core Components

#### 1. API Layer (`src/api/`)
- **FastAPI Application**: Main REST API and WebSocket handling
- **Authentication**: JWT-based with development bypass
- **Endpoints**:
  - Health check: `GET /health`
  - Lawyer matching: `POST /v1/match`
  - Profile management: `GET /v1/profile/{id}`
  - WebSocket: Production uses API Gateway WebSocket API

#### 2. Therapeutic Engine (`src/core/`)
- **LangGraph Orchestration**: State machine for conversation flow
- **Turn Processing**: Manages conversation lifecycle
- **Agent Coordination**: Routes to appropriate specialists

#### 3. Agent System (`src/agents/`)

##### Base Agents
- **SafetyAgent**: Crisis detection and intervention
- **ListenerAgent**: Empathetic response generation
- **AdvisorAgent**: Integrated guidance and suggestions
- **ProfileAgent**: User profile management
- **MatcherAgent**: Lawyer recommendation engine

##### Specialist Agents (`src/agents/legal_specialists/`)
- **CaseGeneralAgent**: Initial intake and routing
- **DivorceAndSeparationAgent**: Divorce proceedings
- **ChildCustodyAgent**: Custody arrangements
- **DomesticViolenceAgent**: Safety-first approach
- **AdoptionAgent**: Adoption processes
- **PropertyDivisionAgent**: Asset division
- And 8 more specialized agents...

##### Analysis Agents
- **EmotionGauge**: Sentiment analysis (28 emotions)
- **AllianceMeter**: Therapeutic alliance scoring
- **SignalExtractAgent**: Structured data extraction
- **ProgressTracker**: Milestone tracking
- **ReflectionAgent**: Journey insights

### State Management

#### Turn State Schema
```python
{
    'turn_id': str,           # Unique turn identifier
    'user_id': str,           # User identifier
    'stage': str,             # Current conversation stage
    'user_text': str,         # Redacted user input
    'assistant_draft': str,   # AI response in progress
    'sentiment': str,         # Basic sentiment
    'enhanced_sentiment': str,# Detailed emotion
    'distress_score': float,  # 0-10 scale
    'engagement_level': float,# 0-10 scale
    'alliance_bond': float,   # Therapeutic bond score
    'alliance_goal': float,   # Goal alignment score
    'alliance_task': float,   # Task agreement score
    'legal_intent': List[str],# Detected legal issues
    'facts': Dict,            # Extracted facts
    'progress_markers': List, # Completed milestones
}
```

### Agent Orchestration Flow

```
User Input
    │
    ▼
┌─────────────────┐
│ Safety Check    │ ← (Parallel)
│ Profile Load    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PII Redaction   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ Parallel Analysis           │
│ - EmotionGauge              │
│ - SignalExtract             │
│ - AllianceMeter             │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────┐
│ Listener Draft  │ ← Begin streaming
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Legal Routing   │ → Specialist Agent
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Matcher Agent   │ ← If appropriate
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Advisor Final   │ ← Integrated response
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Progress Update │
│ Suggestions Gen │
└─────────────────┘
```

## Data Architecture

### Data Stores

#### 1. Elasticsearch
- **Purpose**: Lawyer search and matching
- **Index Structure**:
  ```json
  {
    "lawyer_id": "keyword",
    "name": "text",
    "firm": "text",
    "specialties": "text",
    "location": {
      "city": "keyword",
      "state": "keyword",
      "zip": "keyword"
    },
    "semantic_profile": "semantic_text",
    "ratings": "nested",
    "vector_embedding": "dense_vector"
  }
  ```

#### 2. DynamoDB
- **UserProfiles Table**:
  - Partition Key: `user_id`
  - Attributes: preferences, emotional_timeline, milestones
  - TTL: 180 days

- **ConversationState Table**:
  - Partition Key: `user_id`, Sort Key: `turn_id`
  - Attributes: turn_data, metrics, timestamps
  - TTL: 90 days

#### 3. Redis Cache
- **Session Data**: WebSocket connection state
- **Response Cache**: Common queries and responses
- **Profile Cache**: Frequently accessed user profiles

### Data Flow Patterns

1. **Write Path**:
   ```
   User Input → PII Redaction → State Storage → Profile Update → Cache Update
   ```

2. **Read Path**:
   ```
   Cache Check → Database Query → Data Assembly → Response Generation
   ```

3. **Search Path**:
   ```
   Query Analysis → Semantic/Keyword Search → Ranking → Personalization → Results
   ```

## Security Architecture

### Security Layers

1. **Network Security**:
   - CloudFront with AWS Shield
   - WAF rules for common attacks
   - Private subnets for compute/data
   - Security groups with least privilege

2. **Application Security**:
   - JWT authentication
   - API rate limiting
   - Input validation
   - PII redaction at edge

3. **Data Security**:
   - Encryption at rest (all services)
   - Encryption in transit (TLS 1.2+)
   - Secrets Manager for credentials
   - IAM roles for service access

4. **Compliance**:
   - GDPR-ready with data retention
   - PII handling compliance
   - Audit logging enabled
   - Data isolation per user

### Authentication Flow

```
Client Request
    │
    ▼
API Gateway ← JWT Validation
    │
    ▼
Lambda/ECS ← IAM Role Assumption
    │
    ▼
Backend Services ← Service-to-Service Auth
    │
    ▼
Data Access ← Resource-based Permissions
```

## Integration Architecture

### External Services

1. **AI Services**:
   - **Groq API**: Llama 4 for all therapeutic agents
   - **Anthropic API**: Fallback for complex reasoning
   - **Elasticsearch ELSER**: Semantic search

2. **Monitoring Services**:
   - **CloudWatch**: Native AWS integration
   - **SNS**: Alert notifications
   - **EventBridge**: Scheduled tasks

### Integration Patterns

1. **Circuit Breaker**: For external API calls
   ```python
   @circuit_breaker(failure_threshold=5, timeout=60)
   async def call_groq_api():
       # API call with automatic failover
   ```

2. **Retry Logic**: Exponential backoff
   ```python
   @retry(max_attempts=3, backoff=exponential)
   async def resilient_call():
       # Retryable operation
   ```

3. **Graceful Degradation**:
   - DynamoDB unavailable → In-memory fallback
   - Redis unavailable → Direct database queries
   - AI API unavailable → Cached responses

## Deployment Architecture

### CI/CD Pipeline

```
Developer Push
    │
    ▼
GitHub Actions Trigger
    │
    ├──► Run Tests
    ├──► Build Docker Image
    ├──► Push to ECR
    ├──► Update ECS Task Definition
    ├──► Deploy to ECS
    └──► Run Production Tests
```

### Deployment Scripts

1. **deploy.sh**: Complete deployment automation
   - Syntax validation
   - Docker build and push
   - ECS service update
   - Lambda update
   - Health verification
   - Production testing

2. **GitHub Actions**: Automated on push to main
   - `.github/workflows/deploy.yml`
   - Runs full test suite
   - Deploys on success
   - Sends notifications

### Environment Management

- **Development**: Local Docker setup
- **Staging**: Not currently implemented
- **Production**: Full AWS infrastructure

## Monitoring & Observability

### Metrics Collection

1. **Business Metrics**:
   - User engagement levels
   - Alliance scores (bond/goal/task)
   - Conversation completion rates
   - Lawyer match click-through rates

2. **Technical Metrics**:
   - API latency (p50, p95, p99)
   - Error rates by endpoint
   - WebSocket connection duration
   - Agent processing times

3. **Infrastructure Metrics**:
   - ECS task health
   - Lambda invocation errors
   - Database query performance
   - Cache hit rates

### Logging Strategy

```
Application Logs → CloudWatch Logs → Log Insights
                          │
                          ▼
                   Metrics Filters → CloudWatch Metrics
                          │
                          ▼
                      Alarms → SNS → Email/Slack
```

### Dashboards

- **CloudWatch Dashboard**: `LoveAndLaw-Production`
  - API performance overview
  - Error rate tracking
  - User activity metrics
  - Infrastructure health

### Alerts

- High error rate (>5%)
- API latency (>2s p95)
- ECS task failures
- Lambda errors
- Database connection issues

## Development & Maintenance

### Local Development Setup

1. **Prerequisites**:
   ```bash
   python 3.8+
   docker
   aws-cli (configured)
   ```

2. **Environment Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with API keys
   ```

3. **Local Services**:
   ```bash
   # Start Elasticsearch
   ./start-elasticsearch.sh
   
   # Run application
   python main.py
   ```

4. **Testing**:
   ```bash
   # Unit tests
   pytest tests/
   
   # Integration tests
   python test_production_api.py
   ```

### Code Organization

```
src/
├── agents/              # AI agent implementations
│   ├── base.py         # Base agent class
│   ├── legal_specialists/  # Specialized agents
│   └── *.py            # Core agents
├── api/                # API layer
│   ├── main.py        # FastAPI app
│   └── models.py      # Pydantic models
├── core/              # Core engine
│   ├── therapeutic_engine.py  # LangGraph orchestration
│   └── websocket_handler.py   # WebSocket management
├── models/            # Data models
├── services/          # External services
│   ├── database.py    # Database connections
│   └── elasticsearch_service.py  # Search service
└── utils/            # Utilities
    └── logger.py     # Logging configuration
```

### Maintenance Tasks

1. **Regular Tasks**:
   - Monitor CloudWatch dashboards
   - Review error logs weekly
   - Update dependencies monthly
   - Rotate API keys quarterly

2. **Scaling Considerations**:
   - ECS auto-scaling configured
   - Lambda concurrent execution limits
   - Database read replicas if needed
   - Cache layer expansion

3. **Troubleshooting Guide**:
   - Check CloudWatch logs first
   - Verify service health endpoints
   - Review recent deployments
   - Check external API status

### Adding New Features

1. **New Agent**:
   - Create in `src/agents/legal_specialists/`
   - Inherit from `BaseSpecialistAgent`
   - Add to routing logic
   - Create prompt file
   - Update tests

2. **New API Endpoint**:
   - Add to `src/api/main.py`
   - Create Pydantic models
   - Add authentication if needed
   - Update API documentation
   - Add tests

3. **Infrastructure Changes**:
   - Update Terraform modules
   - Plan changes: `terraform plan`
   - Apply carefully: `terraform apply`
   - Update deployment scripts

## Conclusion

This architecture provides a scalable, secure, and maintainable foundation for the LoveAndLaw therapeutic AI system. The modular design allows for easy extension while maintaining clear separation of concerns. The comprehensive monitoring and deployment automation ensure reliable operations and quick iteration cycles.