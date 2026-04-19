import os
from datetime import datetime
from peewee import (
    SqliteDatabase, Model, CharField, IntegerField, FloatField,
    BooleanField, DateTimeField, ForeignKeyField
)

# Database initialization
db_path = os.environ.get('DATABASE_PATH', r'D:\MEMORY\CODE\WEB\dashboard.db')
db = SqliteDatabase(db_path)


class BaseModel(Model):
    """Base model with common fields"""
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db


class Site(BaseModel):
    """Website to monitor"""
    name = CharField(unique=True)  # e.g., "oipa.ro"
    domain = CharField(unique=True)  # e.g., "https://oipa.ro"
    host = CharField()  # a2|gazduire|raspibig
    type = CharField()  # wordpress|static|app
    access_method = CharField()  # rest|ssh|ftp|cpanel
    rest_url = CharField(null=True)  # e.g., https://domain/wp-json/
    ssh_host = CharField(null=True)
    ftp_host = CharField(null=True)
    notes = CharField(null=True)
    enabled = BooleanField(default=True)

    class Meta:
        table_name = 'sites'


class HealthCheck(BaseModel):
    """Health check result for a site"""
    site = ForeignKeyField(Site, backref='health_checks')
    http_status = IntegerField(null=True)  # 200, 500, null if timeout
    response_time_ms = IntegerField(null=True)
    ssl_valid = BooleanField(null=True)
    ssl_expires_at = DateTimeField(null=True)
    error_message = CharField(null=True)
    timestamp = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'health_checks'


def init_db():
    """Create tables if they don't exist"""
    db.create_tables([Site, HealthCheck], safe=True)


def get_latest_check(site_id):
    """Get latest health check for a site"""
    return (HealthCheck
            .select()
            .where(HealthCheck.site == site_id)
            .order_by(HealthCheck.timestamp.desc())
            .first())
