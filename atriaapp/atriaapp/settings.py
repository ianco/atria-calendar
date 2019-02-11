import os
import datetime
import platform

try:
    # dateutil is an absolute requirement
    import dateutil
except ImportError:
    raise ImportError(
        'django-swingtime requires the "python-dateutil" package')

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '51m=o=g9accsu3#q2=1ks@(0k2j_1#k%*o(unlr8fldv_(&%6v'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'indyconfig.apps.IndyConfig',
    'modeltranslation',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'background_task',
    'rest_framework',
    'swingtime',
    'atriacalendar',
]

def file_ext():
    if platform.system() == 'Linux':
        return '.so'
    elif platform.system() == 'Darwin':
        return '.dylib'
    elif platform.system() == 'Windows':
        return '.dll'
    else:
        return '.so'

INDY_CONFIG = {
    'storage_dll': 'libindystrgpostgres' + file_ext(),
    'storage_entrypoint': 'postgresstorage_init',
    'payment_dll': 'libnullpay' + file_ext(),
    'payment_entrypoint': 'nullpay_init',
    'wallet_config': {'id': '', 'storage_type': 'postgres_storage'},
    'wallet_credentials': {'key': ''},
    'storage_config': {'url': 'localhost:5432'},
    'storage_credentials': {'account': 'postgres', 'password': 'mysecretpassword', 'admin_account': 'postgres', 'admin_password': 'mysecretpassword'},
    'vcx_agency_url': 'http://localhost:8080',
    'vcx_agency_did': 'VsKV7grR1BUE29mG2Fm2kX',
    'vcx_agency_verkey': 'Hezce2UWMZ3wUhVkh2LfKSs8nDzWwzs2Win7EzNN3YaR',
    'vcx_payment_method': 'null',
    'vcx_enterprise_seed': '000000000000000000000000Trustee1',
    'vcx_institution_seed': '00000000000000000000000000000000',
    'vcx_genesis_path': '/tmp/atria-genesis.txt',
    'register_dids': True,
    'ledger_url': 'http://localhost:9000',
    # local indy ledger
    #'vcx_genesis_url': 'http://localhost:9000/genesis',
    # bcovrin ledger for dflow demo
    #'ledger_url': 'http://dflow.bcovrin.vonx.io',
    #'vcx_genesis_url': 'http://dflow.bcovrin.vonx.io/genesis',
}

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}

BACKGROUND_TASK_RUN_ASYNC = False
BACKGROUND_TASK_ASYNC_THREADS = 1
MAX_ATTEMPTS = 1
#MAX_RUN_TIME = 120

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'indyconfig.simplemiddleware.SimpleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTHENTICATION_BACKENDS = ['indyconfig.indyauth.IndyBackend']

ROOT_URLCONF = 'atriaapp.urls'

SESSION_COOKIE_AGE = 1800

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'atriaapp.wsgi.application'

LOGOUT_REDIRECT_URL = '/'

SWINGTIME = {
    'TIMESLOT_START_TIME': datetime.time(14),
    'TIMESLOT_END_TIME_DURATION': datetime.timedelta(hours=6.5)
}

try:
    import django_extensions
except ImportError:
    pass
else:
    INSTALLED_APPS += ('django_extensions',)

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

AUTH_USER_MODEL = 'atriacalendar.User'

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False

gettext = lambda s: s
LANGUAGES = (
    ('en', gettext('English')),
    ('es', gettext('Spanish')),
    ('zh-hans', gettext('Chinese')),
    ('fr', gettext('French')),
)
MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_TRANSLATION_REGISTRY = "atriacalendar.translation"


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'
