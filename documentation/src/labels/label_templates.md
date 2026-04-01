# src/labels/label_templates.py — Templates ZPL

## Rôle

Génère les commandes ZPL (Zebra Programming Language) pour les 4 types d'étiquettes imprimées par le service.

---

## Classe `LabelTemplates`

Classe statique — toutes les méthodes sont des `@staticmethod`.

---

## Méthodes

### `get_main_label_zpl(serial, capacity_kwh, ah)`

Étiquette principale collée à l'extérieur de la batterie.

**Contenu :**
- Numéro de série (`RW-48vXXX0001`)
- QR code encodant le numéro de série
- Capacité en kWh et Ah
- Avertissements de sécurité (LiFePO4, en français)
- Logo / branding REVAW

**Paramètres :**

| Paramètre | Type | Description |
|---|---|---|
| `serial` | str | Numéro de série définitif |
| `capacity_kwh` | float | Capacité (13, 12 ou 8.4) |
| `ah` | int | Capacité en ampères-heures |

---

### `get_v1_label_zpl(serial, capacity_kwh, fabrication_date)`

Étiquette intérieure placée à l'intérieur du boîtier batterie.

**Contenu :**
- Numéro de série
- Version matérielle (V1)
- Date de fabrication

---

### `get_shipping_label_zpl(serial, capacity_kwh)`

Étiquette collée sur le carton d'expédition.

**Contenu :**
- Numéro de série
- Spécifications techniques
- Informations de transport

---

### `get_custom_qr_label_zpl(display_text, qr_content)`

Étiquette QR personnalisée avec texte d'affichage et contenu encodé distincts.

**Paramètres :**

| Paramètre | Type | Description |
|---|---|---|
| `display_text` | str | Texte visible sur l'étiquette |
| `qr_content` | str | Contenu encodé dans le QR code |

---

## Format ZPL

Les templates génèrent des chaînes ZPL brutes envoyées directement au port 9100 de l'imprimante. Ils utilisent les commandes standards :

- `^XA` / `^XZ` — délimiteurs de label
- `^FO` — position du champ
- `^FD` — données du champ
- `^BQ` — QR code
- `^CF` — police de caractères

---

## Dépendances

| Module | Usage |
|---|---|
| `src.labels.printer_config` | `PrinterConfig` pour les constantes de modèles |
