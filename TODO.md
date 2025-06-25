# LoveAndLaw Backend - TODO

## Current Status ✅
- **Production deployment complete**
- REST API: `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production`
- WebSocket: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`
- All therapeutic and legal specialist agents implemented
- Elasticsearch with semantic search configured
- CloudWatch monitoring and SNS alerts active
- Deployment automation with GitHub Actions

## Pending Tasks

### Infrastructure  
- [x] Fix WebSocket 502 error - **COMPLETED** ✅:
  - Lambda WebSocket handler deployed and working (no more 502 errors)
  - ECS service updated to ARM64 architecture with SpaCy pre-installed
  - Internal routes now return 200 OK
  - WebSocket infrastructure fully operational
  - **AI responses are now working!** All runtime errors fixed:
    - Fixed missing json import in therapeutic engine
    - Fixed DynamoDB table name configuration
    - Fixed datetime serialization issues
    - Fixed float/Decimal conversion for DynamoDB
    - Fixed reserved keyword issues in DynamoDB
    - Fixed ProgressTracker async method signature
  - Current deployment: revision 24 with all fixes
  - Test with: `python test_websocket_simple.py`
  - Note: Legal intake has recursion issue with certain messages (low priority)
- [ ] Complete SSL certificate validation (add DNS CNAME record)
- [ ] Configure custom domain (api.loveandlaw.xyz) after SSL validation
- [ ] Implement rate limiting on API Gateway
- [ ] Set up staging environment

### Security
- [ ] Enable authentication in production
- [ ] Implement API key management for clients
- [ ] Add request signing for internal services
- [ ] Complete security audit

### Integration
- [ ] Connect Lambda WebSocket to actual ALB endpoints (currently using mock)
- [x] ~~Integrate real Elasticsearch lawyer data~~ ✅ Completed with semantic search
- [x] ~~Implement DynamoDB user profile persistence~~ ✅ AWS DynamoDB configured with graceful fallback
  - Tables: `loveandlaw-conversations`, `loveandlaw-userprofiles`
  - Create tables: `python scripts/create_dynamodb_tables.py`
  - Terraform configuration added in `terraform/modules/database/dynamodb.tf`
- [x] ~~Configure Redis with authentication~~ ✅ Redis URL updated with proper authentication
- [x] ~~Fix WebSocket recursion error~~ ✅ Fixed therapeutic engine routing to prevent infinite loops

### Features
- [ ] Implement file upload for documents
- [ ] Create admin dashboard
- [ ] Add analytics tracking
- [x] ~~Add PUT endpoint for user profile updates~~ ✅ Completed - PUT /api/v1/profile/{user_id}
- [x] ~~Add save/remove lawyer endpoints~~ ✅ Completed:
  - POST /api/v1/profile/{user_id}/lawyers/{lawyer_id} - Save lawyer to profile
  - DELETE /api/v1/profile/{user_id}/lawyers/{lawyer_id} - Remove lawyer from profile
- [x] ~~Fix lawyer recommendations not being returned~~ ✅ Fixed - lawyer_cards now properly passed through to websocket


### Documentation
- [ ] Create client SDK examples
- [x] ~~Add architecture diagrams~~ ✅ See ARCHITECTURE.md
- [x] ~~Write deployment runbook~~ ✅ See DEPLOYMENT_GUIDE.md
- [x] ~~Create troubleshooting guide~~ ✅ See ARCHITECTURE.md