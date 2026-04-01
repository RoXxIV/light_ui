# src/db/sqlite_manager.py — Gestionnaire SQLite

## Rôle

Couche d'accès à la base de données SQLite locale. Gère l'intégralité du cycle de vie des batteries (création → finalisation → expédition), le suivi SAV, et une file de synchronisation MongoDB.

Toutes les opérations sensibles sont protégées par un `threading.Lock`.

---

## Tables SQLite

### `batteries`

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Identifiant auto-incrémenté |
| `temp_serial` | TEXT | Numéro temporaire (QR interne) |
| `final_serial` | TEXT | Numéro définitif (`RW-48vXXX0001`) |
| `capacity_kwh` | REAL | Capacité en kWh |
| `material_type` | TEXT | Type de matière (A–E) |
| `created_at` | TEXT | Horodatage de création |
| `finished_at` | TEXT | Horodatage de finalisation |
| `shipped_at` | TEXT | Horodatage d'expédition |
| `in_sav` | INTEGER | 0/1 — en garantie |

### `sav_entries`

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Identifiant |
| `serial` | TEXT | Numéro de série de la batterie |
| `arrival_date` | TEXT | Date d'entrée SAV |
| `departure_date` | TEXT | Date de sortie SAV (NULL si ouverte) |

### `sync_queue`

File d'opérations en attente de synchronisation vers MongoDB.

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Identifiant |
| `operation` | TEXT | Type d'opération (JSON) |
| `payload` | TEXT | Données (JSON) |
| `status` | TEXT | `pending` / `sent` / `error` |
| `attempts` | INTEGER | Nombre de tentatives |
| `last_error` | TEXT | Dernier message d'erreur |

---

## Méthodes

### Initialisation

| Méthode | Description |
|---|---|
| `init_db()` | Crée les tables si elles n'existent pas |
| `generate_random_code(length=6)` | Génère un code alphanumérique aléatoire |
| `get_next_numeric_part()` | Retourne le prochain numéro de série à 4 chiffres (thread-safe) |

### Cycle de vie batterie

| Méthode | Description |
|---|---|
| `insert_battery(temp_serial, capacity, material)` | Insère une nouvelle batterie |
| `update_battery_finish(temp_serial, final_serial)` | Associe le numéro définitif et horodate la finalisation |
| `update_battery_expedition(serial)` | Enregistre la date d'expédition |
| `get_battery(serial)` | Récupère une batterie par son numéro |
| `battery_exists(serial)` | Vérifie l'existence d'un numéro de série |
| `get_battery_for_reprint(serial)` | Recherche une batterie pour réimpression |

### Statistiques

| Méthode | Description |
|---|---|
| `get_last_serial()` | Dernier numéro imprimé |
| `count_produced_today()` | Nombre de batteries créées aujourd'hui |
| `count_shipped_today()` | Nombre expédiées aujourd'hui |
| `count_shipped_this_month()` | Nombre expédiées ce mois-ci |

### SAV

| Méthode | Description |
|---|---|
| `insert_sav_entry(serial)` | Enregistre une entrée SAV |
| `close_sav_entry(serial, departure_date)` | Ferme une entrée SAV |
| `get_open_sav_entry(serial)` | Récupère une entrée SAV ouverte |
| `is_battery_in_sav(serial)` | Vérifie si une batterie est en garantie |
| `update_battery_sav_status(serial, status)` | Met à jour le flag `in_sav` |

### File de synchronisation MongoDB

| Méthode | Description |
|---|---|
| `enqueue(operation, payload)` | Ajoute une opération à la file |
| `get_pending_operations()` | Retourne les opérations `pending` |
| `mark_operation_sent(id)` | Marque une opération comme envoyée |
| `mark_operation_attempt(id, error)` | Enregistre une tentative échouée |

---

## Thread-safety

Toutes les écritures et lectures critiques passent par un `threading.Lock` instancié à la création du manager. Les opérations de comptage et de génération de numéro de série sont atomiques.

---

## Dépendances

| Module | Usage |
|---|---|
| `sqlite3` | Accès base de données |
| `threading` | Lock pour thread-safety |
| `json` | Sérialisation des payloads sync |
| `datetime` | Horodatages |
| `src.ui.system_utils` | Logging |
