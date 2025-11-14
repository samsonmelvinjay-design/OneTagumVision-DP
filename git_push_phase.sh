#!/bin/bash
# Git Push Script for Phase Completion
# Usage: ./git_push_phase.sh "Phase 1: Database Schema"

PHASE_NAME="$1"
COMMIT_MESSAGE="Complete $PHASE_NAME - Add suitability analysis models and admin"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository"
    exit 1
fi

# Check if there are changes to commit
if git diff --quiet && git diff --cached --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Add all changes
echo "Adding all changes..."
git add .

# Commit with phase message
echo "Committing changes: $COMMIT_MESSAGE"
git commit -m "$COMMIT_MESSAGE"

# Push to current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "Pushing to branch: $CURRENT_BRANCH"
git push origin "$CURRENT_BRANCH"

echo "✅ Successfully pushed $PHASE_NAME to GitHub!"

