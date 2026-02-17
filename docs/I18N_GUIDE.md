# Internationalization (i18n) Guide

## Overview

This application supports multiple languages using **Babel** and **gettext** for internationalization. The system automatically detects the user's preferred language and returns translated content accordingly.

## Supported Languages

- **English (en)** - Default
- **Arabic (ar)**
- **French (fr)**
- **Spanish (es)**

You can add more languages by:
1. Adding the language code to `SUPPORTED_LANGUAGES` in `backend/app/core/config.py`
2. Creating translation files with `pybabel init -i backend/app/locales/messages.pot -d backend/app/locales -l <lang_code>`

## Language Detection Priority

The middleware detects language in the following order:

1. **Custom Headers**: `X-Language` or `X-Locale` (e.g., `X-Language: ar`)
   - Explicit language override - always takes priority
   - Useful for testing or when user explicitly changes language in UI
   
2. **User Database Preference**: Authenticated user's `preferred_language` field
   - Automatically uses the user's saved preference from database
   - Requires user to be authenticated (set via your auth middleware)
   
3. **Accept-Language Header**: Standard HTTP header (e.g., `Accept-Language: fr-FR,fr;q=0.9,en;q=0.8`)
   - Browser's language preference
   - Used for unauthenticated requests
   
4. **Default**: Falls back to `DEFAULT_LANGUAGE` from settings (English)

## Usage in Code

### Basic Translation

```python
from backend.app.core.i18n import _

# Simple translation
message = _("Welcome to the Next-Gen Backend API!")

# Translation with parameters
greeting = _("Hello, {name}!", name=user.name)
```

### Plural Forms

```python
from backend.app.core.i18n import ngettext

# Plural form translation
count = 5
message = ngettext(
    "You have {n} message",
    "You have {n} messages",
    count,
    n=count
)
```

### In API Routes

```python
from fastapi import APIRouter
from backend.app.core.i18n import _

router = APIRouter()

@router.get("/welcome")
async def welcome():
    return {"message": _("Welcome to the Next-Gen Backend API!")}

@router.post("/login")
async def login(credentials: LoginSchema):
    if not valid:
        raise HTTPException(
            status_code=401,
            detail=_("Invalid credentials")
        )
    return {"message": _("Login successful")}
```

### In Email Templates

Email templates use Jinja2's i18n extension:

```html
{% extends "base.html" %}

{% block title %}{% trans %}Your OTP Code{% endtrans %}{% endblock %}

{% block content %}
    <p>{% trans %}Hello{% endtrans %},</p>
    <p>{% trans expiry_time=expiry_time %}This OTP is valid for {{ expiry_time }} minutes.{% endtrans %}</p>
{% endblock %}
```

## Handling Context Variables in Templates

### Understanding What to Translate

When working with templates, you need to distinguish between:

1. **Static Text** - Always translate with `{% trans %}`
2. **Dynamic Data** - May or may not need translation
3. **User-Generated Content** - Never translate (names, emails, etc.)

### Rule of Thumb:

| Variable Type | Example | Translation Approach |
|---------------|---------|---------------------|
| **Static text** | "Welcome to our service" | `{% trans %}Welcome to our service{% endtrans %}` |
| **System messages** | "Your OTP is valid for X minutes" | `{% trans expiry=5 %}Your OTP is valid for {{ expiry }} minutes{% endtrans %}` |
| **User input** | User's name, email | **No translation** - use `{{ user_name }}` directly |
| **Config values** | Site name, URLs | **No translation** - use `{{ site_name }}` directly |
| **Numbers/Dates** | Counts, timestamps | Pass directly, but consider locale formatting |

### Examples in Email Templates

#### ✅ CORRECT - Static text with dynamic value:

```html
{% block content %}
    <p>{% trans name=user_name %}Hello, {{ name }}!{% endtrans %}</p>
    <p>{% trans expiry_time=expiry_time %}This OTP is valid for {{ expiry_time }} minutes.{% endtrans %}</p>
{% endblock %}
```

This translates to different languages while keeping the user's name and time value:
- English: "Hello, John! This OTP is valid for 5 minutes."
- Arabic: "مرحباً، John! هذا الرمز صالح لمدة 5 دقيقة."

#### ✅ CORRECT - Site/config values DON'T need translation:

```html
{% block content %}
    <h2>{% trans site_name=site_name %}Welcome to {{ site_name }}{% endtrans %}</h2>
    <p>{% trans %}Thank you for registering.{% endtrans %}</p>
{% endblock %}
```

