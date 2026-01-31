
"""
运营数据应用视图
-------------
定义运营数据应用的视图逻辑，包括API视图和前端视图
"""

from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils.crypto import constant_time_compare

from apps.operations.models import Device, DeviceData, ManualOperationData, OperationAnalysis
from apps.operations.services import OperationAnalysisService
from apps.operations.permissions import DeviceApiKeyPermission
from apps.store.models import Shop




def _filter_by_scope(request, queryset):
    tenant = getattr(request, "tenant", None)
    if tenant is not None:
        queryset = queryset.filter(shop__tenant=tenant)
    try:
        profile = request.user.profile
        if profile.role.role_type == 'SHOP' and profile.shop:
            queryset = queryset.filter(shop=profile.shop)
    except Exception:
        pass
    return queryset


class DeviceViewSet(viewsets.ModelViewSet):
    """
    设备管理API视图
    """
    
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _filter_by_scope(self.request, Device.objects.all())
    
    def get_serializer_class(self):
        """
        获取序列化器类
        """
        from apps.operations.serializers import DeviceSerializer
        return DeviceSerializer


class DeviceDataViewSet(viewsets.ModelViewSet):
    """
    设备数据管理API视图
    """
    
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _filter_by_scope(self.request, DeviceData.objects.all())
    
    def get_serializer_class(self):
        """
        获取序列化器类
        """
        from apps.operations.serializers import DeviceDataSerializer
        return DeviceDataSerializer


class ManualOperationDataViewSet(viewsets.ModelViewSet):
    """
    手动运营数据管理API视图
    """
    
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _filter_by_scope(self.request, ManualOperationData.objects.all())
    
    def get_serializer_class(self):
        """
        获取序列化器类
        """
        from apps.operations.serializers import ManualOperationDataSerializer
        return ManualOperationDataSerializer


class OperationAnalysisViewSet(viewsets.ModelViewSet):
    """
    运营分析结果管理API视图
    """
    
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _filter_by_scope(self.request, OperationAnalysis.objects.all())
    
    def get_serializer_class(self):
        """
        获取序列化器类
        """
        from apps.operations.serializers import OperationAnalysisSerializer
        return OperationAnalysisSerializer


