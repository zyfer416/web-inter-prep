#!/bin/bash

# Web-Inter-Prep Deployment Script
# This script automates the deployment process to Render

echo "🚀 Starting deployment to Render..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit"
fi

# Check if remote origin exists
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "❌ No remote origin found!"
    echo "Please add your Render git remote first:"
    echo "git remote add origin https://git.render.com/your-username/web-inter-prep.git"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

echo "📋 Current branch: $CURRENT_BRANCH"

# Add all changes
echo "📝 Adding all changes..."
git add .

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "✅ No changes to commit"
else
    # Commit changes
    echo "💾 Committing changes..."
    git commit -m "Deploy update: $(date '+%Y-%m-%d %H:%M:%S')"
fi

# Push to Render
echo "🚀 Pushing to Render..."
git push origin $CURRENT_BRANCH

echo "✅ Deployment completed!"
echo "🌐 Your app should be available at your Render URL shortly"
echo "⏱️  Render typically takes 2-5 minutes to deploy changes"
