# Revaw — UI de Production Batteries

Interface de gestion de production des batteries reconditionnées.
Tourne sur PC (Windows) connecté à une scanette et une imprimante d'étiquettes Zebra.

---

## Sommaire

1. [Vue d'ensemble](#vue-densemble)
2. [Lancer l'application](#lancer-lapplication)
3. [Structure du projet](#structure-du-projet)
4. [Architecture technique](#architecture-technique)
5. [Commandes disponibles](#commandes-disponibles)
6. [Cycle de vie d'une batterie](#cycle-de-vie-dune-batterie)
7. [Base de données SQLite](#base-de-données-sqlite)
8. [Fichiers CSV (legacy)](#fichiers-csv-legacy)
9. [Configuration](#configuration)
10. [Dépendances](#dépendances)

---

## Vue d'ensemble

```
[Scanette / Clavier]
        |
        v
  [UI Python - ui.py]          Interface CustomTkinter plein écran
        |
        |-- [ScanManager]       Machine à états : interprète les commandes
        |-- [InfoPanel]         Statistiques temps réel (lectures CSV/SQLite)
        |-- [MQTT Client]       Communique avec le service d'impression
        |
        v
  [printer.py]                  Service d'impression (process séparé)
        |
        v
  [Imprimante Zebra]            Impression ZPL via socket TCP
        |
  [CSV / SQLite]                Persistance locale des données
        |
        v (sync quotidien / direct)
  [MongoDB Atlas]               Source de vérité ERP
```

---

## Lancer l'application

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer l'UI
python ui.py

# Lancer le service d'impression (dans un terminal séparé)
python printer.py
```

> L'UI vérifie au démarrage si `printer.py` tourne via `psutil`.
> MQTT doit être disponible sur `localhost:1883`.

---

## Structure du projet

```
light_ui/
│
├── ui.py                        Point d'entrée principal de l'UI
├── printer.py                   Service d'impression (process indépendant)
├── requirements.txt             Dépendances Python
├── revaw.db                     Base de données SQLite locale (générée au démarrage)
│
├── printed_serials.csv          Stockage legacy batteries (en cours de migration)
├── sav_batteries.csv            Stockage legacy SAV (en cours de migration)
│
├── src/
│   ├── __init__.py
│   │
│   ├── db/                      Module base de données SQLite
│   │   ├── __init__.py
│   │   └── sqlite_manager.py    Toutes les fonctions de lecture/écriture SQLite
│   │
│   ├── labels/                  Gestion étiquettes et CSV
│   │   ├── __init__.py
│   │   ├── csv_serial_manager.py  Gestion CSV + génération serials (legacy)
│   │   ├── label_templates.py   Templates ZPL pour l'imprimante Zebra
│   │   └── printer_config.py    Configuration imprimante, MQTT, modèles batteries
│   │
│   └── ui/                      Composants de l'interface
│       ├── system_utils.py      Logging, constantes MQTT, utilitaires système
│       ├── scan_manager.py      Machine à états — traitement des commandes scannées
│       ├── info_panel.py        Panneau d'informations et statistiques (1/4 droite)
│       └── email/               Module envoi email
│           ├── __init__.py
│           ├── email_config.py  Chargement config depuis email_config.json
│           ├── email_config.json Configuration SMTP (gitignored)
│           └── email_templates.py Templates des emails d'expédition
│
├── scripts/
│   └── migrate_csv_to_sqlite.py Migration one-shot CSV -> SQLite
│
├── docs/
│   ├── PLAN_MIGRATION_PC_SQLITE_MONGO.md   Plan de migration en cours
│   ├── RAPPORT_WORKFLOW_PRODUCTION.md      Documentation workflow complet
│   ├── RAPPORT_WORKFLOW_PRODUCTION_SIMPLIFIED.md  Version simplifiée
│   ├── RAPPORT_WORKFLOW_SPARE_PARTS.md     Workflow pièces détachées ERP
│   └── final_sync.py                       Script de sync CSV -> MongoDB (legacy Pi)
│
└── src/logs/
    └── banc_test.log            Fichier de log rotatif (10MB x 5)
```

---

## Architecture technique

### UI (`ui.py` — `SimpleApp`)

Interface CustomTkinter plein écran, mode sombre.

**Layout :**
```
┌────────────────────────────┬──────────────┐
│                            │              │
│   Zone messages (3/4)      │  InfoPanel   │
│   Historique des actions   │   (1/4)      │
│                            │              │
├────────────────────────────┴──────────────┤
│  label_response1 (état courant)           │
│  label_response2 (instruction)            │
│  [entry_prompt — saisie / scan]           │
├───────────────────────────────────────────┤
│  Statut MQTT | Statut Imprimante          │
└───────────────────────────────────────────┘
```

**Threads au démarrage :**
| Thread | Rôle |
|--------|------|
| Thread principal | UI Tkinter |
| `_mqtt_thread` (daemon) | Connexion MQTT avec reconnexion automatique |
| `_update_loop` InfoPanel (daemon) | Refresh stats toutes les 30s |

---

### ScanManager (`src/ui/scan_manager.py`)

Machine à états qui interprète chaque scan ou saisie.

**États :**
| Constante | Valeur | Description |
|-----------|--------|-------------|
| `STATE_IDLE` | 0 | En attente |
| `STATE_AWAIT_FINISH_SERIAL` | 1 | Attend scan QR V1 pour finish |
| `STATE_AWAIT_FINISH_CONFIRM` | 2 | Attend confirmation finish |
| `STATE_AWAIT_EXPEDITION_SERIAL` | 3 | Accumule les batteries à expédier |
| `STATE_AWAIT_EXPEDITION_CONFIRM` | 4 | Attend confirmation expédition |
| `STATE_AWAIT_SAV_SERIAL` | 5 | Attend scan du serial SAV |
| `STATE_AWAIT_SAV_CONFIRM` | 6 | Attend confirmation SAV |
| `STATE_AWAIT_QR_TEXT` | 7 | Attend libellé QR personnalisé |
| `STATE_AWAIT_QR_CONTENT` | 8 | Attend contenu QR personnalisé |
| `STATE_AWAIT_QR_CONFIRM` | 9 | Attend confirmation QR |
| `STATE_AWAIT_REPRINT_SERIAL` | 10 | Attend serial pour réimpression |
| `STATE_AWAIT_REPRINT_CONFIRM` | 11 | Attend confirmation réimpression |

Timeout automatique : **30 secondes** d'inactivité → retour `STATE_IDLE`.

---

### Service d'impression (`printer.py`)

Process indépendant qui écoute les topics MQTT et envoie les commandes ZPL à l'imprimante via socket TCP.

**Topics MQTT écoutés :**
| Topic | Action |
|-------|--------|
| `printer/create_label` | Impression étiquette V1 (création) |
| `printer/validate_battery` | Impression étiquettes Main + Shipping (finish) |
| `printer/create_batch_labels` | Impression multiple (finish avec downgrade) |
| `printer/request_full_reprint` | Réimpression complète |
| `printer/sav_entry` | Notification entrée SAV |
| `printer/sav_departure` | Notification sortie SAV |
| `printer/create_qr` | QR code personnalisé |
| `printer/update_shipping_timestamp` | Mise à jour timestamp expédition |

**Topic publié :**
| Topic | Valeur |
|-------|--------|
| `printer/status` | `on` si imprimante joignable, autre sinon |

---

### MQTT

- Broker : `localhost:1883`
- Reconnexion automatique toutes les 10s en cas d'échec
- L'UI s'abonne à `printer/status` pour afficher l'état de l'imprimante

---

## Commandes disponibles

Saisies au clavier ou scannées via la scanette. Insensibles à la casse.

### `create <A|B|C|D|E>`

Crée une nouvelle batterie du type indiqué.

**Étapes :** scan `create B` → confirmation immédiate

**Actions :**
- Génère un numéro séquentiel (4 chiffres, basé sur le dernier serial du CSV)
- Crée le serial temporaire : `RW-48vXXX<NNNN>` (capacité inconnue avant test)
- Génère un `CodeAleatoireQR` aléatoire (6 caractères alphanumériques)
- Écrit dans `printed_serials.csv`
- Publie sur `printer/create_label` → impression étiquette **V1** (interne batterie)

**Types de batteries :**
| Type | Capacités possibles | Description |
|------|---------------------|-------------|
| A | 13 kWh (271 Ah) ou 12 kWh (250 Ah) | Source type A |
| B | 13 kWh (271 Ah) ou 12 kWh (250 Ah) | Source type B |
| C | 13 kWh (271 Ah) ou 12 kWh (250 Ah) | Source type C |
| D | 8.6 kWh (175 Ah) uniquement | Source type D |
| E | 8.6 kWh (175 Ah) uniquement | Source type E |

---

### `finish <13|12|8.6>`

Valide une batterie après test physique.

**Étapes :** scan `finish 13` → scan QR V1 (interne batterie) → re-scan `finish 13`

**Actions :**
- Identifie la batterie via le QR code V1 scanné
- Remplace `XXX` par la capacité réelle dans le serial (`271`, `250`, ou `175`)
- Met à jour `TimestampTestDone` dans le CSV
- Publie sur `printer/validate_battery` → impression étiquettes **Main** + **Shipping**
- Si downgrade détecté (capacité différente de prévue) : impression de 3 étiquettes via `printer/create_batch_labels`

**Validation type/capacité :**
- Types A, B, C → acceptent 13 kWh ou 12 kWh
- Types D, E → acceptent uniquement 8.6 kWh

---

### `expedition`

Expédie une ou plusieurs batteries.

**Étapes :** scan `expedition` → scan des serials (autant que voulu) → re-scan `expedition`

**Actions par batterie :**
- Vérifie que la batterie est testée (pas de `XXX` dans le serial)
- Détecte si batterie en SAV → traitement sortie SAV automatique
- Écrit `TimestampExpedition` dans le CSV
- Si SAV : met `sav_status = False` + `TimestampDepart` dans `sav_batteries.csv`
- Envoie un email récapitulatif à la liste des destinataires configurés

---

### `sav`

Enregistre l'entrée d'une batterie en SAV (retour client).

**Étapes :** scan `sav` → scan du serial de la batterie

**Actions :**
- Vérifie que le serial existe dans `printed_serials.csv`
- Crée une entrée dans `sav_batteries.csv` (`TimestampArrivee`, serial, `TimestampDepart` vide)
- Met `sav_status = True` dans `printed_serials.csv`

---

### `reprint`

Réimprime les étiquettes d'une batterie existante.

**Étapes :** scan `reprint` → scan du serial (format long `RW-48v...` ou court `B0341`)

**Actions :**
- Recherche la batterie dans le CSV (par serial exact ou par type + 4 derniers chiffres)
- Si batterie testée : réimprime Main + Shipping
- Si batterie non testée : réimprime V1 uniquement

---

### `new qr`

Génère et imprime un QR code personnalisé (non lié à une batterie).

**Étapes :** scan `new qr` → saisie du libellé → saisie du contenu → confirmation

---

## Cycle de vie d'une batterie

```
create <type>
    |
    v
[RW-48vXXX0341]  -- serial temporaire, étiquette V1 imprimée
    |
    | (test physique hors système)
    |
    v
finish <capacité>  -- scan QR V1
    |
    v
[RW-48v2710341]  -- serial définitif, étiquettes Main + Shipping
    |
    |---- expedition  --> [Expédiée] -- email envoyé
    |
    |---- sav         --> [En SAV]
              |
              v
         (réparation ERP)
              |
              v
         expedition   --> [Ré-expédiée] -- sortie SAV automatique
```

---

## Base de données SQLite

Fichier : `revaw.db` (généré automatiquement au démarrage de `ui.py`)

### Table `batteries`

Remplace `printed_serials.csv`.

| Colonne | Type | Description |
|---------|------|-------------|
| `numero_serie` | TEXT PK | Serial de la batterie (`RW-48v...`) |
| `code_aleatoire_qr` | TEXT | Code QR unique (6 caractères) |
| `timestamp_impression` | TEXT | Date/heure de création (ISO 8601) |
| `timestamp_test_done` | TEXT | Date/heure de validation (ISO 8601) |
| `timestamp_expedition` | TEXT | Date/heure d'expédition (ISO 8601) |
| `type` | TEXT | Type batterie source (A, B, C, D, E) |
| `version` | TEXT | Version logiciel au moment de la création |
| `sav_status` | INTEGER | 0 = non / 1 = en SAV |
| `score` | REAL | Score qualité (optionnel, script externe) |

### Table `sav_entries`

Remplace `sav_batteries.csv`.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INTEGER PK auto | Identifiant |
| `numero_serie` | TEXT | Batterie concernée |
| `timestamp_arrivee` | TEXT | Entrée en SAV (ISO 8601) |
| `timestamp_depart` | TEXT | Sortie SAV — NULL si encore en SAV |

### Table `sync_queue`

File d'attente pour la synchronisation MongoDB (worker à venir).

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INTEGER PK auto | Identifiant |
| `operation` | TEXT | `create` / `finish` / `expedition` / `sav_in` / `sav_out` |
| `payload` | TEXT | JSON de l'opération |
| `status` | TEXT | `pending` / `sent` |
| `attempts` | INTEGER | Nombre de tentatives d'envoi |
| `created_at` | TEXT | Date création (ISO 8601) |
| `last_attempt` | TEXT | Date dernière tentative |
| `error` | TEXT | Message d'erreur de la dernière tentative |

> **Edition manuelle** : utiliser [DB Browser for SQLite](https://sqlitebrowser.org/) (gratuit).
> Ouvrir `revaw.db`, double-cliquer sur une valeur, modifier, sauvegarder.
> Préférer l'édition UI fermée.

---

## Fichiers CSV (legacy)

Toujours utilisés par l'UI actuelle. Migration vers SQLite en cours.

### `printed_serials.csv`

| Colonne | Écrit par | Description |
|---------|-----------|-------------|
| `TimestampImpression` | `create` | Date création |
| `NumeroSerie` | `create` / `finish` | Serial (XXX puis réel) |
| `CodeAleatoireQR` | `create` | Code QR unique |
| `TimestampTestDone` | `finish` | Date validation |
| `TimestampExpedition` | `expedition` | Date expédition |
| `type` | `create` | Type batterie (A-E) |
| `version` | `create` | Version logiciel |
| `sav_status` | `sav` / `expedition` | "True" ou "False" |

### `sav_batteries.csv`

| Colonne | Écrit par | Description |
|---------|-----------|-------------|
| `TimestampArrivee` | `sav` | Entrée en SAV |
| `NumeroSerie` | `sav` | Batterie concernée |
| `TimestampDepart` | `expedition` | Sortie SAV (vide si en cours) |

---

## Configuration

### Imprimante (`src/labels/printer_config.py`)

```python
PRINTER_IP   = "192.168.1.123"
PRINTER_PORT = 9100
SOFTWARE_VERSION = "1.1.5.1"
```

### MQTT (`src/ui/system_utils.py`)

```python
MQTT_BROKER = "localhost"
MQTT_PORT   = 1883
```

### Email (`src/ui/email/email_config.json`)

Fichier JSON à créer manuellement (non versionné) :

```json
{
    "GMAIL_USER": "expeditions@example.com",
    "GMAIL_PASSWORD": "app_password_ici",
    "RECIPIENT_EMAILS": ["logistique@example.com"],
    "GMAIL_SMTP_SERVER": "smtp.gmail.com",
    "GMAIL_SMTP_PORT": 465
}
```

> Utiliser un mot de passe d'application Gmail (pas le mot de passe du compte).

---

## Dépendances

```
customtkinter==5.2.2   Interface graphique
darkdetect==0.8.0      Détection thème système
paho-mqtt==2.1.0       Client MQTT
pillow==11.2.1         Traitement d'images
psutil==7.0.0          Détection processus (printer.py)
```

SQLite est inclus nativement dans Python (pas de dépendance externe).

---

## Logs

Fichier : `src/logs/banc_test.log`
- Rotation automatique : 10 MB max, 5 fichiers conservés
- Niveaux : `DEEP_DEBUG`, `DEBUG`, `INFO`, `WARNING`, `ERROR`
- Niveau courant par défaut : `INFO`

---

*Dernière mise à jour : 2026-03-19*