Result:
- English: "Welcome to NextGen Banking!"
- Arabic: "مرحباً بك في NextGen Banking!"

#### ❌ WRONG - Don't translate everything:

```html
<!-- WRONG: site_name should not be in a separate trans block -->
<h2>{% trans %}Welcome to{% endtrans %} {{ site_name }}</h2>
```

This breaks the sentence structure across languages.

#### ✅ CORRECT - URLs and links stay as-is:

```html
{% block content %}
    <p>{% trans %}If the button doesn't work, copy and paste this link:{% endtrans %}</p>
    <div>{{ activation_url }}</div>
{% endblock %}
```

### Sending Emails with Proper i18n

When sending emails from Python code, set the language context before rendering:

```python
from backend.app.core.emails.base import EmailTemplate
from backend.app.core.i18n import set_language, _

# Get user from database
user = await get_user_by_email(db, email)

# Set the language context to user's preference
set_language(user.preferred_language)  # "ar", "fr", "es", etc.

# Prepare context - these are DATA, not translatable text
context = {
    "site_name": settings.SITE_NAME,      # "NextGen Banking"
    "support_email": settings.MAIL_FROM,  # "support@example.com"
    "otp": "123456",                      # User's OTP code
    "expiry_time": 5,                     # Minutes
    "activation_url": "https://...",      # URL
}

# Define your email class
class OTPEmail(EmailTemplate):
    template_name = "login_otp.html"
    template_name_plain = "login_otp.txt"
    subject = _("Your OTP Code")  # This will be translated

# Send email - template will use current language context
await OTPEmail.send_email(
    email_to=user.email,
    context=context
)
```

The template automatically translates static text based on the language you set with `set_language()`.

### Complete Example: Send OTP in User's Language

```python
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.app.core.db import get_session
from backend.app.core.emails.base import EmailTemplate
from backend.app.core.i18n import set_language, _
from backend.app.core.config import settings

router = APIRouter()

class OTPEmail(EmailTemplate):
    template_name = "login_otp.html"
    template_name_plain = "login_otp.txt"
    subject = _("Your OTP Code")

@router.post("/request-otp")
async def request_otp(
    data: OTPRequestSchema,
    db: AsyncSession = Depends(get_session)
):
    # Get user from database
    user = await get_user_by_email(db, data.email)
    
    # Generate OTP
    otp_code = generate_otp()
    
    # Set language to user's preference
    set_language(user.preferred_language)
    
    # Context with raw data (no translation needed)
    context = {
        "site_name": settings.SITE_NAME,
        "support_email": settings.MAIL_FROM,
        "otp": otp_code,
        "expiry_time": settings.OTP_EXPIRATION_MINUTES,
    }
    
    # Send email - template handles translation
    await OTPEmail.send_email(
        email_to=user.email,
        context=context
    )
    
    return {"message": _("OTP sent successfully")}
```

### Context Variables - What Gets Translated Where:

```python
# In your Python code - Set language, prepare data
from backend.app.core.i18n import set_language, _

# Set user's language BEFORE sending email
set_language(user.preferred_language)  # "ar", "fr", "es"

# Prepare context with RAW DATA (no translation):
context = {
    # Config values:
    "site_name": settings.SITE_NAME,          # "NextGen Banking"
    "support_email": settings.MAIL_FROM,      # "support@example.com"
    
    # Raw user data:
    "otp": "123456",                          # OTP code
    "activation_url": "https://...",          # URL
    "user_name": user.full_name,              # "John Doe"
    "expiry_time": 5,                         # Number (minutes)
}

# Translate the subject in code:
subject = _("Your OTP Code")  # Becomes "رمز التحقق الخاص بك" in Arabic
```

```html
<!-- In your template (login_otp.html): -->
{% block content %}
    <!-- ✅ User data - use directly, no translation: -->
    <p>{% trans %}Hello{% endtrans %}, {{ user_name }}</p>
    
    <!-- ✅ Static text with variable: -->
    <p>{% trans %}Your One-Time Password (OTP) for login is:{% endtrans %}</p>
    <h2>{{ otp }}</h2>  <!-- Raw data, no translation -->
    
    <!-- ✅ Static text WITH interpolated value: -->
    <p>{% trans expiry_time=expiry_time %}This OTP is valid for {{ expiry_time }} minutes.{% endtrans %}</p>
    
    <!-- ✅ URLs - use directly: -->
    <a href="{{ activation_url }}">{% trans %}Activate Account{% endtrans %}</a>
{% endblock %}
```

### Complete Email Example

**Python Code (`backend/app/api/routes/auth.py`):**

