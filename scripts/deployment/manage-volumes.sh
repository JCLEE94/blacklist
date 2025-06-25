#\!/bin/bash
# Docker Volume Management Script

set -euo pipefail

ENVIRONMENT=${1:-production}
ACTION=${2:-status}
ENV_FILE=".env.${ENVIRONMENT}"

if [ \! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' "$ENV_FILE"  < /dev/null |  grep -v '^$' | xargs)

case $ACTION in
    "create")
        echo "📁 Creating Docker volumes for $ENVIRONMENT..."
        docker volume create "$VOLUME_INSTANCE_NAME" || echo "Volume $VOLUME_INSTANCE_NAME already exists"
        docker volume create "$VOLUME_DATA_NAME" || echo "Volume $VOLUME_DATA_NAME already exists"
        docker volume create "$VOLUME_LOGS_NAME" || echo "Volume $VOLUME_LOGS_NAME already exists"
        echo "✅ Volumes created"
        ;;
    
    "remove")
        echo "🗑️  Removing Docker volumes for $ENVIRONMENT..."
        read -p "⚠️  This will DELETE all data\! Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            docker volume rm "$VOLUME_INSTANCE_NAME" "$VOLUME_DATA_NAME" "$VOLUME_LOGS_NAME" 2>/dev/null || echo "Some volumes may not exist"
            echo "✅ Volumes removed"
        else
            echo "❌ Operation cancelled"
        fi
        ;;
    
    "backup")
        BACKUP_DIR="./backups/$(date +%Y%m%d-%H%M%S)"
        echo "💾 Backing up volumes to $BACKUP_DIR..."
        mkdir -p "$BACKUP_DIR"
        
        docker run --rm -v "$VOLUME_INSTANCE_NAME":/source -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/instance.tar.gz -C /source .
        docker run --rm -v "$VOLUME_DATA_NAME":/source -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/data.tar.gz -C /source .
        docker run --rm -v "$VOLUME_LOGS_NAME":/source -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/logs.tar.gz -C /source .
        
        echo "✅ Backup completed: $BACKUP_DIR"
        ;;
    
    "restore")
        BACKUP_DIR=${3:-}
        if [ -z "$BACKUP_DIR" ]; then
            echo "❌ Please specify backup directory: ./manage-volumes.sh $ENVIRONMENT restore BACKUP_DIR"
            exit 1
        fi
        
        echo "🔄 Restoring volumes from $BACKUP_DIR..."
        
        docker run --rm -v "$VOLUME_INSTANCE_NAME":/target -v "$(pwd)/$BACKUP_DIR":/backup alpine tar xzf /backup/instance.tar.gz -C /target
        docker run --rm -v "$VOLUME_DATA_NAME":/target -v "$(pwd)/$BACKUP_DIR":/backup alpine tar xzf /backup/data.tar.gz -C /target
        docker run --rm -v "$VOLUME_LOGS_NAME":/target -v "$(pwd)/$BACKUP_DIR":/backup alpine tar xzf /backup/logs.tar.gz -C /target
        
        echo "✅ Restore completed"
        ;;
    
    "inspect")
        echo "🔍 Inspecting Docker volumes for $ENVIRONMENT..."
        echo "Instance Volume: $VOLUME_INSTANCE_NAME"
        docker volume inspect "$VOLUME_INSTANCE_NAME" 2>/dev/null || echo "  Volume not found"
        echo ""
        echo "Data Volume: $VOLUME_DATA_NAME"
        docker volume inspect "$VOLUME_DATA_NAME" 2>/dev/null || echo "  Volume not found"
        echo ""
        echo "Logs Volume: $VOLUME_LOGS_NAME"
        docker volume inspect "$VOLUME_LOGS_NAME" 2>/dev/null || echo "  Volume not found"
        ;;
    
    "status"|*)
        echo "📊 Docker Volume Status for $ENVIRONMENT"
        echo "Environment: $ENVIRONMENT"
        echo "Volumes:"
        echo "  Instance: $VOLUME_INSTANCE_NAME"
        echo "  Data: $VOLUME_DATA_NAME"
        echo "  Logs: $VOLUME_LOGS_NAME"
        echo ""
        echo "Volume Existence:"
        docker volume ls --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}" | grep -E "(NAME|$VOLUME_INSTANCE_NAME|$VOLUME_DATA_NAME|$VOLUME_LOGS_NAME)" || echo "No volumes found"
        echo ""
        echo "Usage:"
        echo "  ./manage-volumes.sh $ENVIRONMENT create    # Create volumes"
        echo "  ./manage-volumes.sh $ENVIRONMENT remove    # Remove volumes"
        echo "  ./manage-volumes.sh $ENVIRONMENT backup    # Backup volumes"
        echo "  ./manage-volumes.sh $ENVIRONMENT restore DIR # Restore from backup"
        echo "  ./manage-volumes.sh $ENVIRONMENT inspect   # Inspect volumes"
        ;;
esac
