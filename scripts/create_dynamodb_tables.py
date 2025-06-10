#!/usr/bin/env python3
"""
Create DynamoDB tables in AWS
"""

import boto3
import sys
from datetime import datetime

def create_tables(region='us-east-1'):
    """Create DynamoDB tables"""
    
    dynamodb = boto3.resource('dynamodb', region_name=region)
    client = boto3.client('dynamodb', region_name=region)
    
    tables_to_create = [
        {
            'name': 'loveandlaw-conversations',
            'hash_key': 'user_id',
            'range_key': 'turn_id',
            'description': 'Conversation turn states'
        },
        {
            'name': 'loveandlaw-userprofiles',
            'hash_key': 'user_id',
            'range_key': None,
            'description': 'User profiles and preferences'
        }
    ]
    
    # Check existing tables
    existing_tables = client.list_tables()['TableNames']
    
    for table_config in tables_to_create:
        table_name = table_config['name']
        
        if table_name in existing_tables:
            print(f"✓ Table {table_name} already exists")
            continue
            
        print(f"Creating table {table_name}...")
        
        # Define key schema
        key_schema = [
            {
                'AttributeName': table_config['hash_key'],
                'KeyType': 'HASH'
            }
        ]
        
        # Define attribute definitions
        attribute_definitions = [
            {
                'AttributeName': table_config['hash_key'],
                'AttributeType': 'S'
            }
        ]
        
        # Add range key if specified
        if table_config['range_key']:
            key_schema.append({
                'AttributeName': table_config['range_key'],
                'KeyType': 'RANGE'
            })
            attribute_definitions.append({
                'AttributeName': table_config['range_key'],
                'AttributeType': 'S'
            })
        
        try:
            # Create the table
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                BillingMode='PAY_PER_REQUEST',
                StreamSpecification={
                    'StreamEnabled': False
                },
                Tags=[
                    {'Key': 'Project', 'Value': 'loveandlaw'},
                    {'Key': 'Environment', 'Value': 'production'},
                    {'Key': 'Description', 'Value': table_config['description']},
                    {'Key': 'CreatedAt', 'Value': datetime.utcnow().isoformat()}
                ]
            )
            
            # Wait for table to be created
            print(f"Waiting for {table_name} to be created...")
            table.wait_until_exists()
            
            # Enable TTL
            client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': 'ttl'
                }
            )
            
            print(f"✓ Table {table_name} created successfully with TTL enabled")
            
        except Exception as e:
            print(f"✗ Error creating table {table_name}: {e}")
            sys.exit(1)
    
    print("\n✅ All DynamoDB tables created successfully!")
    print("\nTable ARNs:")
    for table_config in tables_to_create:
        table_name = table_config['name']
        response = client.describe_table(TableName=table_name)
        print(f"- {table_name}: {response['Table']['TableArn']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create DynamoDB tables for Love & Law')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    create_tables(args.region)