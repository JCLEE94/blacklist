#!/bin/bash
# Kubernetes utilities for blacklist CI/CD scripts

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Default values
DEFAULT_NAMESPACE="blacklist"
DEFAULT_APP_NAME="blacklist"
DEFAULT_TIMEOUT="300"

# Check Kubernetes connectivity
check_k8s_connection() {
    print_step "Checking Kubernetes connection..."
    
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        print_info "Please check your kubeconfig settings"
        return 1
    fi
    
    local context=$(kubectl config current-context)
    print_success "Connected to cluster: $context"
    return 0
}

# Get pod status
get_pod_status() {
    local namespace="${1:-$DEFAULT_NAMESPACE}"
    local app_label="${2:-app=$DEFAULT_APP_NAME}"
    
    kubectl get pods -n "$namespace" -l "$app_label" \
        --no-headers -o custom-columns=":metadata.name,:status.phase"
}

# Wait for deployment to be ready
wait_for_deployment() {
    local deployment="${1:-$DEFAULT_APP_NAME}"
    local namespace="${2:-$DEFAULT_NAMESPACE}"
    local timeout="${3:-$DEFAULT_TIMEOUT}"
    
    print_step "Waiting for deployment $deployment to be ready..."
    
    if kubectl rollout status deployment/"$deployment" \
        -n "$namespace" \
        --timeout="${timeout}s"; then
        print_success "Deployment $deployment is ready"
        return 0
    else
        print_error "Deployment $deployment failed to become ready within ${timeout}s"
        return 1
    fi
}

# Get deployment info
get_deployment_info() {
    local deployment="${1:-$DEFAULT_APP_NAME}"
    local namespace="${2:-$DEFAULT_NAMESPACE}"
    
    print_step "Deployment information for $deployment:"
    
    # Get basic deployment info
    kubectl get deployment "$deployment" -n "$namespace" \
        -o custom-columns=\
"NAME:.metadata.name,\
READY:.status.readyReplicas,\
DESIRED:.spec.replicas,\
IMAGE:.spec.template.spec.containers[0].image"
    
    echo ""
    
    # Get pod information
    print_info "Pod status:"
    kubectl get pods -n "$namespace" -l "app=$deployment" \
        -o custom-columns=\
"POD:.metadata.name,\
STATUS:.status.phase,\
RESTARTS:.status.containerStatuses[0].restartCount,\
AGE:.metadata.creationTimestamp"
}

# Scale deployment
scale_deployment() {
    local deployment="${1:-$DEFAULT_APP_NAME}"
    local replicas="${2:-3}"
    local namespace="${3:-$DEFAULT_NAMESPACE}"
    
    print_step "Scaling deployment $deployment to $replicas replicas..."
    
    kubectl scale deployment/"$deployment" \
        --replicas="$replicas" \
        -n "$namespace"
    
    if [[ $? -eq 0 ]]; then
        print_success "Scaled deployment to $replicas replicas"
        wait_for_deployment "$deployment" "$namespace"
    else
        print_error "Failed to scale deployment"
        return 1
    fi
}

# Get logs from deployment
get_deployment_logs() {
    local deployment="${1:-$DEFAULT_APP_NAME}"
    local namespace="${2:-$DEFAULT_NAMESPACE}"
    local tail_lines="${3:-100}"
    local follow="${4:-false}"
    
    print_step "Getting logs from deployment $deployment..."
    
    local follow_flag=""
    if [[ "$follow" == "true" ]]; then
        follow_flag="-f"
    fi
    
    kubectl logs deployment/"$deployment" \
        -n "$namespace" \
        --tail="$tail_lines" \
        --all-containers=true \
        --prefix=true \
        $follow_flag
}

# Execute command in pod
exec_in_pod() {
    local command="$1"
    local deployment="${2:-$DEFAULT_APP_NAME}"
    local namespace="${3:-$DEFAULT_NAMESPACE}"
    
    # Get first running pod
    local pod=$(kubectl get pods -n "$namespace" \
        -l "app=$deployment" \
        -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | \
        awk '{print $1}')
    
    if [[ -z "$pod" ]]; then
        print_error "No running pod found for deployment $deployment"
        return 1
    fi
    
    print_step "Executing command in pod $pod..."
    kubectl exec -n "$namespace" "$pod" -- $command
}

# Apply Kubernetes manifests
apply_manifests() {
    local manifest_path="${1:-k8s/}"
    
    print_step "Applying Kubernetes manifests from $manifest_path..."
    
    if [[ -f "$manifest_path" ]]; then
        # Single file
        kubectl apply -f "$manifest_path"
    elif [[ -d "$manifest_path" ]]; then
        # Directory - use kustomize if available
        if [[ -f "$manifest_path/kustomization.yaml" ]]; then
            print_info "Using Kustomize to apply manifests"
            kubectl apply -k "$manifest_path"
        else
            # Apply all YAML files in directory
            kubectl apply -f "$manifest_path"
        fi
    else
        print_error "Manifest path not found: $manifest_path"
        return 1
    fi
}

# Delete Kubernetes resources
delete_resources() {
    local manifest_path="${1:-k8s/}"
    
    print_step "Deleting Kubernetes resources from $manifest_path..."
    
    if [[ -f "$manifest_path" ]]; then
        kubectl delete -f "$manifest_path" --ignore-not-found=true
    elif [[ -d "$manifest_path" ]]; then
        if [[ -f "$manifest_path/kustomization.yaml" ]]; then
            kubectl delete -k "$manifest_path" --ignore-not-found=true
        else
            kubectl delete -f "$manifest_path" --ignore-not-found=true
        fi
    fi
}

# Port forward to service
port_forward() {
    local local_port="${1:-8541}"
    local service_port="${2:-8541}"
    local service="${3:-$DEFAULT_APP_NAME}"
    local namespace="${4:-$DEFAULT_NAMESPACE}"
    
    print_step "Port forwarding localhost:$local_port -> $service:$service_port"
    print_info "Press Ctrl+C to stop port forwarding"
    
    kubectl port-forward -n "$namespace" "svc/$service" \
        "$local_port:$service_port"
}

# Get service URL
get_service_url() {
    local service="${1:-$DEFAULT_APP_NAME}"
    local namespace="${2:-$DEFAULT_NAMESPACE}"
    
    # Check for LoadBalancer
    local external_ip=$(kubectl get svc "$service" -n "$namespace" \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    
    if [[ -n "$external_ip" ]]; then
        echo "http://$external_ip"
        return
    fi
    
    # Check for NodePort
    local node_port=$(kubectl get svc "$service" -n "$namespace" \
        -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    
    if [[ -n "$node_port" ]]; then
        local node_ip=$(kubectl get nodes \
            -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null)
        
        if [[ -z "$node_ip" ]]; then
            node_ip=$(kubectl get nodes \
                -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null)
        fi
        
        if [[ -n "$node_ip" ]]; then
            echo "http://$node_ip:$node_port"
            return
        fi
    fi
    
    # Check for Ingress
    local ingress_host=$(kubectl get ingress -n "$namespace" \
        -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null)
    
    if [[ -n "$ingress_host" ]]; then
        echo "https://$ingress_host"
        return
    fi
    
    echo "No external URL found. Use port-forward to access the service."
}

# Export Kubernetes functions
export -f check_k8s_connection get_pod_status wait_for_deployment
export -f get_deployment_info scale_deployment get_deployment_logs
export -f exec_in_pod apply_manifests delete_resources
export -f port_forward get_service_url