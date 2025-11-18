# Guide de Déploiement - Analyseur de Documents FilAgent

**Version**: 1.0.0
**Date**: 2025-11-18
**Audience**: Administrateurs systèmes, DevOps, Responsables IT

---

## Table des Matières

1. [Prérequis](#prérequis)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Tests de validation](#tests-de-validation)
5. [Déploiement en production](#déploiement-en-production)
6. [Monitoring et maintenance](#monitoring-et-maintenance)
7. [Sécurité](#sécurité)
8. [Troubleshooting](#troubleshooting)
9. [Rollback](#rollback)

---

## Prérequis

### Système d'exploitation

**Compatible avec**:
- ✅ macOS 10.15+ (Catalina et plus récent)
- ✅ Ubuntu 20.04+ / Debian 11+
- ✅ Windows 10/11 (avec WSL2 recommandé)

**Recommandation production**: Ubuntu 22.04 LTS Server

---

### Ressources matérielles

| Ressource | Minimum | Recommandé | Production |
|-----------|---------|------------|------------|
| CPU | 2 cores | 4 cores | 8+ cores |
| RAM | 4 GB | 8 GB | 16+ GB |
| Disque | 10 GB | 50 GB | 200+ GB (logs) |
| Réseau | 10 Mbps | 100 Mbps | 1 Gbps |

**Notes**:
- Le traitement de fichiers volumineux (>20 MB) nécessite 8+ GB RAM
- Les logs d'audit peuvent croître rapidement (planifier rotation)
- IOPS élevés recommandés pour `/logs` (SSD de préférence)

---

### Logiciels requis

#### Python

**Version**: Python 3.10, 3.11, 3.12, 3.13, ou 3.14

**Installation (Ubuntu)**:
```bash
# Python 3.12 recommandé
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

**Installation (macOS)**:
```bash
# Homebrew
brew install python@3.12
```

**Vérification**:
```bash
python3 --version  # Devrait afficher 3.10+
```

---

#### PDM (Package Manager)

**Installation**:
```bash
# Via pip
pip install --user pdm

# Via Homebrew (macOS)
brew install pdm

# Vérification
pdm --version
```

**Alternative**: Si PDM non disponible, utiliser pip avec `requirements.txt`

---

#### Dépendances système

**Ubuntu/Debian**:
```bash
sudo apt install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git \
    curl
```

**macOS**:
```bash
# Xcode Command Line Tools
xcode-select --install
```

---

## Installation

### 1. Cloner le dépôt

```bash
# HTTPS
git clone https://github.com/your-org/FilAgent.git
cd FilAgent

# SSH (si configuré)
git clone git@github.com:your-org/FilAgent.git
cd FilAgent
```

---

### 2. Installer les dépendances

**Avec PDM (recommandé)**:
```bash
# Installation complète
pdm install

# Avec groupes optionnels
pdm install -G ui      # Interface Gradio (requis pour Document Analyzer)
pdm install -G dev     # Outils de développement
pdm install -G ml      # Dépendances ML (si besoin)
```

**Avec pip** (fallback):
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
.\venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

---

### 3. Vérifier les dépendances Document Analyzer

Les dépendances critiques pour l'analyseur de documents:

```bash
pdm run python -c "
import PyPDF2
import openpyxl
import pandas
import docx
print('✅ Toutes les dépendances Document Analyzer sont installées')
"
```

**Si erreurs**, réinstaller manuellement:
```bash
pdm add PyPDF2 openpyxl pandas python-docx
```

---

## Configuration

### 1. Fichier de configuration principal

**Fichier**: `config/agent.yaml`

**Section Document Analyzer**:
```yaml
# Document Analyzer Tool Configuration
document_analyzer:
  enabled: true
  max_file_size_mb: 50          # Taille maximale des fichiers
  processing_timeout_seconds: 30 # Timeout de traitement
  supported_extensions:
    - .pdf
    - .docx
    - .xlsx
    - .xls
  temp_directory: /tmp/filagent  # Répertoire temporaire
  cleanup_on_error: true         # Cleanup automatique en cas d'erreur

# Compliance settings
compliance:
  loi25:
    enabled: true
    pii_redaction: true          # Redaction PII obligatoire
    decision_records: true       # DR pour chaque analyse
```

---

### 2. Variables d'environnement

**Fichier**: `.env` (créer à la racine du projet)

```bash
# FilAgent Core
FILAGENT_ENV=production           # ou "development", "staging"
FILAGENT_LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR

# Document Analyzer
DOCUMENT_ANALYZER_MAX_SIZE_MB=50
DOCUMENT_ANALYZER_TIMEOUT=30
DOCUMENT_ANALYZER_TEMP_DIR=/var/tmp/filagent

# Perplexity API (si utilisé pour analyse assistée)
PERPLEXITY_API_KEY=your_api_key_here

# OpenAI (optionnel)
OPENAI_API_KEY=your_openai_key_here

# Paths
LOGS_DIR=/var/log/filagent
DECISIONS_DIR=/var/log/filagent/decisions
AUDIT_DIR=/var/log/filagent/audit
```

**Permissions**:
```bash
chmod 600 .env  # Lecture/écriture propriétaire uniquement
```

---

### 3. Structure des répertoires

**Créer les répertoires requis**:
```bash
# Logs et audit
sudo mkdir -p /var/log/filagent/{events,decisions,audit,safeties,prompts}
sudo chown -R $USER:$USER /var/log/filagent
chmod 750 /var/log/filagent

# Temp files (cleanup automatique)
mkdir -p /var/tmp/filagent
chmod 1777 /var/tmp/filagent  # Sticky bit pour sécurité

# Optional: Backup des Decision Records
mkdir -p /var/backup/filagent/decisions
```

---

### 4. Configuration Gradio

**Fichier**: `gradio_app_production.py` (ligne ~1700-1750)

**Paramètres de l'interface**:
```python
# Configuration du serveur Gradio
demo.launch(
    server_name="0.0.0.0",      # Écouter sur toutes les interfaces
    server_port=7860,            # Port par défaut
    share=False,                 # Ne PAS créer de tunnel public (sécurité)
    auth=None,                   # Authentication (voir section Sécurité)
    ssl_keyfile=None,            # SSL/TLS (recommandé en production)
    ssl_certfile=None,
    show_error=True,             # Afficher erreurs en dev (False en prod)
    quiet=False
)
```

**Pour production avec HTTPS**:
```python
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=False,
    auth=("admin", "secure_password_here"),  # Authentication basique
    ssl_keyfile="/etc/ssl/private/filagent.key",
    ssl_certfile="/etc/ssl/certs/filagent.crt",
    show_error=False,  # Ne pas exposer stack traces
    quiet=True
)
```

---

## Tests de validation

### 1. Tests unitaires

**Exécuter tous les tests**:
```bash
pdm run pytest tests/test_document_analyzer_error_handling.py -v
```

**Résultats attendus**:
```
tests/test_document_analyzer_error_handling.py::TestValidateFile::test_validate_nonexistent_file PASSED
tests/test_document_analyzer_error_handling.py::TestValidateFile::test_validate_unsupported_extension PASSED
tests/test_document_analyzer_error_handling.py::TestValidateFile::test_validate_valid_excel PASSED
tests/test_document_analyzer_error_handling.py::TestValidateFile::test_validate_valid_pdf PASSED
tests/test_document_analyzer_error_handling.py::TestValidateFile::test_validate_valid_word PASSED
...
======================== 21 passed in 5.23s ========================
```

**Si échecs**: Voir section [Troubleshooting](#troubleshooting)

---

### 2. Tests de conformité

**Exécuter tests Loi 25/PIPEDA/RGPD**:
```bash
pdm run pytest tests/test_compliance_document_analyzer.py -v -m compliance
```

**Résultats attendus**:
```
tests/test_compliance_document_analyzer.py::TestLoi25Compliance::test_data_minimization PASSED
tests/test_compliance_document_analyzer.py::TestLoi25Compliance::test_consent_mechanism PASSED
tests/test_compliance_document_analyzer.py::TestLoi25Compliance::test_data_accuracy PASSED
tests/test_compliance_document_analyzer.py::TestLoi25Compliance::test_security_measures PASSED
tests/test_compliance_document_analyzer.py::TestLoi25Compliance::test_retention_deletion PASSED
...
======================== 15 passed, 3 warnings in 8.45s ========================
```

**Compliance Score**: 100% (15/15 tests réglementaires)

**3 warnings**: Ce sont des best practices (non-bloquantes)

---

### 3. Tests d'intégration

**Test complet end-to-end**:
```bash
# Démarrer l'interface
pdm run python gradio_app_production.py &
GRADIO_PID=$!

# Attendre démarrage
sleep 5

# Tester l'endpoint
curl -X POST http://localhost:7860/api/predict \
  -H "Content-Type: application/json" \
  -d '{"data": ["test"]}'

# Arrêter
kill $GRADIO_PID
```

**Résultat attendu**: Réponse HTTP 200 avec JSON valide

---

### 4. Test de charge (optionnel)

**Installation**:
```bash
pip install locust
```

**Fichier**: `tests/load/locustfile.py`
```python
from locust import HttpUser, task, between

class DocumentAnalyzerUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def analyze_document(self):
        # Simuler upload et analyse
        files = {'file': open('tests/fixtures/valid_invoice.xlsx', 'rb')}
        self.client.post("/analyze", files=files, data={"analysis_type": "invoice"})
```

**Exécution**:
```bash
locust -f tests/load/locustfile.py --host=http://localhost:7860
```

**Objectifs de performance**:
- 10 utilisateurs simultanés: < 2s response time
- 50 utilisateurs simultanés: < 5s response time
- 0% taux d'erreur

---

## Déploiement en production

### Option 1: Systemd (Ubuntu/Debian)

**Fichier**: `/etc/systemd/system/filagent-gradio.service`

```ini
[Unit]
Description=FilAgent Document Analyzer (Gradio Interface)
After=network.target

[Service]
Type=simple
User=filagent
Group=filagent
WorkingDirectory=/opt/filagent
Environment="PATH=/opt/filagent/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/filagent"
EnvironmentFile=/opt/filagent/.env
ExecStart=/opt/filagent/venv/bin/python gradio_app_production.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/filagent/gradio.log
StandardError=append:/var/log/filagent/gradio-error.log

# Sécurité
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/filagent /var/tmp/filagent

[Install]
WantedBy=multi-user.target
```

**Commandes**:
```bash
# Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable filagent-gradio
sudo systemctl start filagent-gradio

# Vérifier statut
sudo systemctl status filagent-gradio

# Voir les logs
sudo journalctl -u filagent-gradio -f
```

---

### Option 2: Docker (recommandé pour isolation)

**Fichier**: `Dockerfile.gradio`

```dockerfile
FROM python:3.12-slim

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer utilisateur non-root
RUN useradd -m -u 1000 filagent

# Workspace
WORKDIR /app
COPY --chown=filagent:filagent . /app

# Installer dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Créer répertoires
RUN mkdir -p /var/log/filagent /var/tmp/filagent && \
    chown -R filagent:filagent /var/log/filagent /var/tmp/filagent

# Switch to non-root user
USER filagent

# Expose port
EXPOSE 7860

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Start
CMD ["python", "gradio_app_production.py"]
```

**Build et run**:
```bash
# Build
docker build -t filagent-gradio:v2.3.0 -f Dockerfile.gradio .

# Run
docker run -d \
    --name filagent-gradio \
    -p 7860:7860 \
    -v /var/log/filagent:/var/log/filagent \
    -v /var/tmp/filagent:/var/tmp/filagent \
    --env-file .env \
    --restart unless-stopped \
    filagent-gradio:v2.3.0

# Logs
docker logs -f filagent-gradio
```

---

### Option 3: Docker Compose (multi-services)

**Fichier**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  gradio:
    build:
      context: .
      dockerfile: Dockerfile.gradio
    container_name: filagent-gradio
    ports:
      - "7860:7860"
    volumes:
      - ./logs:/var/log/filagent
      - ./temp:/var/tmp/filagent
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7860/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # FastAPI server (optionnel)
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: filagent-api
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/var/log/filagent
    env_file:
      - .env
    restart: unless-stopped

volumes:
  logs:
  temp:
```

**Commandes**:
```bash
# Démarrer tous les services
docker-compose up -d

# Voir logs
docker-compose logs -f gradio

# Arrêter
docker-compose down
```

---

### Option 4: Kubernetes (production à grande échelle)

**Fichier**: `k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: filagent-gradio
  labels:
    app: filagent-gradio
spec:
  replicas: 3
  selector:
    matchLabels:
      app: filagent-gradio
  template:
    metadata:
      labels:
        app: filagent-gradio
    spec:
      containers:
      - name: gradio
        image: filagent-gradio:v2.3.0
        ports:
        - containerPort: 7860
        envFrom:
        - secretRef:
            name: filagent-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /
            port: 7860
          initialDelaySeconds: 30
          periodSeconds: 10
        volumeMounts:
        - name: logs
          mountPath: /var/log/filagent
      volumes:
      - name: logs
        persistentVolumeClaim:
          claimName: filagent-logs-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: filagent-gradio-service
spec:
  selector:
    app: filagent-gradio
  ports:
  - protocol: TCP
    port: 80
    targetPort: 7860
  type: LoadBalancer
```

**Déploiement**:
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml  # Si Ingress configuré
```

---

## Monitoring et maintenance

### 1. Logs à surveiller

**Structure des logs**:
```
/var/log/filagent/
├── events/                  # Logs d'événements (JSONL)
│   └── 2025-11-18.jsonl
├── decisions/               # Decision Records (JSON avec signature)
│   └── DR-20251118-*.json
├── audit/                   # Logs d'audit WORM
│   └── audit.log
├── gradio.log              # Logs Gradio (stdout)
└── gradio-error.log        # Logs Gradio (stderr)
```

---

### 2. Métriques à surveiller

**Application**:
- Nombre d'analyses par heure
- Temps moyen de traitement
- Taux d'erreur (doit être < 1%)
- Taille moyenne des fichiers traités

**Système**:
- CPU utilization (< 70% en moyenne)
- RAM utilization (< 80%)
- Disk I/O (SSD recommandé pour `/var/log`)
- Espace disque disponible (alerte si < 20%)

**Exemple avec Prometheus** (optionnel):
```python
# Dans gradio_app_production.py
from prometheus_client import Counter, Histogram, start_http_server

# Métriques
ANALYSES_TOTAL = Counter('filagent_analyses_total', 'Total analyses')
ANALYSIS_DURATION = Histogram('filagent_analysis_duration_seconds', 'Analysis duration')
ERRORS_TOTAL = Counter('filagent_errors_total', 'Total errors')

# Démarrer serveur Prometheus
start_http_server(9090)
```

---

### 3. Rotation des logs

**Fichier**: `/etc/logrotate.d/filagent`

```
/var/log/filagent/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0640 filagent filagent
    sharedscripts
    postrotate
        systemctl reload filagent-gradio > /dev/null 2>&1 || true
    endscript
}

# Decision Records - IMPORTANT: Ne JAMAIS supprimer (rétention 7 ans)
/var/log/filagent/decisions/*.json {
    # Pas de rotation, archivage uniquement
    compress
    delaycompress
    notifempty
    missingok
    dateext
    dateformat -%Y%m%d
    # Copier vers backup au lieu de supprimer
    sharedscripts
    postrotate
        rsync -a /var/log/filagent/decisions/ /var/backup/filagent/decisions/
    endscript
}
```

**Activer**:
```bash
sudo logrotate -f /etc/logrotate.d/filagent
```

---

### 4. Backup des Decision Records

**Importance**: Les Decision Records (DR) sont légalement requis pour 7 ans (Loi 25).

**Script**: `/usr/local/bin/backup-filagent-dr.sh`

```bash
#!/bin/bash
# Backup des Decision Records

SOURCE="/var/log/filagent/decisions"
DEST="/var/backup/filagent/decisions"
REMOTE="s3://your-bucket/filagent/decisions"  # Optionnel: S3, NAS, etc.

# Local backup
rsync -av --delete "$SOURCE/" "$DEST/"

# Remote backup (optionnel)
# aws s3 sync "$SOURCE" "$REMOTE" --storage-class GLACIER

# Vérifier intégrité (signatures EdDSA)
python3 /opt/filagent/scripts/verify_dr_signatures.py "$DEST"

echo "Backup DR completed: $(date)"
```

**Cron**: `/etc/cron.d/filagent-backup`
```
# Backup quotidien à 2h du matin
0 2 * * * filagent /usr/local/bin/backup-filagent-dr.sh >> /var/log/filagent/backup.log 2>&1
```

---

## Sécurité

### 1. Authentication Gradio

**Option 1: Authentication basique** (simple, mais limitée)

```python
# Dans gradio_app_production.py
demo.launch(
    auth=("admin", "P@ssw0rd!2025"),
    auth_message="Connexion requise - FilAgent Document Analyzer"
)
```

**Option 2: Authentication avec liste d'utilisateurs**

```python
def authenticate(username, password):
    valid_users = {
        "admin": "hashed_password_1",
        "analyst": "hashed_password_2"
    }
    # Utiliser bcrypt pour hash
    import bcrypt
    if username in valid_users:
        return bcrypt.checkpw(password.encode(), valid_users[username].encode())
    return False

demo.launch(auth=authenticate)
```

**Option 3: OAuth/SSO** (entreprise)

Intégrer avec:
- Azure AD
- Google Workspace
- Okta
- Keycloak

Voir documentation Gradio: https://www.gradio.app/guides/authentication

---

### 2. Reverse Proxy (Nginx)

**Fichier**: `/etc/nginx/sites-available/filagent`

```nginx
upstream filagent_gradio {
    server 127.0.0.1:7860;
}

server {
    listen 80;
    server_name filagent.your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name filagent.your-domain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/filagent.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/filagent.your-domain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/filagent-access.log;
    error_log /var/log/nginx/filagent-error.log;

    # Max upload size (50 MB + overhead)
    client_max_body_size 60M;

    location / {
        proxy_pass http://filagent_gradio;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**Activer**:
```bash
sudo ln -s /etc/nginx/sites-available/filagent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### 3. Firewall (UFW)

```bash
# Autoriser uniquement ports nécessaires
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP (redirect)
sudo ufw allow 443/tcp  # HTTPS

# Bloquer accès direct à Gradio (passer par Nginx)
sudo ufw deny 7860/tcp

# Activer
sudo ufw enable
```

---

### 4. SSL/TLS avec Let's Encrypt

```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir certificat
sudo certbot --nginx -d filagent.your-domain.com

# Auto-renouvellement (cron)
sudo certbot renew --dry-run
```

---

### 5. Hardening

**Permissions des fichiers**:
```bash
# Configuration
chmod 600 .env
chmod 640 config/agent.yaml

# Logs
chmod 750 /var/log/filagent
chmod 640 /var/log/filagent/*.log
chmod 640 /var/log/filagent/decisions/*.json

# Code
chmod 750 gradio_app_production.py
chmod 640 tools/*.py
```

**SELinux/AppArmor** (si disponible):
```bash
# AppArmor profile pour FilAgent
sudo aa-enforce /etc/apparmor.d/usr.bin.python3
```

---

## Troubleshooting

### Problème: Port 7860 déjà utilisé

**Symptôme**:
```
OSError: [Errno 48] Address already in use
```

**Solution**:
```bash
# Trouver le processus
lsof -i :7860

# Tuer le processus
kill -9 <PID>

# Ou changer le port dans gradio_app_production.py
```

---

### Problème: Import Error (dépendances manquantes)

**Symptôme**:
```
ModuleNotFoundError: No module named 'PyPDF2'
```

**Solution**:
```bash
# Réinstaller dépendances
pdm install
# ou
pip install -r requirements.txt

# Vérifier
python3 -c "import PyPDF2; import openpyxl; import docx; print('OK')"
```

---

### Problème: Tests échouent

**Symptôme**:
```
tests/test_document_analyzer_error_handling.py::test_validate_valid_excel FAILED
```

**Solution**:
```bash
# Recréer les fixtures
cd tests/fixtures
python create_test_fixtures.py

# Vérifier fixtures créées
ls -lh tests/fixtures/
```

---

### Problème: Espace disque insuffisant

**Symptôme**:
```
❌ Espace disque insuffisant
```

**Solution**:
```bash
# Vérifier espace
df -h /var/log/filagent

# Nettoyer vieux logs (>30 jours)
find /var/log/filagent/events -name "*.jsonl" -mtime +30 -delete

# Compresser Decision Records anciens (PAS SUPPRIMER!)
find /var/log/filagent/decisions -name "*.json" -mtime +90 -exec gzip {} \;
```

---

### Problème: Timeout sur gros fichiers

**Symptôme**:
```
❌ Temps de traitement dépassé (>30s)
```

**Solution**:
```python
# Augmenter timeout dans config/agent.yaml
document_analyzer:
  processing_timeout_seconds: 60  # Au lieu de 30

# Ou dans gradio_app_production.py
PROCESSING_TIMEOUT_SECONDS = 60
```

---

## Rollback

### Procédure de rollback

**1. Arrêter le service**:
```bash
sudo systemctl stop filagent-gradio
# ou
docker-compose down
```

**2. Restaurer version précédente**:
```bash
# Git
git checkout v2.2.0
pdm install

# Docker
docker pull filagent-gradio:v2.2.0
docker-compose up -d
```

**3. Restaurer configuration**:
```bash
# Si sauvegardé
cp /var/backup/filagent/config/agent.yaml.bak config/agent.yaml
```

**4. Vérifier**:
```bash
curl http://localhost:7860/
# Devrait répondre
```

**5. Redémarrer**:
```bash
sudo systemctl start filagent-gradio
```

---

### Backup avant mise à jour

**Script**: `/usr/local/bin/backup-before-update.sh`

```bash
#!/bin/bash
BACKUP_DIR="/var/backup/filagent/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup code
cp -r /opt/filagent "$BACKUP_DIR/code"

# Backup config
cp -r /opt/filagent/config "$BACKUP_DIR/config"

# Backup .env
cp /opt/filagent/.env "$BACKUP_DIR/env"

# Backup Decision Records (IMPORTANT)
cp -r /var/log/filagent/decisions "$BACKUP_DIR/decisions"

echo "Backup completed: $BACKUP_DIR"
```

**Avant chaque mise à jour**:
```bash
sudo /usr/local/bin/backup-before-update.sh
```

---

## Checklist de déploiement

**Avant déploiement**:
- [ ] Tests unitaires passent (21/21)
- [ ] Tests de conformité passent (15/15)
- [ ] Configuration validée (`config/agent.yaml`)
- [ ] Variables d'environnement définies (`.env`)
- [ ] Certificats SSL installés (production)
- [ ] Firewall configuré
- [ ] Backup configuré (Decision Records)
- [ ] Monitoring en place
- [ ] Documentation à jour

**Après déploiement**:
- [ ] Service démarré et stable
- [ ] Health checks OK
- [ ] Tests end-to-end fonctionnent
- [ ] Logs correctement générés
- [ ] Métriques collectées
- [ ] Backup fonctionne
- [ ] Alertes configurées
- [ ] Équipe formée

---

**Version du guide**: 1.0.0
**Dernière mise à jour**: 2025-11-18
**Compatible avec**: FilAgent v2.3.0+
