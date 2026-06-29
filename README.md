# Ynov-k3s — Pipeline DevSecOps

Projet de mise en place d'une pipeline DevSecOps complète pour une application de restauration microservices, déployée sur un cluster k3s avec durcissement CIS, supervision et analyses de sécurité automatisées.

---

## Objectif

Automatiser l'intégralité du cycle de vie d'une application — du commit au déploiement — en intégrant la sécurité à chaque étape :

- Analyse statique du code et des images (SAST, CVE)
- Durcissement CIS Level 1 des machines cibles
- Mesure de conformité avant/après durcissement (OpenSCAP)
- Signature des images de conteneurs (Cosign keyless)
- Analyse dynamique de l'application déployée (DAST)
- Supervision en temps réel via Grafana

---

## Infrastructure

| Machine | IP | Rôle |
|---|---|---|
| VM1 | `178.170.25.222` | Nœud k3s (master), contrôleur Ansible |
| VM2 | `178.170.25.222` | Cible de durcissement CIS et scans OpenSCAP |
| VM3 | `178.170.25.242` | Cible de durcissement CIS et scans OpenSCAP |
| Harbor | `frhb102257flex.ikexpress.com` | Registry privé pour les images signées |

---

## Application

Application de restauration découpée en 5 microservices Python (Flask) :

- **customer** — gestion des clients
- **waiter** — prise de commandes
- **kitchen** — gestion de la cuisine
- **payment** — paiements
- **reservation** — réservations

Chaque service expose des métriques Prometheus via `prometheus-flask-exporter`.

---

## Pipeline GitHub Actions

La pipeline se déclenche à chaque push sur `main` et s'exécute en plusieurs étapes séquentielles et parallèles.

```
[ansible-lint] [bandit] [semgrep] [trivy]
        └──────────────┬──────────────┘
                [build-and-sign]
                       │
          [openscap-before VM2] [openscap-before VM3]
                       └──────────┬──────────┘
                              [deploy]
                    ┌──────────────┴────────────┐
          [deploy-monitoring]           [deploy-apps]
                    └──────────────┬────────────┘
          [openscap-after VM2] [openscap-after VM3]
                                  [zap]
```

### Étapes détaillées

#### Qualité & Sécurité statique
| Job | Outil | Rôle |
|---|---|---|
| `ansible-lint` | ansible-lint | Lint des playbooks et rôles Ansible |
| `bandit` | Bandit | SAST Python — détection de vulnérabilités dans le code |
| `semgrep` | Semgrep | SAST multi-langage (Python, Dockerfile, Ansible) |
| `trivy` | Trivy | Scan CVE des images Docker (HIGH/CRITICAL, unfixed exclus) |

#### Build & Signature
Les 5 images sont buildées, poussées sur Harbor puis signées avec **Cosign keyless** (signature OIDC sans clé privée stockée).

#### Scans CIS OpenSCAP
Exécutés en parallèle sur VM2 et VM3, avant et après le durcissement :
- Scan avec le profil `cis_level1_server` du SCAP Security Guide
- Extraction du score et push vers le Pushgateway Prometheus
- Affichage dans Grafana pour comparer l'impact du durcissement

#### Déploiement
- **`deploy`** : applique le durcissement CIS (VM1 + VM3) et installe k3s (VM1 uniquement) via Ansible
- **`deploy-monitoring`** : déploie la stack de supervision sur k3s
- **`deploy-apps`** : applique les manifests Kubernetes de l'application

#### DAST
**OWASP ZAP** effectue un scan baseline sur `http://178.170.25.223:30001` après déploiement.

---

## Durcissement CIS (rôle `cis_ubuntu`)

Le rôle Ansible applique le benchmark CIS Ubuntu 24.04 Level 1 :

- Blacklist des modules noyau inutiles (cramfs, hfs, udf…)
- Montage `/tmp` avec `nodev,nosuid,noexec`
- Désactivation IPv6
- Durcissement SSH (pas de root, max 4 tentatives, keepalive)
- Bannière SSH légale
- Auditd configuré
- Sysctl réseau durci (`syncookies`, anti-ICMP redirect, `ip_forward` activé pour k3s)
- Désactivation des services inutiles (cups, avahi, vsftpd…)
- Pare-feu UFW (deny entrant par défaut, ports 22/6443/30001/30091 ouverts)
- Politique de mots de passe
- Permissions fichiers critiques (`/etc/passwd`, `/etc/shadow`, `/etc/group`)
- Désactivation des core dumps
- AppArmor activé
- Logrotate configuré

---

## Stack de supervision

Déployée dans le namespace `restaurant` sur k3s :

| Composant | Port | Rôle |
|---|---|---|
| Prometheus | interne | Collecte des métriques |
| Pushgateway | `30091` | Réception des scores OpenSCAP |
| Grafana | `30001` | Dashboard de visualisation |
| Node Exporter | `9100` | Métriques système VM1 |
| Node Exporter (VM3) | `9100` | Métriques système VM3 |
| kube-state-metrics | interne | Métriques Kubernetes |

### Dashboard Grafana

Le dashboard `Ynov-k3s DevSecOps` est provisionné automatiquement et affiche :

- **Scores CIS** : avant/après durcissement pour VM2 et VM3, delta d'amélioration, courbe d'évolution
- **Ressources VM2** : CPU, mémoire, disque, uptime
- **Ressources VM3** : CPU, mémoire, disque, uptime
- **Santé cluster k3s** : pods running/pending/failed, deployments ready, tableau des pods par namespace

---

## Structure du dépôt

```
Ynov-k3s/
├── .github/workflows/pipeline.yml   # Pipeline DevSecOps
├── app/                             # Code source des microservices
│   ├── customer/
│   ├── waiter/
│   ├── kitchen/
│   ├── payment/
│   ├── reservation/
│   └── shared/
├── k8s/                             # Manifests Kubernetes
│   ├── monitoring/                  # Stack Prometheus/Grafana
│   └── *.yaml                       # Déploiements applicatifs
├── playbooks/
│   ├── harden.yml                   # Durcissement CIS (VM1 + VM3)
│   ├── k3s.yml                      # Installation k3s (VM1)
│   └── monitoring.yml               # Déploiement monitoring
├── roles/
│   ├── cis_ubuntu/                  # Rôle durcissement CIS L1
│   └── k3s_install/                 # Rôle installation k3s
└── inventory/
    └── hosts.yml                    # Inventaire (VM1, VM3)
```
