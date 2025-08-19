#!/bin/bash
# Generate GitHub Pages portfolio content

echo "📊 Generating portfolio documentation..."

# Ensure docs directory exists
mkdir -p docs/{assets,portfolio}

# Generate main portfolio page
cat > docs/index.html << 'HTML'
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blacklist Management System - Portfolio</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        header {
            text-align: center;
            padding: 3rem 0;
            animation: fadeInDown 1s;
        }
        
        h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
            margin: 3rem 0;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            animation: fadeInUp 1s;
            transition: transform 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            background: rgba(255,255,255,0.15);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            opacity: 0.9;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 3rem 0;
        }
        
        .feature-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 2rem;
            animation: fadeIn 1.5s;
        }
        
        .feature-card h3 {
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }
        
        .tech-stack {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 2rem 0;
        }
        
        .tech-tag {
            background: rgba(255,255,255,0.2);
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-size: 0.9rem;
        }
        
        .deployment-comparison {
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            padding: 2rem;
            margin: 2rem 0;
        }
        
        .comparison-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-top: 1.5rem;
        }
        
        .deployment-option {
            background: rgba(255,255,255,0.1);
            padding: 1.5rem;
            border-radius: 10px;
        }
        
        .cta {
            text-align: center;
            margin: 3rem 0;
        }
        
        .btn {
            display: inline-block;
            padding: 1rem 2rem;
            background: rgba(255,255,255,0.2);
            color: #fff;
            text-decoration: none;
            border-radius: 30px;
            margin: 0 0.5rem;
            transition: all 0.3s;
        }
        
        .btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .implementation-showcase {
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 2rem;
            margin: 2rem 0;
        }
        
        .code-preview {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9rem;
            margin: 1rem 0;
        }
        
        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            background: #4CAF50;
            color: white;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-right: 0.5rem;
        }
        
        .badge.k8s { background: #326CE5; }
        .badge.docker { background: #2496ED; }
        .badge.cicd { background: #FF6B6B; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛡️ Blacklist Management System</h1>
            <p class="subtitle">Enterprise Threat Intelligence Platform with Dual Deployment Support</p>
            <p style="margin-top: 1rem;">
                <span class="badge k8s">Kubernetes</span>
                <span class="badge docker">Docker Compose</span>
                <span class="badge cicd">GitOps</span>
            </p>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">95%</div>
                <div class="stat-label">Test Coverage</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">7.58ms</div>
                <div class="stat-label">API Response</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">2</div>
                <div class="stat-label">Deployment Platforms</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">25+</div>
                <div class="stat-label">API Endpoints</div>
            </div>
        </div>
        
        <div class="implementation-showcase">
            <h2>🎯 Core Implementation Highlights</h2>
            <p style="margin: 1rem 0;">Successfully implemented dual deployment strategy supporting both Kubernetes and Docker Compose environments</p>
            
            <div class="code-preview">
# Kubernetes Deployment (Production)
kubectl apply -f k8s/
argocd app sync blacklist
kubectl get pods -n blacklist

# Docker Compose Deployment (Development)
docker-compose up -d
docker-compose ps
curl http://localhost:32542/health
            </div>
        </div>
        
        <div class="deployment-comparison">
            <h2>🚀 Deployment Architecture Comparison</h2>
            <div class="comparison-grid">
                <div class="deployment-option">
                    <h3>☸️ Kubernetes</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li>✅ Auto-scaling with HPA</li>
                        <li>✅ Rolling updates</li>
                        <li>✅ Service mesh ready</li>
                        <li>✅ Multi-replica HA</li>
                        <li>✅ Resource quotas</li>
                        <li>✅ RBAC security</li>
                        <li>✅ ArgoCD GitOps</li>
                    </ul>
                </div>
                <div class="deployment-option">
                    <h3>🐳 Docker Compose</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li>✅ Simple deployment</li>
                        <li>✅ Local development</li>
                        <li>✅ Resource efficient</li>
                        <li>✅ Quick setup</li>
                        <li>✅ Volume management</li>
                        <li>✅ Network isolation</li>
                        <li>✅ Environment config</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="features">
            <div class="feature-card">
                <h3>🏗️ Architecture</h3>
                <p>Microservices-ready architecture with both K8s and Docker Compose support. Implemented service discovery, load balancing, and health checks for both platforms.</p>
            </div>
            <div class="feature-card">
                <h3>🔄 GitOps Pipeline</h3>
                <p>Fully automated CI/CD with GitHub Actions, ArgoCD for K8s, and Watchtower for Docker Compose. Self-hosted runners for enhanced performance.</p>
            </div>
            <div class="feature-card">
                <h3>📦 Offline Deployment</h3>
                <p>Complete air-gap package for RHEL 8 environments. All dependencies included, zero internet requirement for installation.</p>
            </div>
            <div class="feature-card">
                <h3>🔒 Security</h3>
                <p>JWT + API Key dual authentication, Fernet encryption, automated secret rotation, network policies for both deployment types.</p>
            </div>
            <div class="feature-card">
                <h3>📊 Monitoring</h3>
                <p>Prometheus metrics (55 custom metrics), health checks, performance baselines. ServiceMonitor for K8s, direct metrics for Docker.</p>
            </div>
            <div class="feature-card">
                <h3>🧪 Testing</h3>
                <p>95% test coverage with pytest, integration tests for both deployment types, automated testing in CI/CD pipeline.</p>
            </div>
        </div>
        
        <div class="tech-stack">
            <span class="tech-tag">Python 3.9</span>
            <span class="tech-tag">Flask</span>
            <span class="tech-tag">PostgreSQL</span>
            <span class="tech-tag">Redis</span>
            <span class="tech-tag">Docker</span>
            <span class="tech-tag">Kubernetes</span>
            <span class="tech-tag">ArgoCD</span>
            <span class="tech-tag">GitHub Actions</span>
            <span class="tech-tag">Prometheus</span>
            <span class="tech-tag">Nginx</span>
            <span class="tech-tag">Helm</span>
            <span class="tech-tag">GitOps</span>
        </div>
        
        <div class="cta">
            <a href="https://github.com/JCLEE94/blacklist" class="btn">📁 View Source</a>
            <a href="https://blacklist.jclee.me" class="btn">🌐 Live Demo</a>
        </div>
        
        <footer style="text-align: center; margin-top: 3rem; opacity: 0.8;">
            <p>© 2025 JC Lee - DevOps & Security Engineer</p>
            <p style="margin-top: 0.5rem;">Enterprise-grade threat intelligence platform with dual deployment architecture</p>
        </footer>
    </div>
    
    <script>
        // Animate numbers on scroll
        const animateValue = (obj, start, end, duration) => {
            let startTimestamp = null;
            const step = (timestamp) => {
                if (!startTimestamp) startTimestamp = timestamp;
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                obj.innerHTML = Math.floor(progress * (end - start) + start);
                if (progress < 1) {
                    window.requestAnimationFrame(step);
                }
            };
            window.requestAnimationFrame(step);
        };
        
        // Animate stats when visible
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const statNumbers = entry.target.querySelectorAll('.stat-number');
                    statNumbers.forEach(stat => {
                        const value = stat.innerText;
                        if (value.includes('%')) {
                            animateValue(stat, 0, 95, 2000);
                            setTimeout(() => { stat.innerHTML = '95%'; }, 2000);
                        }
                    });
                }
            });
        });
        
        document.querySelectorAll('.stats').forEach(el => observer.observe(el));
    </script>
</body>
</html>
HTML

# Create necessary marker files
touch docs/.nojekyll

echo "✅ Portfolio generation complete!"