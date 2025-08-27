// Shared Pipeline Library for Blacklist Management System

def call(Map config = [:]) {
    pipeline {
        agent any
        
        environment {
            // Merge default config with provided config
            REGISTRY = config.registry ?: 'registry.jclee.me'
            IMAGE_NAME = config.imageName ?: 'blacklist'
            PYTHON_VERSION = config.pythonVersion ?: '3.11'
        }
        
        stages {
            stage('Quality Gates') {
                steps {
                    script {
                        runQualityGates()
                    }
                }
            }
            
            stage('Security Scan') {
                steps {
                    script {
                        runSecurityScans()
                    }
                }
            }
            
            stage('Build & Deploy') {
                when {
                    branch 'main'
                }
                steps {
                    script {
                        buildAndDeploy()
                    }
                }
            }
        }
    }
}

def runQualityGates() {
    echo "Running quality gates..."
    
    // Code formatting
    sh """
        . venv/bin/activate
        black --check src/ tests/
        isort --check-only src/ tests/
        flake8 src/ tests/
    """
    
    // Test coverage
    sh """
        . venv/bin/activate
        pytest --cov=src --cov-report=xml --cov-report=html
    """
    
    // Publish reports
    publishHTML([
        reportDir: 'htmlcov',
        reportFiles: 'index.html',
        reportName: 'Coverage Report'
    ])
}

def runSecurityScans() {
    echo "Running security scans..."
    
    // Bandit security scan
    sh """
        . venv/bin/activate
        bandit -r src/ -f json -o bandit-report.json
    """
    
    // Safety dependency check
    sh """
        . venv/bin/activate
        safety check --json --output safety-report.json
    """
    
    // Trivy scan
    sh """
        trivy fs --exit-code 0 --severity MEDIUM,HIGH,CRITICAL .
    """
}

def buildAndDeploy() {
    echo "Building and deploying..."
    
    // Build Docker image
    def version = sh(
        script: "jq -r '.version' package.json",
        returnStdout: true
    ).trim()
    
    docker.build("${REGISTRY}/${IMAGE_NAME}:${version}")
    docker.build("${REGISTRY}/${IMAGE_NAME}:latest")
    
    // Push to registry
    docker.withRegistry("https://${REGISTRY}", 'registry-credentials') {
        docker.image("${REGISTRY}/${IMAGE_NAME}:${version}").push()
        docker.image("${REGISTRY}/${IMAGE_NAME}:latest").push()
    }
    
    // Deploy using Blue-Green strategy
    deployBlueGreen(version)
}

def deployBlueGreen(version) {
    echo "Deploying version ${version} using Blue-Green strategy..."
    
    sh """
        # Implementation of Blue-Green deployment
        ./scripts/deploy-blue-green.sh ${version}
    """
}

return this