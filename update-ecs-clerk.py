#!/usr/bin/env python3
import json
import subprocess
import os

# Load environment variables
CLERK_PUBLISHABLE_KEY = os.getenv('CLERK_PUBLISHABLE_KEY', '')
CLERK_FRONTEND_API = os.getenv('CLERK_FRONTEND_API', '')

# Get the current task definition
result = subprocess.run(['aws', 'ecs', 'describe-task-definition', '--task-definition', 'loveandlaw-production:24', '--region', 'us-east-1'], capture_output=True, text=True)
task_def = json.loads(result.stdout)['taskDefinition']

# Clean up task definition for registration
for key in ['taskDefinitionArn', 'revision', 'status', 'requiresAttributes', 'compatibilities', 'registeredAt', 'registeredBy']:
    task_def.pop(key, None)

# Add Clerk environment variables
container = task_def['containerDefinitions'][0]
clerk_env_vars = [
    {"name": "USE_CLERK_AUTH", "value": "True"},
    {"name": "CLERK_PUBLISHABLE_KEY", "value": CLERK_PUBLISHABLE_KEY},
    {"name": "CLERK_FRONTEND_API", "value": CLERK_FRONTEND_API}
]

# Add new environment variables
for env_var in clerk_env_vars:
    # Check if it already exists
    existing = next((e for e in container['environment'] if e['name'] == env_var['name']), None)
    if existing:
        existing['value'] = env_var['value']
    else:
        container['environment'].append(env_var)

# Add Clerk secret key to secrets
clerk_secret = {"name": "CLERK_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:085603066392:secret:loveandlaw-production-api-keys-LXBGtE:CLERK_SECRET_KEY::"}

# Check if it already exists in secrets
if 'secrets' not in container:
    container['secrets'] = []
    
existing_secret = next((s for s in container['secrets'] if s['name'] == 'CLERK_SECRET_KEY'), None)
if not existing_secret:
    container['secrets'].append(clerk_secret)

# Save the updated task definition
with open('/tmp/updated-task-def.json', 'w') as f:
    json.dump(task_def, f, indent=2)

print("Task definition updated with Clerk configuration")
print(f"USE_CLERK_AUTH: True")
print(f"CLERK_PUBLISHABLE_KEY: {CLERK_PUBLISHABLE_KEY}")
print(f"CLERK_FRONTEND_API: {CLERK_FRONTEND_API}")
print(f"CLERK_SECRET_KEY: Added to secrets")

# Register the new task definition
result = subprocess.run(['aws', 'ecs', 'register-task-definition', '--cli-input-json', 'file:///tmp/updated-task-def.json', '--region', 'us-east-1'], capture_output=True, text=True)
if result.returncode == 0:
    response = json.loads(result.stdout)
    new_revision = response['taskDefinition']['revision']
    print(f"\nNew task definition registered: loveandlaw-production:{new_revision}")
    
    # Update the service to use the new task definition
    print("\nUpdating ECS service...")
    result = subprocess.run([
        'aws', 'ecs', 'update-service',
        '--cluster', 'loveandlaw-production',
        '--service', 'loveandlaw-production-api',
        '--task-definition', f'loveandlaw-production:{new_revision}',
        '--force-new-deployment',
        '--region', 'us-east-1'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("ECS service updated successfully!")
        print("\nWaiting for deployment to stabilize...")
        subprocess.run([
            'aws', 'ecs', 'wait', 'services-stable',
            '--cluster', 'loveandlaw-production',
            '--services', 'loveandlaw-production-api',
            '--region', 'us-east-1'
        ])
        print("Deployment complete!")
    else:
        print(f"Failed to update service: {result.stderr}")
else:
    print(f"Failed to register task definition: {result.stderr}")