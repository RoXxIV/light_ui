# src/ui/email/email_templates.py — Templates d'emails

## Rôle

Génère le contenu des emails de notification d'expédition, en formats texte brut et HTML. Groupe les batteries par modèle et statut SAV pour une présentation claire.

---

## Classe `EmailTemplates`

Classe statique — toutes les méthodes sont des `@staticmethod` ou `@classmethod`.

---

## Méthodes publiques

### `generate_expedition_email_content(batteries, date)`

Génère le contenu complet de l'email d'expédition.

**Retourne :** `dict` avec les clés `text` et `html`

**Paramètres :**

| Paramètre | Type | Description |
|---|---|---|
| `batteries` | list[dict] | Liste des batteries expédiées |
| `date` | str | Date d'expédition formatée |

---

### `generate_expedition_subject(count, date)`

Génère l'objet de l'email.

**Exemple de sortie :**
```
[REVAW] Expédition du 01/04/2026 — 12 batteries
```

---

## Méthodes privées

### `_generate_expedition_text_content(batteries, date)`

Corps de l'email en texte brut.

**Contenu :**
- En-tête avec date et nombre total
- Groupement par capacité (13 kWh, 12 kWh, 8.4 kWh)
- Indication SAV pour les batteries en garantie
- Zone de signature manuelle
- Branding REVAW

---

### `_generate_expedition_html_content(batteries, date)`

Corps de l'email en HTML stylisé.

**Contenu :**
- Même structure que la version texte
- Mise en forme CSS inline (compatible clients email)
- Tableau de liste des batteries avec coloration SAV
- Zone de signature

---

## Structure des données `batteries`

Chaque entrée de la liste est un `dict` contenant :

| Clé | Type | Description |
|---|---|---|
| `serial` | str | Numéro de série définitif |
| `capacity_kwh` | float | Capacité en kWh |
| `in_sav` | bool | Si la batterie est en garantie |

---

## Dépendances

| Module | Usage |
|---|---|
| `datetime` | Formatage des dates |
| `typing` | Annotations de types |
| `src.labels.printer_config` | `PrinterConfig.BATTERY_MODELS` pour les libellés |