class DeviceDataCollectionAPI(APIView):
    """
    设备数据采集API
    -------------
    用于智能设备向系统上报数据
    """
    
    permission_classes = [DeviceApiKeyPermission]
    
    def post(self, request, format=None):
        """
        处理设备数据上报
        """
        try:
            # 获取设备ID和API密钥
            device_id = request.data.get('device_id')
            api_key = request.data.get('api_key')
            data_type = request.data.get('data_type')
            value = request.data.get('value')
            data_time = request.data.get('data_time')
            
            # 验证参数
            if not all([device_id, api_key, data_type, value]):
                return Response(
                    {'error': 'Missing required parameters'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 验证设备
            device = getattr(request, 'device', None)
            if device is None or device.device_id != device_id:
                return Response(
                    {'error': 'Invalid device ID or API key'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # 更新设备状态
            device.status = Device.DeviceStatus.ONLINE
            device.last_active_at = timezone.now()
            device.save()
            
            # 处理数据时间
            if data_time:
                # 尝试解析数据时间
                try:
                    data_time_obj = datetime.fromisoformat(data_time)
                except ValueError:
                    data_time_obj = timezone.now()
            else:
                data_time_obj = timezone.now()
            
            # 创建设备数据记录
            device_data, created = DeviceData.objects.get_or_create(
                device=device,
                data_type=data_type,
                data_time=data_time_obj,
                defaults={
                    'shop': device.shop,
                    'value': Decimal(str(value)),
                    'metadata': request.data.get('metadata', {}),
                },
            )
            
            # 触发数据分析
            if created:
                self.trigger_analysis(device.shop)
            
            return Response(
                {'success': True, 'data_id': device_data.id},
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def trigger_analysis(self, shop):
        """
        触发数据分析
        """
        # 使用分析服务执行数据分析
        OperationAnalysisService.analyze_shop_data(shop)


class ManualDataUploadView(TemplateView):
    """
    手动数据上传视图
    -------------
    用于店铺手动上传运营数据
    """
    
    template_name = 'operations/manual_upload.html'
    
    def get_context_data(self, **kwargs):
        """
        获取上下文数据
        """
        context = super().get_context_data(**kwargs)
        context['shops'] = Shop.objects.filter(is_deleted=False)
        return context
    
    def post(self, request, *args, **kwargs):
        """
        处理表单提交
        """
        try:
            if request.FILES:
                return render(request, self.template_name, {
                    'error': '该表单不支持文件上传，请使用 CSV 导入功能',
                    'shops': Shop.objects.filter(is_deleted=False)
                })
            # 获取表单数据
            shop_id = request.POST.get('shop')
            data_date = request.POST.get('data_date')
            foot_traffic = request.POST.get('foot_traffic')
            sales_amount = request.POST.get('sales_amount')
            transaction_count = request.POST.get('transaction_count')
            remarks = request.POST.get('remarks')
            
            # 验证参数
            if not all([shop_id, data_date]):
                return render(request, self.template_name, {
                    'error': '店铺和日期为必填项',
                    'shops': Shop.objects.filter(is_deleted=False)
                })
            
            # 获取店铺
            shop = Shop.objects.get(id=shop_id)
            
            # 解析日期
            data_date_obj = datetime.strptime(data_date, '%Y-%m-%d').date()
            
            # 处理可选参数
            foot_traffic = int(foot_traffic) if foot_traffic else None
            sales_amount = Decimal(sales_amount) if sales_amount else None
            transaction_count = int(transaction_count) if transaction_count else None
            
            # 创建或更新手动数据记录
            manual_data, created = ManualOperationData.objects.update_or_create(
                shop=shop,
                data_date=data_date_obj,
                defaults={
                    'foot_traffic': foot_traffic,
                    'sales_amount': sales_amount,
                    'transaction_count': transaction_count,
                    'uploaded_by': request.user.username if hasattr(request.user, 'username') else 'admin',
                    'remarks': remarks
                }
            )
            
            # 触发数据分析
            OperationAnalysisService.analyze_shop_data(shop)
            
            return redirect('operations:dashboard')
            
        except Exception as e:
            return render(request, self.template_name, {
                'error': str(e),
                'shops': Shop.objects.filter(is_deleted=False)
            })


class OperationDashboardView(TemplateView):
    """
    运营数据仪表盘视图
    -------------
    用于展示运营数据的可视化界面
    """
    
    template_name = 'operations/dashboard.html'
    
    def get_context_data(self, **kwargs):
        """???????"""
        context = super().get_context_data(**kwargs)

        time_range = self.request.GET.get('time_range', '7')
        shop_id = self.request.GET.get('shop_id')

        days = int(time_range)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        if shop_id:
            shops = list(Shop.objects.filter(id=shop_id, is_deleted=False))
        else:
            shops = list(Shop.objects.filter(is_deleted=False))

        shop_ids = [s.id for s in shops]
        analysis_by_key = {}
        if shop_ids:
            analyses = (
                OperationAnalysis.objects
                .filter(shop_id__in=shop_ids, analyzed_at__date__gte=start_date.date(), analyzed_at__date__lte=end_date.date())
                .order_by('shop_id', 'analyzed_at')
            )
            for analysis in analyses:
                key = (analysis.shop_id, analysis.analyzed_at.date())
                prev = analysis_by_key.get(key)
                if prev is None or analysis.analyzed_at > prev.analyzed_at:
                    analysis_by_key[key] = analysis

        date_list = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_list.append(current_date)
            current_date += timedelta(days=1)

        dashboard_data = []
        total_foot_traffic = 0
        total_sales = Decimal('0')
        total_transactions = 0
        total_conversion_rate = 0

        # ????????
        trend_map = {d: {'foot_traffic': 0, 'sales': Decimal('0')} for d in date_list}

        for shop in shops:
            daily_data = []
            shop_foot_traffic = 0
            shop_sales = Decimal('0')
            shop_transactions = 0

            for d in date_list:
                day_analysis = analysis_by_key.get((shop.id, d))
                day_foot_traffic = day_analysis.total_foot_traffic if day_analysis else 0
                day_sales = day_analysis.total_sales if day_analysis else Decimal('0')
                day_transactions = day_analysis.analysis_result.get('total_transactions', 0) if day_analysis else 0

                shop_foot_traffic += day_foot_traffic
                shop_sales += day_sales
                shop_transactions += day_transactions

                trend_map[d]['foot_traffic'] += day_foot_traffic
                trend_map[d]['sales'] += day_sales

                daily_data.append({
                    'date': d.strftime('%Y-%m-%d'),
                    'foot_traffic': day_foot_traffic,
                    'sales': float(day_sales),
                    'transactions': day_transactions
                })

            shop_avg_transaction_value = (shop_sales / shop_transactions) if shop_transactions > 0 else Decimal('0')
            shop_conversion_rate = (shop_transactions / shop_foot_traffic * 100) if shop_foot_traffic > 0 else 0

            total_foot_traffic += shop_foot_traffic
            total_sales += shop_sales
            total_transactions += shop_transactions
            total_conversion_rate += shop_conversion_rate

            dashboard_data.append({
                'shop_id': shop.id,
                'shop_name': shop.name,
                'total_foot_traffic': shop_foot_traffic,
                'total_sales': float(shop_sales),
                'total_transactions': shop_transactions,
                'average_transaction_value': float(shop_avg_transaction_value),
                'conversion_rate': shop_conversion_rate,
                'daily_data': daily_data
            })

        avg_transaction_value = (total_sales / total_transactions) if total_transactions > 0 else Decimal('0')
        avg_conversion_rate = (total_conversion_rate / len(shops)) if len(shops) > 0 else 0

        trend_data = [
            {
                'date': d.strftime('%Y-%m-%d'),
                'foot_traffic': trend_map[d]['foot_traffic'],
                'sales': float(trend_map[d]['sales'])
            }
            for d in date_list
        ]

        context['dashboard_data'] = dashboard_data
        context['trend_data'] = trend_data
        context['total_foot_traffic'] = total_foot_traffic
        context['total_sales'] = float(total_sales)
        context['total_transactions'] = total_transactions
        context['avg_transaction_value'] = float(avg_transaction_value)
        context['avg_conversion_rate'] = float(avg_conversion_rate)
        context['start_date'] = str(start_date.date())
        context['end_date'] = str(end_date.date())
        context['time_range'] = time_range
        context['shops'] = [{'id': shop.id, 'name': shop.name} for shop in Shop.objects.filter(is_deleted=False)]
        context['selected_shop'] = shop_id

        return context


class AnalysisView(TemplateView):
    """
    数据分析视图
    -------------
    用于展示详细的数据分析结果
    """
    
    template_name = 'operations/analysis.html'
    
    def get_context_data(self, **kwargs):
        """
        获取上下文数据
        """
        context = super().get_context_data(**kwargs)
        
        # 获取所有店铺
        shops = Shop.objects.filter(is_deleted=False)
        
        # 获取分析结果
        analyses = OperationAnalysis.objects.order_by('-analyzed_at')[:20]
        
        context['shops'] = shops
        context['analyses'] = analyses
        
        return context


class DeviceManagementView(TemplateView):
    """
    设备管理视图
    -------------
    用于管理智能设备
    """
    
    template_name = 'operations/device_management.html'
    
    def get_context_data(self, **kwargs):
        """
        获取上下文数据
        """
        context = super().get_context_data(**kwargs)
        
        # 获取所有设备
        devices = Device.objects.all()
        
        # 获取所有店铺
        shops = Shop.objects.filter(is_deleted=False)
        
        context['devices'] = devices
        context['shops'] = shops
        
        return context


class ReportsView(TemplateView):
    """
    数据报表视图
    -------------
    用于生成和展示数据报表
    """
    
    template_name = 'operations/reports.html'
    
    def get_context_data(self, **kwargs):
        """
        获取上下文数据
        """
        context = super().get_context_data(**kwargs)
        
        # 获取所有店铺
        shops = Shop.objects.filter(is_deleted=False)
        
        context['shops'] = shops
        
        return context


class DeviceDataReceiveAPIView(APIView):
    """
    设备数据接收API端点
    
    用途：
    - 接收来自物联网设备的实时数据
    - 支持客流统计仪、POS机、环境传感器等多种设备类型
    - 支持批量数据上传
    
    端点: POST /api/operations/device_data/
    
    请求格式：
    {
        "device_id": "DEVICE_001",
        "device_type": "FOOT_TRAFFIC",
        "shop_id": 1,
        "timestamp": "2024-01-16T10:30:00+08:00",
        "data": {
            "traffic_count": 120,
            "temperature": 22.5,
            "humidity": 65
        }
    }
    
    批量上传（可选）：
    {
        "records": [
            { "device_id": "...", "data": {...} },
            { "device_id": "...", "data": {...} }
        ]
    }
    """
    
    permission_classes = [DeviceApiKeyPermission]
    
    def post(self, request):
        """
        接收设备数据并存储
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 检查是否为批量上传
            data = request.data
            records = data.get('records', [])
            
            if records:
                # 批量处理
                return self._handle_batch_upload(request, records)
            else:
                # 单条处理
                return self._handle_single_upload(request, data)
                
        except Exception as e:
            logger.error(f"Error in device data upload: {str(e)}")
            return Response(
                {
                    'status': 'error',
                    'message': f'设备数据上传失败: {str(e)}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _handle_single_upload(self, request, data):
        """处理单条设备数据上传"""
        import logging
        logger = logging.getLogger(__name__)

        device_id = data.get('device_id')
        device_type = data.get('device_type')
        shop_id = data.get('shop_id')
        timestamp = data.get('timestamp')
        device_data = data.get('data', {})

        if not all([device_id, device_type, shop_id]):
            return Response(
                {
                    'status': 'error',
                    'message': '缺少必填字段：device_id, device_type, shop_id'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = data.get('api_key') or request.headers.get('X-Device-Key')
        if not api_key:
            return Response(
                {'status': 'error', 'message': '缺少 api_key'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            device = getattr(request, 'device', None)
            if device is None or device.device_id != device_id:
                return Response(
                    {'status': 'error', 'message': '设备密钥校验失败'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except Device.DoesNotExist:
            return Response(
                {'status': 'error', 'message': f'设备不存在: {device_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not device.api_key or not constant_time_compare(device.api_key, str(api_key)):
            return Response(
                {'status': 'error', 'message': '设备密钥校验失败'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if str(device.shop_id) != str(shop_id):
            return Response(
                {'status': 'error', 'message': 'shop_id 与设备不匹配'},
                status=status.HTTP_403_FORBIDDEN
            )

        device.status = Device.DeviceStatus.ONLINE
        device.last_active_at = timezone.now()
        device.ip_address = self._get_client_ip(request)
        device.save(update_fields=['status', 'last_active_at', 'ip_address'])

        if timestamp:
            try:
                from django.utils.dateparse import parse_datetime
                record_time = parse_datetime(timestamp)
            except Exception:
                record_time = timezone.now()
        else:
            record_time = timezone.now()

        value = self._extract_numeric_value(device_data)
        device_record, created = DeviceData.objects.get_or_create(
            device=device,
            data_type=device_type,
            data_time=record_time,
            defaults={
                'shop_id': shop_id,
                'value': value,
                'metadata': device_data,
            },
        )

        logger.info(f"Device data received from {device_id}: {device_record.id}")

        return Response(
            {
                'status': 'success',
                'message': '设备数据已接收',
                'data': {
                    'record_id': device_record.id,
                    'device_id': device.device_id,
                    'timestamp': record_time.isoformat()
                }
            },
            status=status.HTTP_201_CREATED
        )

    def _handle_batch_upload(self, request, records):
        """处理批量设备数据上传"""
        import logging
        logger = logging.getLogger(__name__)

        result = {
            'status': 'success',
            'total_records': len(records),
            'success_count': 0,
            'failed_count': 0,
            'failed_items': []
        }

        for idx, item in enumerate(records):
            try:
                device_id = item.get('device_id')
                device_type = item.get('device_type')
                shop_id = item.get('shop_id')
                timestamp = item.get('timestamp')
                device_data = item.get('data', {})

                if not all([device_id, device_type, shop_id]):
                    result['failed_count'] += 1
                    result['failed_items'].append({
                        'index': idx,
                        'device_id': device_id,
                        'error': '缺少必填字段'
                    })
                    continue

                api_key = item.get('api_key') or request.headers.get('X-Device-Key')
                if not api_key:
                    result['failed_count'] += 1
                    result['failed_items'].append({
                        'index': idx,
                        'device_id': device_id,
                        'error': '缺少 api_key'
                    })
                    continue

                try:
                    device = Device.objects.get(device_id=device_id)
                except Device.DoesNotExist:
                    result['failed_count'] += 1
                    result['failed_items'].append({
                        'index': idx,
                        'device_id': device_id,
                        'error': '设备不存在'
                    })
                    continue

                if not device.api_key or not constant_time_compare(device.api_key, str(api_key)):
                    result['failed_count'] += 1
                    result['failed_items'].append({
                        'index': idx,
                        'device_id': device_id,
                        'error': '设备密钥校验失败'
                    })
                    continue

                if str(device.shop_id) != str(shop_id):
                    result['failed_count'] += 1
                    result['failed_items'].append({
                        'index': idx,
                        'device_id': device_id,
                        'error': 'shop_id 与设备不匹配'
                    })
                    continue

                device.status = Device.DeviceStatus.ONLINE
                device.last_active_at = timezone.now()
                device.save(update_fields=['status', 'last_active_at'])

                if timestamp:
                    try:
                        from django.utils.dateparse import parse_datetime
                        record_time = parse_datetime(timestamp)
                    except Exception:
                        record_time = timezone.now()
                else:
                    record_time = timezone.now()

                value = self._extract_numeric_value(device_data)
                DeviceData.objects.get_or_create(
                    device=device,
                    data_type=device_type,
                    data_time=record_time,
                    defaults={
                        'shop_id': shop_id,
                        'value': value,
                        'metadata': device_data,
                    },
                )

                result['success_count'] += 1
                logger.info(f"Batch device data received from {device_id}")

            except Exception as e:
                result['failed_count'] += 1
                result['failed_items'].append({
                    'index': idx,
                    'device_id': item.get('device_id', 'unknown'),
                    'error': str(e)
                })
                logger.error(f"Error processing batch item {idx}: {str(e)}")

        return Response(result, status=status.HTTP_200_OK)


    @staticmethod
    def _get_client_ip(request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def _extract_numeric_value(payload):
        for key in ('value', 'traffic_count', 'sales_amount', 'sales'):
            if key in payload and payload[key] is not None:
                try:
                    return Decimal(str(payload[key]))
                except Exception:
                    break
        return Decimal('0')


class DeviceStatusUpdateAPIView(APIView):
    """
    设备状态更新API端点
    
    用途：
    - 更新设备的在线/离线状态
    - 更新设备的配置和信息
    
    端点: PATCH /api/operations/device/{device_id}/status/
    
    请求格式：
    {
        "status": "ONLINE" | "OFFLINE" | "MAINTENANCE",
        "ip_address": "192.168.1.100",
        "last_active_at": "2024-01-16T10:30:00+08:00"
    }
    """
    
    permission_classes = [DeviceApiKeyPermission]
    
    def patch(self, request, device_id):
        """更新设备状态"""
        try:
            device = Device.objects.get(device_id=device_id)
            
            # 更新设备状态
            status_value = request.data.get('status')
            if status_value and status_value in dict(Device.DeviceStatus.choices):
                device.status = status_value
            
            # 更新 IP 地址
            ip_address = request.data.get('ip_address')
            if ip_address:
                device.ip_address = ip_address
            
            # 更新最后活跃时间
            device.last_active_at = timezone.now()
            
            device.save()
            
            return Response(
                {
                    'status': 'success',
                    'message': '设备状态已更新',
                    'data': {
                        'device_id': device.device_id,
                        'status': device.status,
                        'last_active_at': device.last_active_at.isoformat()
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Device.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': f'设备不存在: {device_id}'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    'status': 'error',
                    'message': f'设备状态更新失败: {str(e)}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
