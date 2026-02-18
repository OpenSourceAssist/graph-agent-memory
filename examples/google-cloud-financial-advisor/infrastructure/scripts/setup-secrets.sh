#!/bin/bash
# Setup Google Cloud Secret Manager secrets for Financial Advisor
# Usage: ./setup-secrets.sh [PROJECT_ID]

set -e

PROJECT_ID="${1:-$(gcloud config get-value project)}"

echo "Setting up secrets for Financial Advisor"
echo "Project: $PROJECT_ID"
echo ""

# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"

# Function to create or update a secret
create_secret() {
    local name=$1
    local prompt=$2

    echo ""
    echo "Secret: $name"

    if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
        echo "  Secret already exists. Do you want to update it? (y/N)"
        read -r update
        if [[ "$update" != "y" && "$update" != "Y" ]]; then
            echo "  Skipping..."
            return
        fi
    fi

    echo "$prompt"
    read -rs value
    echo ""

    if [[ -z "$value" ]]; then
        echo "  Empty value, skipping..."
        return
    fi

    # Create or update the secret
    if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
        echo -n "$value" | gcloud secrets versions add "$name" --data-file=- --project="$PROJECT_ID"
        echo "  Updated secret: $name"
    else
        echo -n "$value" | gcloud secrets create "$name" --data-file=- --project="$PROJECT_ID"
        echo "  Created secret: $name"
    fi
}

echo "This script will create the following secrets:"
echo "  - neo4j-uri: Neo4j connection URI (e.g., neo4j+s://xxx.databases.neo4j.io)"
echo "  - neo4j-password: Neo4j password"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Create secrets
create_secret "neo4j-uri" "  Enter Neo4j URI (e.g., neo4j+s://xxx.databases.neo4j.io):"
create_secret "neo4j-password" "  Enter Neo4j password:"

echo ""
echo "Secret setup complete!"
echo ""
echo "To grant Cloud Run access to these secrets, run:"
echo ""
echo "  # Get the default compute service account"
echo "  SA=\"\$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com\""
echo ""
echo "  # Grant access to secrets"
echo "  gcloud secrets add-iam-policy-binding neo4j-uri \\"
echo "      --member=\"serviceAccount:\$SA\" \\"
echo "      --role=\"roles/secretmanager.secretAccessor\" \\"
echo "      --project=\"$PROJECT_ID\""
echo ""
echo "  gcloud secrets add-iam-policy-binding neo4j-password \\"
echo "      --member=\"serviceAccount:\$SA\" \\"
echo "      --role=\"roles/secretmanager.secretAccessor\" \\"
echo "      --project=\"$PROJECT_ID\""
