from django.utils.crypto import constant_time_compare
from rest_framework.permissions import BasePermission
from apps.operations.models import Device


class DeviceApiKeyPermission(BasePermission):
    message = 'Invalid device credentials'

    def has_permission(self, request, view):
        # Support single-device requests (header/body) and batch uploads (records list)
        device_id = request.headers.get('X-Device-Id') or request.data.get('device_id')
        api_key = request.headers.get('X-Device-Key') or request.data.get('api_key')
        if device_id and api_key:
            return self._validate_device(request, device_id, api_key)

        records = request.data.get('records') if isinstance(request.data, dict) else None
        if records:
            for item in records:
                item_device_id = item.get('device_id')
                item_api_key = item.get('api_key') or request.headers.get('X-Device-Key')
                if not item_device_id or not item_api_key:
                    return False
                if not self._validate_device(request, item_device_id, item_api_key, attach=False):
                    return False
            return True

        return False

    def _validate_device(self, request, device_id, api_key, attach=True):
        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            return False
        if not device.api_key:
            return False
        if not constant_time_compare(device.api_key, str(api_key)):
            return False
        if attach:
            request.device = device
        return True
