#!/bin/bash

#################################################################################
# Jenkins Setup Script for Blacklist Management System
# This script sets up Jenkins with all required plugins and configurations
#################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
JENKINS_URL="http://localhost:8080"
JENKINS_HOME="/var/jenkins_home"
ADMIN_USER="admin"
ADMIN_PASS="admin123!@#"  # Change this in production

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Jenkins Setup for Blacklist System${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to wait for Jenkins to be ready
wait_for_jenkins() {
    echo -e "${YELLOW}Waiting for Jenkins to start...${NC}"
    while ! curl -s -o /dev/null -w "%{http_code}" ${JENKINS_URL} | grep -q "200\|403"; do
        sleep 5
        echo -n "."
    done
    echo -e "\n${GREEN}Jenkins is ready!${NC}"
}

# Function to get initial admin password
get_initial_password() {
    if [ -f "${JENKINS_HOME}/secrets/initialAdminPassword" ]; then
        INITIAL_PASS=$(cat ${JENKINS_HOME}/secrets/initialAdminPassword)
        echo -e "${GREEN}Initial admin password: ${INITIAL_PASS}${NC}"
    else
        echo -e "${RED}Initial admin password not found${NC}"
    fi
}

# Function to install plugins
install_plugins() {
    echo -e "${YELLOW}Installing required plugins...${NC}"
    
    PLUGINS=(
        "git"
        "github"
        "github-branch-source"
        "workflow-aggregator"
        "pipeline-stage-view"
        "docker-workflow"
        "docker-plugin"
        "credentials-binding"
        "timestamper"
        "ws-cleanup"
        "ansicolor"
        "build-timeout"
        "email-ext"
        "slack"
        "htmlpublisher"
        "junit"
        "cobertura"
        "performance"
        "blueocean"
        "kubernetes"
        "kubernetes-cli"
        "kubernetes-credentials-provider"
        "trivy"
    )
    
    for plugin in "${PLUGINS[@]}"; do
        echo "Installing plugin: ${plugin}"
        java -jar jenkins-cli.jar -s ${JENKINS_URL} -auth ${ADMIN_USER}:${ADMIN_PASS} \
            install-plugin ${plugin} -restart || true
    done
    
    echo -e "${GREEN}Plugins installation completed${NC}"
}

# Function to create credentials
create_credentials() {
    echo -e "${YELLOW}Creating Jenkins credentials...${NC}"
    
    # Create credentials.xml template
    cat > /tmp/credentials.xml <<EOF
<com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>
  <scope>GLOBAL</scope>
  <id>registry-jclee-credentials</id>
  <description>Docker Registry Credentials</description>
  <username>jclee94</username>
  <password>bingogo1</password>
</com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>
EOF
    
    # Import credentials
    java -jar jenkins-cli.jar -s ${JENKINS_URL} -auth ${ADMIN_USER}:${ADMIN_PASS} \
        create-credentials-by-xml system::system::jenkins _ < /tmp/credentials.xml
    
    echo -e "${GREEN}Credentials created successfully${NC}"
}

# Function to create Jenkins job
create_job() {
    echo -e "${YELLOW}Creating Jenkins job for Blacklist...${NC}"
    
    # Create job config
    cat > /tmp/job-config.xml <<'EOF'
<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <actions/>
  <description>Blacklist Management System CI/CD Pipeline</description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
      <triggers>
        <hudson.triggers.SCMTrigger>
          <spec>H/5 * * * *</spec>
          <ignorePostCommitHooks>false</ignorePostCommitHooks>
        </hudson.triggers.SCMTrigger>
      </triggers>
    </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
    <com.coravy.hudson.plugins.github.GithubProjectProperty>
      <projectUrl>https://github.com/qws941/blacklist/</projectUrl>
    </com.coravy.hudson.plugins.github.GithubProjectProperty>
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition">
    <scm class="hudson.plugins.git.GitSCM">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>https://github.com/qws941/blacklist.git</url>
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>*/main</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="list"/>
      <extensions/>
    </scm>
    <scriptPath>Jenkinsfile</scriptPath>
    <lightweight>true</lightweight>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>
EOF
    
    # Create job
    java -jar jenkins-cli.jar -s ${JENKINS_URL} -auth ${ADMIN_USER}:${ADMIN_PASS} \
        create-job blacklist-pipeline < /tmp/job-config.xml
    
    echo -e "${GREEN}Jenkins job created successfully${NC}"
}

# Function to setup Docker in Jenkins
setup_docker() {
    echo -e "${YELLOW}Setting up Docker in Jenkins...${NC}"
    
    # Install Docker CLI in Jenkins container
    docker exec jenkins bash -c "
        apt-get update && \
        apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release && \
        curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
        echo 'deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \$(lsb_release -cs) stable' | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
        apt-get update && \
        apt-get install -y docker-ce-cli
    "
    
    # Add jenkins user to docker group
    docker exec jenkins usermod -aG docker jenkins || true
    
    echo -e "${GREEN}Docker setup completed${NC}"
}

# Function to setup Python environment
setup_python() {
    echo -e "${YELLOW}Setting up Python environment...${NC}"
    
    docker exec jenkins bash -c "
        apt-get update && \
        apt-get install -y python3.11 python3.11-venv python3-pip && \
        python3.11 -m pip install --upgrade pip
    "
    
    echo -e "${GREEN}Python setup completed${NC}"
}

# Main setup flow
main() {
    echo -e "${GREEN}Starting Jenkins setup...${NC}"
    
    # Start Jenkins if not running
    if ! docker ps | grep -q jenkins; then
        echo -e "${YELLOW}Starting Jenkins container...${NC}"
        docker-compose -f jenkins/docker-compose.jenkins.yml up -d
    fi
    
    # Wait for Jenkins
    wait_for_jenkins
    
    # Get initial password
    get_initial_password
    
    # Download Jenkins CLI
    echo -e "${YELLOW}Downloading Jenkins CLI...${NC}"
    wget ${JENKINS_URL}/jnlpJars/jenkins-cli.jar -O jenkins-cli.jar
    
    # Setup components
    setup_docker
    setup_python
    
    # Note: Manual steps required for first setup
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Manual Setup Required:${NC}"
    echo -e "${YELLOW}1. Access Jenkins at ${JENKINS_URL}${NC}"
    echo -e "${YELLOW}2. Use initial admin password shown above${NC}"
    echo -e "${YELLOW}3. Install suggested plugins${NC}"
    echo -e "${YELLOW}4. Create admin user${NC}"
    echo -e "${YELLOW}5. Run this script again after initial setup${NC}"
    echo -e "${YELLOW}========================================${NC}"
    
    read -p "Have you completed the initial setup? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_plugins
        create_credentials
        create_job
        
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Jenkins setup completed successfully!${NC}"
        echo -e "${GREEN}Access Jenkins at: ${JENKINS_URL}${NC}"
        echo -e "${GREEN}Job created: blacklist-pipeline${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        echo -e "${YELLOW}Please complete the initial setup first${NC}"
    fi
}

# Run main function
main