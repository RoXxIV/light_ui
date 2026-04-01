# scripts/migrate_csv_to_sqlite.py — Migration CSV → SQLite

## Rôle

Script one-shot pour migrer les données legacy des fichiers CSV vers la base SQLite. À exécuter une seule fois lors du passage en production de la branche `sqlite`.

---

## Utilisation

```bash
python scripts/migrate_csv_to_sqlite.py
```

---

## Fonctions

### `migrate_batteries()`

Migre `printed_serials.csv` → table `batteries` de SQLite.

- Parcourt toutes les lignes du CSV
- Utilise `INSERT OR IGNORE` pour rester idempotent (relançable sans duplication)
- Convertit les champs vides en `NULL`
- Mappe les colonnes CSV vers le schéma SQLite

---

### `migrate_sav()`

Migre `sav_batteries.csv` → table `sav_entries` de SQLite.

- Même logique idempotente (`INSERT OR IGNORE`)
- Convertit les statuts booléens CSV (`"True"` / `"False"`) vers `1` / `0` SQLite

---

### `print_summary()`

Affiche le nombre de lignes présentes dans chaque table après migration :

```
batteries  : 127 lignes
sav_entries: 14 lignes
sync_queue : 0 lignes
```

---

### `main()`

Orchestre la migration avec gestion d'erreurs :
1. Initialise la base (`init_db()`)
2. Lance `migrate_batteries()`
3. Lance `migrate_sav()`
4. Affiche le résumé

---

## Fonctions utilitaires internes

| Fonction | Description |
|---|---|
| `_parse_sav_status(value)` | Convertit `"True"` / `"False"` en `1` / `0` |
| `_empty_to_none(value)` | Convertit les chaînes vides en `None` (→ `NULL` SQLite) |

---

## Fichiers source attendus

| Fichier | Description |
|---|---|
| `printed_serials.csv` | Historique des numéros de série imprimés |
| `sav_batteries.csv` | Entrées/sorties SAV |

Les deux fichiers doivent être à la racine du projet (`light_ui/`).

---

## Idempotence

Le script peut être relancé plusieurs fois sans effet : `INSERT OR IGNORE` garantit qu'aucune ligne existante n'est dupliquée ni écrasée.

---

## Dépendances

| Module | Usage |
|---|---|
| `csv` | Lecture des fichiers CSV |
| `sqlite3` | Accès direct à la base |
| `os`, `sys` | Gestion des chemins et sortie |
| `src.db.sqlite_manager` | `SQLiteManager` pour l'init et les insertions |
