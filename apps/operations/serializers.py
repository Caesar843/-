
"""
运营数据序列化器
-------------
定义运营数据相关的序列化器
"""

from rest_framework import serializers
from apps.operations.models import Device, DeviceData, ManualOperationData, OperationAnalysis


class DeviceSerializer(serializers.ModelSerializer):
    """
    设备序列化器
    """
    
    class Meta:
        model = Device
        fields = '__all__'


class DeviceDataSerializer(serializers.ModelSerializer):
    """
    设备数据序列化器
    """
    
    class Meta:
        model = DeviceData
        fields = '__all__'


class ManualOperationDataSerializer(serializers.ModelSerializer):
    """
    手动运营数据序列化器
    """
    
    class Meta:
        model = ManualOperationData
        fields = '__all__'


class OperationAnalysisSerializer(serializers.ModelSerializer):
    """
    运营分析结果序列化器
    """
    
    class Meta:
        model = OperationAnalysis
        fields = '__all__'
