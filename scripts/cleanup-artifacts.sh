#!/bin/bash

echo "🧹 Cleaning up GitHub Actions artifacts..."

# Get all artifacts
artifacts=$(gh api "/repos/JCLEE94/blacklist/actions/artifacts?per_page=100" | jq -r '.artifacts[] | "\(.id)|\(.name)|\(.created_at)"')

# Count total artifacts
total_count=$(echo "$artifacts" | wc -l)
echo "📊 Total artifacts: $total_count"

# Keep only the latest 10 artifacts
keep_count=10
delete_count=$((total_count - keep_count))

if [ $delete_count -gt 0 ]; then
    echo "🗑️  Deleting $delete_count old artifacts..."
    
    # Sort by date and get artifacts to delete
    artifacts_to_delete=$(echo "$artifacts" | sort -t'|' -k3 -r | tail -n +$((keep_count + 1)))
    
    # Delete each artifact
    while IFS='|' read -r id name created_at; do
        echo "  - Deleting: $name (created: $created_at)"
        gh api -X DELETE "/repos/JCLEE94/blacklist/actions/artifacts/$id"
    done <<< "$artifacts_to_delete"
    
    echo "✅ Cleanup complete!"
else
    echo "ℹ️  No artifacts to delete (keeping latest $keep_count)"
fi

# Show remaining artifacts
echo ""
echo "📋 Remaining artifacts:"
gh api "/repos/JCLEE94/blacklist/actions/artifacts?per_page=10" | jq -r '.artifacts[] | "  - \(.name) (\(.size_in_bytes / 1048576 | floor)MB)"'