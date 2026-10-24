#!/usr/bin/env bash
# Usage: upsert-comment.sh <lane> <body-file>
# Updates the pull request comment carrying `<!-- crap-gate:<lane> -->`, or posts it if there is none.
# Needs GH_TOKEN with pull-requests: write, and runs on pull_request events only.
set -euo pipefail

lane=$1
body_file=$2
marker="<!-- crap-gate:${lane} -->"
pr=$(jq -r '.pull_request.number' "$GITHUB_EVENT_PATH")

id=$(gh api --paginate "repos/${GITHUB_REPOSITORY}/issues/${pr}/comments" \
  --jq ".[] | select(.body | startswith(\"${marker}\")) | .id" | head -n 1)

if [ -n "$id" ]; then
  gh api --method PATCH "repos/${GITHUB_REPOSITORY}/issues/comments/${id}" -F "body=@${body_file}" --silent
else
  gh api --method POST "repos/${GITHUB_REPOSITORY}/issues/${pr}/comments" -F "body=@${body_file}" --silent
fi
