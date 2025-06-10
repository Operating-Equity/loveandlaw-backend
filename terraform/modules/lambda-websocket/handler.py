import json
import boto3
import os
import urllib3
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
apigateway = boto3.client('apigatewaymanagementapi', 
                         endpoint_url=os.environ.get('WEBSOCKET_API_ENDPOINT'))

# Initialize HTTP client for ECS communication
http = urllib3.PoolManager()

# Get environment variables
CONNECTION_TABLE = os.environ.get('CONNECTION_TABLE', 'loveandlaw-websocket-connections')
ECS_SERVICE_URL = os.environ.get('ECS_SERVICE_URL', 'http://internal-loveandlaw-production-alb-2146976236.us-east-1.elb.amazonaws.com')

# Get DynamoDB table
connection_table = dynamodb.Table(CONNECTION_TABLE)

def handler(event, context):
    """Main Lambda handler for WebSocket events"""
    
    route_key = event.get('requestContext', {}).get('routeKey')
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    print(f"Route: {route_key}, Connection: {connection_id}")
    
    try:
        if route_key == '$connect':
            return handle_connect(connection_id, event)
        elif route_key == '$disconnect':
            return handle_disconnect(connection_id)
        elif route_key == '$default':
            return handle_message(connection_id, event)
        else:
            return {'statusCode': 400, 'body': 'Invalid route'}
            
    except Exception as e:
        print(f"Error: {str(e)}")
        # Try to send error to client
        try:
            send_to_client(connection_id, {
                'type': 'error',
                'message': 'Internal server error'
            })
        except:
            pass
        return {'statusCode': 500, 'body': 'Internal server error'}

def handle_connect(connection_id, event):
    """Handle new WebSocket connection"""
    
    # Store connection info
    connection_table.put_item(
        Item={
            'connectionId': connection_id,
            'connectedAt': datetime.utcnow().isoformat(),
            'authenticated': False
        }
    )
    
    print(f"Connection {connection_id} established")
    return {'statusCode': 200, 'body': 'Connected'}

def handle_disconnect(connection_id):
    """Handle WebSocket disconnection"""
    
    # Remove connection info
    connection_table.delete_item(
        Key={'connectionId': connection_id}
    )
    
    # Notify ECS service
    try:
        url = f"{ECS_SERVICE_URL}/internal/websocket/disconnect"
        response = http.request(
            'POST',
            url,
            body=json.dumps({'connectionId': connection_id}),
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        print(f"Notified ECS of disconnect: {response.status}")
    except Exception as e:
        print(f"Failed to notify ECS of disconnect: {e}")
    
    print(f"Connection {connection_id} disconnected")
    return {'statusCode': 200, 'body': 'Disconnected'}

def handle_message(connection_id, event):
    """Handle incoming WebSocket message"""
    
    try:
        # Parse message
        body = json.loads(event.get('body', '{}'))
        print(f"Received message: {body}")
        
        # Forward to ECS service
        internal_message = {
            'connectionId': connection_id,
            'type': body.get('type'),
            'cid': body.get('cid'),
            'text': body.get('text'),
            'user_id': body.get('user_id'),
            'conversation_id': body.get('conversation_id'),
            'requestContext': event.get('requestContext')
        }
        
        url = f"{ECS_SERVICE_URL}/internal/websocket/message"
        print(f"Forwarding message to ECS at: {url}")
        
        response = http.request(
            'POST',
            url,
            body=json.dumps(internal_message),
            headers={
                'Content-Type': 'application/json',
                'X-Connection-Id': connection_id
            },
            timeout=25
        )
        
        print(f"ECS response status: {response.status}")
        
        if response.status == 200:
            # Parse response
            response_data = json.loads(response.data.decode('utf-8'))
            
            # Send messages to client
            if 'messages' in response_data and response_data['messages']:
                for msg in response_data['messages']:
                    send_to_client(connection_id, msg)
            elif 'message' in response_data:
                send_to_client(connection_id, response_data['message'])
                
            return {'statusCode': 200, 'body': 'Message processed'}
        else:
            print(f"ECS error response: {response.data}")
            send_to_client(connection_id, {
                'type': 'error',
                'message': 'Error processing message'
            })
            return {'statusCode': 500, 'body': 'Error processing message'}
            
    except Exception as e:
        print(f"Error handling message: {str(e)}")
        import traceback
        traceback.print_exc()
        
        try:
            send_to_client(connection_id, {
                'type': 'error',
                'message': 'Error processing message'
            })
        except:
            pass
            
        return {'statusCode': 500, 'body': 'Error processing message'}

def send_to_client(connection_id, message):
    """Send message to WebSocket client"""
    
    try:
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        print(f"Sent to client: {message.get('type', 'unknown')}")
    except apigateway.exceptions.GoneException:
        print(f"Connection {connection_id} is gone")
        # Clean up connection
        connection_table.delete_item(
            Key={'connectionId': connection_id}
        )
        raise
    except Exception as e:
        print(f"Error sending to client: {e}")
        raise