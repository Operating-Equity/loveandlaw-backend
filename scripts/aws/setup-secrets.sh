#!/bin/bash
# Setup AWS Secrets Manager for LoveAndLaw

set -e

# Check if required environment variables are set
if [ -z "$GROQ_API_KEY" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: Please set GROQ_API_KEY and ANTHROPIC_API_KEY environment variables"
    exit 1
fi

# Generate a strong JWT secret
JWT_SECRET=$(openssl rand -base64 32)

# Create the secret in AWS Secrets Manager
aws secretsmanager create-secret \
    --name loveandlaw/api-keys \
    --description "API keys for LoveAndLaw backend" \
    --secret-string "{
        \"GROQ_API_KEY\": \"$GROQ_API_KEY\",
        \"ANTHROPIC_API_KEY\": \"$ANTHROPIC_API_KEY\",
        \"JWT_SECRET_KEY\": \"$JWT_SECRET\"
    }" \
    --region us-east-1

echo "✅ Secrets created successfully!"
echo ""
echo "Generated JWT Secret (save this): $JWT_SECRET"
echo ""
echo "To update secrets later, use:"
echo "aws secretsmanager update-secret --secret-id loveandlaw/api-keys --secret-string '{...}'"