```python
from backend.app.core.emails.helpers import send_otp_email, get_email_context
from backend.app.core.emails.base import EmailTemplate, update_jinja_translations
from backend.app.core.i18n import set_language, _

@router.post("/request-otp")
async def request_otp(data: Obase import EmailTemplate
from backend.app.core.i18n import set_language, _

class OTPEmail(EmailTemplate):
    template_name = "login_otp.html"
    template_name_plain = "login_otp.txt"
    subject = _("Your OTP Code")

@router.post("/request-otp")
async def request_otp(data: OTPRequestSchema, db: Session):
    user = await get_user_by_email(db, data.email)
    
    # Generate OTP
    otp_code = generate_otp()
    
    # Set language to user's preference
    set_language(user.preferred_language)  # "ar", "fr", etc.
    
    # Context with raw data
    context = {
        "site_name": settings.SITE_NAME,
        "support_email": settings.MAIL_FROM,
        "otp": otp_code,
        "expiry_time": settings.OTP_EXPIRATION_MINUTES,
    }
    
    # Send - template handles translation based on set_language()
    await OTPEmail.send_email(email_to=user.email, context=contextail Template (`backend/app/core/emails/templates/login_otp.html`):**

```html
{% extends "base.html" %}

{% block title %}{% trans %}Your OTP Code{% endtrans %}{% endblock %}

{% block header %}{% trans %}One-Time Password{% endtrans %}{% endblock %}

{% block content %}
    <p>{% trans %}Hello{% endtrans %},</p>
    
    <p>{% trans %}Your One-Time Password (OTP) for login is:{% endtrans %}</p>
    
    <h2 style="text-align: center; padding: 10px; background-color: f8f9fa; border-radius: 5px;">
        {{ otp }}
    </h2>
    
    <p>{% trans expiry_time=expiry_time %}This OTP is valid for {{ expiry_time }} minutes. Please use it within this timeframe to complete your login process.{% endtrans %}</p>
    
    <p>{% trans %}If you did not request this OTP, please ignore this email and contact our support team immediately.{% endtrans %}</p>
{% endblock %}
```

**Result in Different Languages:**

English:
```
Hello,
Your One-Time Password (OTP) for login is:
123456
This OTP is valid for 5 minutes. Please use it within this timeframe to complete your login process.
```

Arabic:
```
مرحباً،
رمز التحقق (OTP) لتسجيل الدخول هو:
123456
هذا الرمز صالح لمدة 5 دقيقة. يرجى استخدامه خلال هذا الإطار الزمني لإكمال عملية تسجيل الدخول.
```

### Setting Language Manually

```python
from backend.app.core.i18n import set_language

# Set language for the current context
set_language("ar")  # Arabic
```

## Testing Different Languages

### Using cURL

```bash
# Request in Arabic
curl -H "X-Language: ar" http://localhost:8000/api/v1/home/

# Request in French
curl -H "Accept-Language: fr-FR,fr;q=0.9" http://localhost:8000/api/v1/home/

# Request in Spanish
curl -H "X-Language: es" http://localhost:8000/api/v1/home/
```

### Using Python Requests

```python
import requests

# Arabic
response = requests.get(
    "http://localhost:8000/api/v1/home/",
    headers={"X-Language": "ar"}
)

# French
response = requests.get(
    "http://localhost:8000/api/v1/home/",
    headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
)
```

## Managing Translations

### 1. Extract Messages from Code

Extract all translatable strings from Python code and templates:

```bash
make i18n-extract
```

Or manually:

```bash
pybabel extract -F babel.cfg -o backend/app/locales/messages.pot .
```

### 2. Update Translation Files

Update existing translation files with new messages:

```bash
make i18n-update
```

Or manually:

```bash
pybabel update -i backend/app/locales/messages.pot -d backend/app/locales -l ar
pybabel update -i backend/app/locales/messages.pot -d backend/app/locales -l fr
pybabel update -i backend/app/locales/messages.pot -d backend/app/locales -l es
```

### 3. Edit Translation Files

Edit `.po` files in `backend/app/locales/<lang>/LC_MESSAGES/messages.po`:

```po
msgid "Welcome to the Next-Gen Backend API!"
msgstr "مرحباً بك في واجهة برمجة التطبيقات من الجيل القادم!"
```

### 4. Compile Translations

Compile `.po` files to binary `.mo` files:

```bash
make i18n-compile
```

Or manually:

```bash
python scripts/compile_translations.py
```

**Important**: Always compile translations after editing `.po` files!

### 5. Add a New Language

```bash
# Initialize new language (e.g., German)
pybabel init -i backend/app/locales/messages.pot -d backend/app/locales -l de

