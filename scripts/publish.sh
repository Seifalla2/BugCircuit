#!/usr/bin/env bash
set -euo pipefail

# Preconditions: create an empty PUBLIC repo at the destination first.
if [ -d .git ]; then
  echo 'Git metadata already exists. Inspect status and remote before publishing.' >&2
  exit 1
fi

git init
git branch -M main
git add .
git commit -m 'feat: initial evidence-first BugCircuit v0.1 alpha'
git remote add origin https://github.com/Seifalla2/BugCircuit.git
printf '%s\n' 'Review the commit and push by running: git push -u origin main'
