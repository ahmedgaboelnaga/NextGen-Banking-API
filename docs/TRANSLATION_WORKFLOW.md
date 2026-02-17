# Translation Workflow Guide

## TL;DR - What You Need to Know

**Translations work like linting/formatting (local development), NOT like migrations (Docker container).**

## Quick Reference

| Task | Command | When to Run |
|------|---------|-------------|
| Added new `_("text")` in code? | `make i18n-refresh` | After coding |
| Edit translations | Edit `.po` files | Manually |
| Test translations | `make i18n-compile` then `make up` | Before commit |
| Commit | `git add backend/app/locales/` | Include both `.po` and `.mo` |

## Detailed Workflow

### Scenario 1: You Added New API Error Messages

```python
# backend/app/api/routes/auth.py
from backend.app.core.i18n import _

@router.post("/login")
async def login(data: LoginSchema):
    if not valid:
        raise HTTPException(
            status_code=401,
            detail=_("Invalid username or password")  # ← NEW
        )
```

**Steps:**

```bash
# 1. Extract the new message
make i18n-extract
# Creates/updates: backend/app/locales/messages.pot

# 2. Update all language files
make i18n-update
# Updates: backend/app/locales/{ar,fr,es,en}/LC_MESSAGES/messages.po

# 3. Edit translation files
# File: backend/app/locales/ar/LC_MESSAGES/messages.po
msgid "Invalid username or password"
msgstr "اسم المستخدم أو كلمة المرور غير صحيحة"

# File: backend/app/locales/fr/LC_MESSAGES/messages.po
msgid "Invalid username or password"
msgstr "Nom d'utilisateur ou mot de passe invalide"

# 4. Compile translations
make i18n-compile
# Creates: backend/app/locales/{ar,fr,es,en}/LC_MESSAGES/messages.mo

# 5. Test in Docker
make up
curl -H "X-Language: ar" http://localhost:8000/api/v1/login

# 6. Commit (BOTH .po and .mo files)
git add backend/app/locales/
git commit -m "Add login error message translations"
git push
```

### Scenario 2: Translator Sent You Updated .po Files

```bash
# Translator emails you: messages_ar_updated.po

# 1. Replace the file
cp messages_ar_updated.po backend/app/locales/ar/LC_MESSAGES/messages.po

# 2. Compile
make i18n-compile

# 3. Test
make up
curl -H "X-Language: ar" http://localhost:8000/api/v1/home/

# 4. Commit
git add backend/app/locales/ar/
git commit -m "Update Arabic translations"
git push
```

### Scenario 3: Quick One-Command Update

```bash
# Run extract + update in one command
make i18n-refresh

# Now manually edit the .po files...
# Then compile:
make i18n-compile

# Commit
git add backend/app/locales/
git commit -m "Update translations"
```

## File Structure

```
backend/app/locales/
├── messages.pot              # Template (source) - generated from code
├── en/LC_MESSAGES/
│   ├── messages.po          # Edit this ✏️ - Commit ✓
│   └── messages.mo          # Generated - Commit ✓
├── ar/LC_MESSAGES/
│   ├── messages.po          # Edit this ✏️ - Commit ✓
│   └── messages.mo          # Generated - Commit ✓
├── fr/LC_MESSAGES/
│   ├── messages.po          # Edit this ✏️ - Commit ✓
│   └── messages.mo          # Generated - Commit ✓
└── es/LC_MESSAGES/
    ├── messages.po          # Edit this ✏️ - Commit ✓
    └── messages.mo          # Generated - Commit ✓
```

## Comparison: Translations vs Migrations vs Linting

| Aspect | Translations | Migrations | Linting |
|--------|--------------|------------|---------|
| **Extract/Generate** | Local (`make i18n-extract`) | Container (`make makemigrations`) | Local (`ruff check`) |
| **Edit** | Local (`.po` files) | - | Local (code) |
| **Compile/Apply** | Local (`make i18n-compile`) | Container (`make migrate`) | Local (`ruff format`) |
| **Commit** | `.po` + `.mo` files | Migration files | Fixed code |
| **Docker needs** | Just reads `.mo` files | Runs migrations on startup | Just runs code |

## Why Not Compile in Docker?

You **could** compile in Docker, but it's unnecessary complexity:

### ❌ Compile in Docker (Not Recommended)
```dockerfile
# In Dockerfile or entrypoint.sh
RUN python scripts/compile_translations.py
```

**Problems:**
- Slower build time
- Compilation happens every container restart
- Harder to debug translation issues
- More complex setup

### ✅ Compile Locally (Recommended)
```bash
# In development
make i18n-compile
git add backend/app/locales/**/*.mo
git commit -m "Update translations"
```

**Benefits:**
- Fast Docker startup
- See results immediately
- Simple workflow
- Binary files are small (~10KB each)

## Pre-commit Hook (Optional)

Ensure translations are compiled before committing:

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Check if .po files changed
if git diff --cached --name-only | grep -q "\.po$"; then
    echo "📝 .po files changed, compiling translations..."
    make i18n-compile
    
    # Add compiled .mo files
    git add backend/app/locales/**/*.mo
    
    echo "✓ Translations compiled and added to commit"
fi
```

## Common Questions

### Q: Do I commit .mo files to git?
**A: Yes!** They're small (~10KB each) and avoid build complexity.

### Q: Why not compile in Docker like we run migrations?
**A:** Migrations modify the database (stateful). Compilations generate static files (stateless). Static files should be committed.

### Q: What if I forget to compile before committing?
**A:** Docker will use old translations. Just run `make i18n-compile`, commit `.mo` files, and push.

### Q: Can translators work without knowing Python/Docker?
**A:** Yes! Just send them `.po` files, they edit and return them, you compile locally.

### Q: How often should I run i18n-extract?
**A:** After adding new `_("text")` calls in your code. Not every commit, only when adding translatable strings.

## Summary

```bash
# Your typical workflow:
# 1. Code new feature
git add backend/app/api/routes/payments.py
git commit -m "Add payment route"

# 2. Add translations (if you used _() in the code)
make i18n-refresh          # Extract + update
# Edit .po files
make i18n-compile          # Compile
git add backend/app/locales/
git commit -m "Add payment translations"

# 3. Docker just works
make up
```

**Think of it like this:**
- **Linting** = Run locally before commit ✓
- **Formatting** = Run locally before commit ✓
- **Translations** = Run locally before commit ✓
- **Migrations** = Run in Docker after deployment ✓
