import json
from datetime import date, datetime
from decimal import Decimal

from django.db import models


def serialize_instance(instance, fields):
    data = {}
    for field in fields:
        value = getattr(instance, field, None)
        data[field] = _normalize_value(value)
    return data


def _normalize_value(value):
    if isinstance(value, models.Model):
        return value.pk
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def normalize_for_hash(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
