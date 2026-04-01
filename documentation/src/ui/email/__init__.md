# src/ui/email/__init__.py — Initialisation du module email

## Rôle

Expose les classes et objets du module email.

---

## Exports

```python
from src.ui.email.email_templates import EmailTemplates
from src.ui.email.email_config import EmailConfig, email_config
```

Permet d'importer directement avec :

```python
from src.ui.email import EmailTemplates, EmailConfig, email_config
```

> `email_config` est une instance singleton de `EmailConfig` pré-chargée.
