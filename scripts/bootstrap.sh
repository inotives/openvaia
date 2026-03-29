#!/bin/bash
set -e

# Generate .env files from templates if they don't already exist

copy_if_missing() {
    local template="$1"
    local target="${template%.template}"
    if [ ! -f "$target" ]; then
        cp "$template" "$target"
        echo "Created $target from template"
    else
        echo "Skipped $target (already exists)"
    fi
}

echo "Bootstrapping environment files..."

copy_if_missing .env.template
copy_if_missing agents/robin/.env.template
copy_if_missing agents/ino/.env.template

echo "Done. Edit the .env files with your actual credentials."
