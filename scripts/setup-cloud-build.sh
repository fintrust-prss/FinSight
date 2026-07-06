#!/bin/bash
# ==============================================================
# Quick Setup Script for Cloud Build Deployment
# ==============================================================
# Run this script to quickly set up Cloud Build deployment
# Usage: bash setup-cloud-build.sh

set -e

echo "🚀 MSME Financial Health Card — Cloud Build Setup"
echo "=================================================="
echo ""
echo "⚠️  IMPORTANT: You must grant yourself the Editor role FIRST!"
echo ""
echo "Run this command in another terminal BEFORE continuing:"
echo ""
echo "  gcloud projects add-iam-policy-binding \$(gcloud config get-value project) \\"
echo "    --member=user:fintrust.prss@gmail.com \\"
echo "    --role=roles/editor"
echo ""
read -p "Press Enter once you've run the command above and waited 30 seconds for it to take effect..."
echo ""

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project set. Run: gcloud config set project PROJECT_ID"
    exit 1
fi

echo "📍 Project: $PROJECT_ID"
echo ""

# Step 1: Enable APIs
echo "Step 1️⃣  — Enabling required GCP APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  sql.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --quiet
echo "✅ APIs enabled"
echo ""

# Step 2: Create Artifact Registry
echo "Step 2️⃣  — Creating Artifact Registry repository..."
REPO_EXISTS=$(gcloud artifacts repositories list --location=us-central1 --format='value(name)' | grep -c msme-healthcard || true)
if [ $REPO_EXISTS -eq 0 ]; then
    gcloud artifacts repositories create msme-healthcard \
      --repository-format=docker \
      --location=us-central1 \
      --description="MSME Financial Health Card — Docker images" \
      --quiet
    echo "✅ Artifact Registry repository created"
else
    echo "✅ Artifact Registry repository already exists"
fi
echo ""

# Step 3: Create/Update Secrets
echo "Step 3️⃣  — Setting up secrets..."
read -sp "Enter PostgreSQL password: " DB_PASSWORD
echo ""

# Check if secret exists
if gcloud secrets describe postgres-password &>/dev/null; then
    echo -n "$DB_PASSWORD" | gcloud secrets versions add postgres-password --data-file=-
    echo "✅ Updated postgres-password secret"
else
    echo -n "$DB_PASSWORD" | gcloud secrets create postgres-password --data-file=-
    echo "✅ Created postgres-password secret"
fi

# PostgreSQL user
if gcloud secrets describe postgres-user &>/dev/null; then
    echo "✅ postgres-user secret already exists"
else
    echo -n "msme_app" | gcloud secrets create postgres-user --data-file=-
    echo "✅ Created postgres-user secret"
fi
echo ""

# Step 4: Grant Cloud Build service account access to secrets
echo "Step 4️⃣  — Granting Cloud Build service account access to secrets..."
BUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

gcloud secrets add-iam-policy-binding postgres-password \
  --member=serviceAccount:${BUILD_SA} \
  --role=roles/secretmanager.secretAccessor \
  --quiet

gcloud secrets add-iam-policy-binding postgres-user \
  --member=serviceAccount:${BUILD_SA} \
  --role=roles/secretmanager.secretAccessor \
  --quiet

echo "✅ Service account permissions updated"
echo ""

# Step 5: Connect GitHub
echo "Step 5️⃣  — GitHub Repository Connection"
echo "To connect your GitHub repo, run:"
echo ""
echo "  gcloud builds connect --repository-name=msme-financial-health-card \\"
echo "    --github-owner=YOUR_GITHUB_USERNAME \\"
echo "    --region=us-central1"
echo ""
echo "This will prompt you to authorize GitHub."
echo ""

# Step 6: Create Cloud SQL instance (optional)
echo "Step 6️⃣  — Cloud SQL Instance (Optional)"
echo "To create PostgreSQL instance, run:"
echo ""
echo "  gcloud sql instances create msme-postgres \\"
echo "    --database-version=POSTGRES_15 \\"
echo "    --tier=db-custom-2-8192 \\"
echo "    --region=us-central1 \\"
echo "    --network=default"
echo ""
echo "  gcloud sql databases create msme_healthcard --instance=msme-postgres"
echo ""

# Step 7: Update cloudbuild.yml
echo "Step 7️⃣  — Update cloudbuild.yml"
read -p "Enter Cloud SQL connection name (format: project:region:instance): " DB_HOST
read -p "Enter backend Cloud Run service URL (leave empty for auto-generated): " BACKEND_URL

echo "Updating cloudbuild.yml..."
sed -i.bak "s|_DB_HOST: .*|_DB_HOST: '$DB_HOST'|g" cloudbuild.yml
if [ ! -z "$BACKEND_URL" ]; then
    sed -i.bak "s|_BACKEND_URL: .*|_BACKEND_URL: '$BACKEND_URL'|g" cloudbuild.yml
fi
rm cloudbuild.yml.bak 2>/dev/null || true
echo "✅ cloudbuild.yml updated"
echo ""

# Summary
echo "============================================"
echo "✅ Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Connect your GitHub repository (see Step 5️⃣  above)"
echo "2. Create Cloud SQL instance (see Step 6️⃣  above)"
echo "3. Push to main branch:"
echo "   git add cloudbuild.yml"
echo "   git commit -m 'Update deployment config'"
echo "   git push origin main"
echo ""
echo "4. Monitor build at: https://console.cloud.google.com/cloud-build/builds"
echo ""