# Add 'de' to SUPPORTED_LANGUAGES in config.py
# Edit backend/app/locales/de/LC_MESSAGES/messages.po
# Compile translations
make i18n-compile
```

## File Structure

```
backend/app/
├── locales/
│   ├── messages.pot          # Template file (source messages)
│   ├── en/
│   │   └── LC_MESSAGES/
│   │       ├── messages.po   # English translations
│   │       └── messages.mo   # Compiled (binary)
│   ├── ar/
│   │   └── LC_MESSAGES/
│   │       ├── messages.po   # Arabic translations
│   │       └── messages.mo   # Compiled
│   ├── fr/
│   │   └── LC_MESSAGES/
│   │       ├── messages.po   # French translations
│   │       └── messages.mo   # Compiled
│   └── es/
│       └── LC_MESSAGES/
│           ├── messages.po   # Spanish translations
│           └── messages.mo   # Compiled
└── core/
    ├── i18n.py              # i18n utilities
    └── middleware.py        # Language detection middleware
```

## Database Schema

Users can save their language preference:

```python
class User:
    preferred_language: str = "en"  # ISO 639-1 code
```

### Creating Migration

```bash
make makemigrations name="add_user_language_preference"
make migrate
```

## Best Practices

### 1. Mark All User-Facing Strings

```python
# ✅ Good
return {"message": _("Operation successful")}

# ❌ Bad
return {"message": "Operation successful"}
```

### 2. Use Named Placeholders

```python
# ✅ Good - translator can reorder
_("Hello, {name}! You have {count} messages.", name=user.name, count=5)

# ❌ Bad - fixed order
_("Hello, %s! You have %d messages." % (user.name, 5))
```

### 3. Provide Context for Translators

```po
# Good: Add comments for context
#: backend/app/api/routes/auth.py:45
#. This message is shown when user enters wrong password
msgid "Invalid credentials"
msgstr "بيانات الاعتماد غير صحيحة"
```

### 4. Keep Messages Simple

```python
# ✅ Good - Simple, translatable
_("Account created successfully")

# ❌ Bad - Complex, hard to translate
_("Your account has been created successfully and you can now login!")
```

### 5. Extract After Major Changes

Run `make i18n-extract` and `make i18n-update` regularly, especially after:
- Adding new error messages
- Creating new API endpoints
- Updating email templates

## RTL (Right-to-Left) Support

For RTL languages like Arabic, consider:

1. **Frontend**: Use CSS `direction: rtl` for Arabic
2. **Email Templates**: Add RTL styling conditionally
3. **Text Alignment**: Use logical properties (`text-align: start` instead of `left`)

## Performance

- Translations are **cached** using `@lru_cache`
- `.mo` files are loaded once at startup
- Minimal overhead per request
- Language detection happens in middleware

## Troubleshooting

### Translations Not Showing

1. **Check .mo files exist**: Run `make i18n-compile`
2. **Verify language code**: Must match exactly (case-sensitive)
3. **Check Accept-Language header**: Ensure it's properly formatted
4. **Clear cache**: Restart the application

### Missing Translations

1. **Extract messages**: `make i18n-extract`
2. **Update .po files**: `make i18n-update`
3. **Edit translations**: Update `.po` files manually
4. **Compile**: `make i18n-compile`

### Wrong Language Detected

Check the middleware priority:
1. X-Language header (highest)
2. Accept-Language header
3. User preference
4. Default language (lowest)

## Examples

### Complete Authentication Flow

```python
from fastapi import APIRouter, HTTPException
from backend.app.core.i18n import _

router = APIRouter()

@router.post("/register")
async def register(data: RegisterSchema):
    if await user_exists(data.email):
        raise HTTPException(
            status_code=400,
            detail=_("Email already registered")
        )
    
    await create_user(data)
    return {"message": _("Account created successfully")}

@router.post("/login")
async def login(data: LoginSchema):
    user = await authenticate(data.email, data.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail=_("Invalid credentials")
        )
    
    if user.is_locked:
        raise HTTPException(
            status_code=403,
            detail=_("Account locked due to too many failed attempts")
        )
    
    return {"message": _("Login successful")}
```

## Resources

- [Babel Documentation](https://babel.pocoo.org/)
- [Python gettext](https://docs.python.org/3/library/gettext.html)
- [Jinja2 i18n Extension](https://jinja.palletsprojects.com/en/3.1.x/extensions/#i18n-extension)
- [ISO 639-1 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
