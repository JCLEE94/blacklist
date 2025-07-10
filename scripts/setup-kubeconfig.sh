#!/bin/bash
# Setup kubeconfig for GitHub Actions

echo "🔧 Setting up kubeconfig..."

# Check if running in GitHub Actions
if [ -n "$GITHUB_ACTIONS" ]; then
    echo "Running in GitHub Actions environment"
    
    # Create .kube directory
    mkdir -p $HOME/.kube
    
    # Check for KUBE_CONFIG secret
    if [ -n "$KUBE_CONFIG" ]; then
        echo "Using KUBE_CONFIG from secrets"
        echo "$KUBE_CONFIG" | base64 -d > $HOME/.kube/config
        chmod 600 $HOME/.kube/config
    else
        echo "⚠️ KUBE_CONFIG secret not found"
        echo "Please add KUBE_CONFIG secret to GitHub repository:"
        echo "1. Get your kubeconfig: base64 ~/.kube/config"
        echo "2. Add to GitHub: Settings → Secrets → Actions → New repository secret"
        echo "3. Name: KUBE_CONFIG"
        echo "4. Value: <base64 encoded kubeconfig>"
    fi
else
    echo "Running in local environment"
    
    # Check for existing kubeconfig
    if [ -f "$HOME/.kube/config" ] && [ -s "$HOME/.kube/config" ]; then
        echo "✅ Using existing kubeconfig"
    else
        # Try common locations
        if [ -f "/etc/rancher/k3s/k3s.yaml" ]; then
            echo "Found k3s config"
            sudo cp /etc/rancher/k3s/k3s.yaml $HOME/.kube/config
            sudo chown $(id -u):$(id -g) $HOME/.kube/config
            chmod 600 $HOME/.kube/config
            sed -i 's/127.0.0.1/localhost/g' $HOME/.kube/config
        elif [ -f "/etc/kubernetes/admin.conf" ]; then
            echo "Found k8s admin config"
            sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
            sudo chown $(id -u):$(id -g) $HOME/.kube/config
            chmod 600 $HOME/.kube/config
        else
            echo "❌ No kubeconfig found"
            echo "Please configure kubectl manually"
            exit 1
        fi
    fi
fi

# Test connection
echo "Testing kubectl connection..."
if kubectl cluster-info &>/dev/null; then
    echo "✅ kubectl configured successfully"
    kubectl get nodes
else
    echo "❌ kubectl connection failed"
    echo "Current kubeconfig:"
    kubectl config view
    exit 1
fi