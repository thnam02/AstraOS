"""Test configuration.

Sets APP_ENV before the application is imported so startup does not
wait for PostgreSQL.
"""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
