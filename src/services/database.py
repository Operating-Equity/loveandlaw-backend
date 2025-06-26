from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
import os
import json
import aioboto3
from elasticsearch import AsyncElasticsearch
import redis.asyncio as redis
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def serialize_for_dynamodb(obj):
    """Convert datetime objects to ISO format strings and floats to Decimals"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: serialize_for_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_dynamodb(item) for item in obj]
    return obj


class DynamoDBService:
    def __init__(self):
        self.session = None
        self.dynamodb = None
        self.conversation_table = None
        self.user_profile_table = None
        
    async def initialize(self):
        """Initialize DynamoDB connection"""
        try:
            self.session = aioboto3.Session()
            
            if settings.dynamodb_endpoint:
                # Local development
                self.dynamodb = await self.session.resource(
                    'dynamodb',
                    endpoint_url=settings.dynamodb_endpoint,
                    region_name=settings.aws_region
                ).__aenter__()
            else:
                # Production AWS
                self.dynamodb = await self.session.resource(
                    'dynamodb',
                    region_name=settings.aws_region
                ).__aenter__()
            
            # Create tables if they don't exist (for local dev)
            await self._create_tables_if_not_exist()
            
            self.conversation_table = await self.dynamodb.Table(settings.dynamodb_conversations_table)
            self.user_profile_table = await self.dynamodb.Table(settings.dynamodb_profiles_table)
            
            logger.info("DynamoDB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB: {e}")
            raise
    
    async def _create_tables_if_not_exist(self):
        """Create DynamoDB tables for local development"""
        if not settings.dynamodb_endpoint:
            # In AWS, tables should be created via Terraform
            return
            
        existing_tables = await self.dynamodb.meta.client.list_tables()
        existing_table_names = existing_tables.get('TableNames', [])
        
        # ConversationState table
        if settings.dynamodb_conversations_table not in existing_table_names:
            await self.dynamodb.create_table(
                TableName=settings.dynamodb_conversations_table,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'turn_id', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'turn_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            logger.info("Created ConversationState table")
        
        # UserProfiles table
        if settings.dynamodb_profiles_table not in existing_table_names:
            await self.dynamodb.create_table(
                TableName=settings.dynamodb_profiles_table,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            logger.info("Created UserProfiles table")
    
    async def save_turn_state(self, turn_state: Dict[str, Any]):
        """Save conversation turn state"""
        if not self.conversation_table:
            logger.warning("DynamoDB not initialized, skipping turn state save")
            return
            
        try:
            # Serialize datetime objects and floats
            turn_state = serialize_for_dynamodb(turn_state)
            
            # Set TTL
            ttl = int((datetime.utcnow() + timedelta(days=settings.conversation_ttl_days)).timestamp())
            turn_state['ttl'] = ttl
            
            await self.conversation_table.put_item(Item=turn_state)
            logger.info(f"Saved turn state: {turn_state['turn_id']}")
        except Exception as e:
            logger.error(f"Failed to save turn state: {e}")
            raise
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        if not self.user_profile_table:
            logger.warning("DynamoDB not initialized, returning empty profile")
            return None
            
        try:
            response = await self.user_profile_table.get_item(
                Key={'user_id': user_id}
            )
            return response.get('Item')
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]):
        """Update user profile"""
        if not self.user_profile_table:
            logger.warning("DynamoDB not initialized, skipping profile update")
            return
            
        try:
            # Serialize datetime objects and floats
            updates = serialize_for_dynamodb(updates)
            
            # Set TTL
            ttl = int((datetime.utcnow() + timedelta(days=settings.user_profile_ttl_days)).timestamp())
            updates['ttl'] = ttl
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            # Build update expression with attribute names for reserved keywords
            update_expr = "SET "
            expr_values = {}
            expr_names = {}
            
            for key, value in updates.items():
                # Skip primary key fields
                if key == 'user_id':
                    continue
                    
                # Use placeholder for attribute names to handle reserved keywords
                attr_name = f"#{key}"
                expr_names[attr_name] = key
                update_expr += f"{attr_name} = :{key}, "
                expr_values[f":{key}"] = value
            
            update_expr = update_expr.rstrip(", ")
            
            await self.user_profile_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )
            logger.info(f"Updated user profile: {user_id}")
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            raise
    
    async def get_recent_turns(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation turns for a user"""
        try:
            response = await self.conversation_table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id},
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get recent turns: {e}")
            return []
    
    async def get_user_conversations(self, user_id: str, limit: int = 20, offset: int = 0, status: str = None) -> Dict[str, Any]:
        """Get all conversations for a user with pagination"""
        if not self.conversation_table:
            logger.warning("DynamoDB not initialized, returning empty conversations")
            return {
                "conversations": [],
                "total": 0
            }
            
        try:
            # Query all turns for the user
            response = await self.conversation_table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id},
                ScanIndexForward=False  # Most recent first
            )
            
            items = response.get('Items', [])
            
            # Group by conversation_id
            conversations_map = {}
            for item in items:
                conv_id = item.get('conversation_id')
                if not conv_id:
                    continue
                    
                if conv_id not in conversations_map:
                    conversations_map[conv_id] = {
                        'conversation_id': conv_id,
                        'user_id': user_id,
                        'created_at': item.get('created_at'),
                        'updated_at': item.get('created_at'),
                        'messages': [],
                        'distress_scores': []
                    }
                
                conversations_map[conv_id]['messages'].append(item)
                conversations_map[conv_id]['updated_at'] = max(
                    conversations_map[conv_id]['updated_at'],
                    item.get('created_at', '')
                )
                
                if item.get('distress_score') is not None:
                    conversations_map[conv_id]['distress_scores'].append(float(item['distress_score']))
            
            # Build conversation summaries
            conversations = []
            for conv_id, conv_data in conversations_map.items():
                messages = conv_data['messages']
                
                # Get last user message
                user_messages = [m for m in messages if m.get('user_text')]
                last_message = user_messages[0].get('user_text', '') if user_messages else ''
                
                # Calculate average distress score
                avg_distress = sum(conv_data['distress_scores']) / len(conv_data['distress_scores']) if conv_data['distress_scores'] else 5.0
                
                # Extract legal topics
                legal_topics = set()
                for msg in messages:
                    if msg.get('legal_intent'):
                        legal_topics.update(msg['legal_intent'])
                
                conversation_summary = {
                    'conversation_id': conv_id,
                    'user_id': user_id,
                    'created_at': conv_data['created_at'],
                    'updated_at': conv_data['updated_at'],
                    'status': 'active',  # Default for now
                    'last_message': last_message[:100] if last_message else None,
                    'summary': None,  # To be implemented
                    'message_count': len(messages),
                    'average_distress_score': avg_distress,
                    'legal_topics': list(legal_topics)
                }
                
                conversations.append(conversation_summary)
            
            # Sort by updated_at descending
            conversations.sort(key=lambda x: x['updated_at'], reverse=True)
            
            # Apply pagination
            total = len(conversations)
            conversations = conversations[offset:offset + limit]
            
            return {
                'conversations': conversations,
                'total': total
            }
            
        except Exception as e:
            logger.error(f"Failed to get user conversations: {e}")
            return {"conversations": [], "total": 0}
    
    async def get_conversation_messages(self, user_id: str, conversation_id: str, 
                                      limit: int = 50, offset: int = 0, 
                                      order: str = "asc") -> Dict[str, Any]:
        """Get all messages for a specific conversation"""
        if not self.conversation_table:
            logger.warning("DynamoDB not initialized, returning empty messages")
            return {
                "messages": [],
                "total": 0
            }
            
        try:
            # Query all turns for the user
            response = await self.conversation_table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id},
                ScanIndexForward=(order == "asc")
            )
            
            # Filter for specific conversation
            all_items = response.get('Items', [])
            conversation_items = [
                item for item in all_items 
                if item.get('conversation_id') == conversation_id
            ]
            
            # Convert to message format
            messages = []
            for item in conversation_items:
                # User message
                if item.get('user_text'):
                    messages.append({
                        'message_id': f"{item['turn_id']}-user",
                        'turn_id': item['turn_id'],
                        'timestamp': item.get('created_at', ''),
                        'role': 'user',
                        'content': item['user_text'],
                        'redacted': item.get('pii_found', False)
                    })
                
                # Assistant message
                if item.get('assistant_response'):
                    messages.append({
                        'message_id': f"{item['turn_id']}-assistant",
                        'turn_id': item['turn_id'],
                        'timestamp': item.get('created_at', ''),
                        'role': 'assistant',
                        'content': item['assistant_response'],
                        'redacted': False
                    })
            
            # Apply pagination
            total = len(messages)
            messages = messages[offset:offset + limit]
            
            return {
                'messages': messages,
                'total': total
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {e}")
            return {"messages": [], "total": 0}
    
    async def close(self):
        """Close DynamoDB connection"""
        if self.session:
            await self.session.__aexit__(None, None, None)


# Import ElasticsearchService from the dedicated module
# (Removed duplicate class definition)
class RedisService:
    def __init__(self):
        self.client = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Failed to get from Redis: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        """Set value in cache"""
        try:
            if ttl:
                await self.client.setex(key, ttl, value)
            else:
                await self.client.set(key, value)
        except Exception as e:
            logger.error(f"Failed to set in Redis: {e}")
    
    async def delete(self, key: str):
        """Delete value from cache"""
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete from Redis: {e}")
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()


# Import ElasticsearchService from the dedicated module
from src.services.elasticsearch_service import ElasticsearchService

# Global instances
dynamodb_service = DynamoDBService()
elasticsearch_service = ElasticsearchService()
redis_service = RedisService()


async def initialize_databases():
    """Initialize all database connections"""
    global dynamodb_service, elasticsearch_service, redis_service
    
    # Check for skip flags
    skip_aws = os.environ.get("SKIP_AWS_INIT", "false").lower() == "true"
    skip_redis = os.environ.get("SKIP_REDIS_INIT", "false").lower() == "true"
    
    # Initialize DynamoDB only if not skipped
    if not skip_aws:
        try:
            await dynamodb_service.initialize()
            logger.info("DynamoDB initialized successfully")
        except Exception as e:
            logger.warning(f"DynamoDB initialization failed: {e}. Running without DynamoDB.")
    else:
        logger.info("Skipping DynamoDB initialization (SKIP_AWS_INIT=true)")
    
    # Initialize Elasticsearch
    try:
        await elasticsearch_service.initialize()
        logger.info("Elasticsearch initialized successfully")
    except Exception as e:
        logger.warning(f"Elasticsearch initialization failed: {e}. Running without Elasticsearch.")
    
    # Initialize Redis only if not skipped
    if not skip_redis:
        try:
            await redis_service.initialize()
            logger.info("Redis initialized successfully")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}. Running without Redis.")
    else:
        logger.info("Skipping Redis initialization (SKIP_REDIS_INIT=true)")


async def close_databases():
    """Close all database connections"""
    if dynamodb_service:
        try:
            await dynamodb_service.close()
        except Exception as e:
            logger.warning(f"Error closing DynamoDB: {e}")
    
    if elasticsearch_service:
        try:
            await elasticsearch_service.close()
        except Exception as e:
            logger.warning(f"Error closing Elasticsearch: {e}")
    
    if redis_service:
        try:
            await redis_service.close()
        except Exception as e:
            logger.warning(f"Error closing Redis: {e}")