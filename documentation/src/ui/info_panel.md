# src/ui/info_panel.py — Panel d'informations et statistiques

## Rôle

Gère l'affichage des statistiques de production en temps réel et les boutons d'action de l'interface. Interroge SQLite toutes les 30 secondes en arrière-plan.

---

## Classe `InfoPanel`

### Initialisation

| Méthode | Description |
|---|---|
| `__init__(app)` | Reçoit la référence à `SimpleApp`, crée les widgets |
| `create_info_widgets()` | Génère les labels de stats et les boutons CTk |

---

## Mise à jour des données

| Méthode | Description |
|---|---|
| `start_updates()` | Démarre le thread de mise à jour en arrière-plan |
| `stop_updates()` | Arrête proprement le thread |
| `_update_loop()` | Boucle toutes les 30 secondes |
| `_collect_data()` | Requête SQLite pour les statistiques |
| `_update_display()` | Met à jour les widgets avec les nouvelles données |
| `manual_refresh()` | Force une mise à jour immédiate |
| `_safe_manual_refresh()` | Version thread-safe du refresh manuel |

### Statistiques affichées

- Dernier numéro de série imprimé
- Batteries produites aujourd'hui
- Batteries expédiées aujourd'hui
- Batteries expédiées ce mois-ci

---

## Boutons d'action

Chaque bouton correspond à une étape du workflow de production :

| Bouton | Handler | Description |
|---|---|---|
| CREATE | `_on_create_click()` | Ouvre modal sélection type matière (A–E) |
| FINISH | `_on_finish_click()` | Ouvre modal sélection capacité (13/12/8.4 kWh) |
| CONFIRM FINISH | `_on_finish_confirm_click()` | Confirme la finalisation |
| EXPEDITION | `_on_expedition_click()` | Active/désactive le mode expédition |
| SAV | `_on_sav_click()` | Lance le processus SAV |
| CANCEL | `_on_cancel_click()` | Annule l'opération en cours |

---

## Modales

Les modales sont des fenêtres `CTkToplevel` bloquantes permettant à l'utilisateur de sélectionner :

- **Type de matière** : A, B, C, D ou E (lors du CREATE)
- **Capacité** : 13 kWh, 12 kWh ou 8.4 kWh (lors du FINISH)

Le choix est transmis au `ScanManager` via la référence à `app`.

---

## Gestion des états des boutons

| Méthode | Description |
|---|---|
| `reset_action_buttons()` | Remet tous les boutons en état initial |
| `show_finish_confirm_button()` | Affiche le bouton de confirmation de finish |

---

## Dépendances

| Module | Usage |
|---|---|
| `customtkinter` | Widgets CTk (labels, boutons, modales) |
| `threading` | Thread de mise à jour en arrière-plan |
| `time` | Intervalle de 30s entre les updates |
| `src.db.sqlite_manager` | Lecture des statistiques |
| `src.ui.system_utils` | Logging |
