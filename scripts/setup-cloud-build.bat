@echo off
REM ==============================================================
REM Quick Setup Script for Cloud Build Deployment (Windows)
REM ==============================================================
REM Run this script to quickly set up Cloud Build deployment
REM Usage: setup-cloud-build.bat

setlocal enabledelayedexpansion

echo.
echo 🚀 MSME Financial Health Card — Cloud Build Setup
echo ==================================================
echo.
echo ⚠️  IMPORTANT: You must grant yourself the Editor role FIRST!
echo.
echo Run this command in another terminal BEFORE continuing:
echo.
echo   gcloud projects add-iam-policy-binding %%gcloud config get-value project%% ^
echo     --member=user:fintrust.prss@gmail.com ^
echo     --role=roles/editor
echo.
pause

REM Get project ID
for /f "tokens=*" %%i in ('gcloud config get-value project') do set PROJECT_ID=%%i

if "!PROJECT_ID!"=="" (
    echo ❌ Error: No GCP project set. Run: gcloud config set project PROJECT_ID
    exit /b 1
)

echo 📍 Project: !PROJECT_ID!
echo.

REM Step 1: Enable APIs
echo Step 1️⃣  — Enabling required GCP APIs...
call gcloud services enable ^
  cloudbuild.googleapis.com ^
  run.googleapis.com ^
  artifactregistry.googleapis.com ^
  sqladmin.googleapis.com ^
  secretmanager.googleapis.com ^
  cloudresourcemanager.googleapis.com ^
  --quiet

if %errorlevel% neq 0 (
    echo ❌ Failed to enable APIs
    exit /b 1
)
echo ✅ APIs enabled
echo.

REM Step 2: Create Artifact Registry
echo Step 2️⃣  — Creating Artifact Registry repository...

gcloud artifacts repositories list --location=us-central1 --format="value(name)" | findstr /C:"msme-healthcard" >nul
if %errorlevel% neq 0 (
    call gcloud artifacts repositories create msme-healthcard ^
      --repository-format=docker ^
      --location=us-central1 ^
      --description="MSME Financial Health Card — Docker images" ^
      --quiet
    echo ✅ Artifact Registry repository created
) else (
    echo ✅ Artifact Registry repository already exists
)
echo.


REM Step 4: Grant Cloud Build service account access to secrets
echo Step 4️⃣  — Granting Cloud Build service account access to secrets...
set BUILD_SA=!PROJECT_ID!@cloudbuild.gserviceaccount.com

call gcloud secrets add-iam-policy-binding postgres-password ^
  --member=serviceAccount:!BUILD_SA! ^
  --role=roles/secretmanager.secretAccessor ^
  --quiet

call gcloud secrets add-iam-policy-binding postgres-user ^
  --member=serviceAccount:!BUILD_SA! ^
  --role=roles/secretmanager.secretAccessor ^
  --quiet

echo ✅ Service account permissions updated
echo.

REM Summary
echo ============================================
echo ✅ Setup Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Connect your GitHub repository:
echo.
echo    gcloud builds connect --repository-name=msme-financial-health-card ^
echo      --github-owner=YOUR_GITHUB_USERNAME ^
echo      --region=us-central1
echo.
echo 2. Create Cloud SQL instance:
echo.
echo    gcloud sql instances create msme-postgres ^
echo      --database-version=POSTGRES_15 ^
echo      --tier=db-custom-2-8192 ^
echo      --region=us-central1 ^
echo      --network=default
echo.
echo    gcloud sql databases create msme_healthcard --instance=msme-postgres
echo.
echo 3. Update cloudbuild.yml with your Cloud SQL connection name
echo    and backend URL
echo.
echo 4. Push to main branch:
echo.
echo    git add cloudbuild.yml
echo    git commit -m "Update deployment config"
echo    git push origin main
echo.
echo 5. Monitor build at: https://console.cloud.google.com/cloud-build/builds
echo.

endlocal
