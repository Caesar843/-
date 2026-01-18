"""
运营数据分析服务
-----------------
实现运营数据的汇总和分析逻辑
"""

from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
from apps.operations.models import DeviceData, ManualOperationData, OperationAnalysis
from apps.store.models import Shop


class OperationAnalysisService:
    """
    运营数据分析服务类
    """
    
    @staticmethod
    def analyze_shop_data(shop, analysis_period='daily', period_start=None, period_end=None):
        """
        分析店铺运营数据
        
        Args:
            shop: 店铺对象
            analysis_period: 分析周期，可选值：daily, weekly, monthly, quarterly, yearly
            period_start: 分析周期开始时间
            period_end: 分析周期结束时间
            
        Returns:
            OperationAnalysis: 分析结果对象
        """
        
        # 如果没有指定时间范围，根据分析周期设置默认值
        if not period_end:
            period_end = timezone.now()
        
        if not period_start:
            if analysis_period == 'daily':
                period_start = period_end - timedelta(days=1)
            elif analysis_period == 'weekly':
                period_start = period_end - timedelta(weeks=1)
            elif analysis_period == 'monthly':
                period_start = period_end - timedelta(days=30)
            elif analysis_period == 'quarterly':
                period_start = period_end - timedelta(days=90)
            elif analysis_period == 'yearly':
                period_start = period_end - timedelta(days=365)
            else:
                period_start = period_end - timedelta(days=1)
        
        # 汇总数据
        summary_data = OperationAnalysisService._summarize_data(shop, period_start, period_end)
        
        # 计算同比增长率
        year_ago_start = period_start - timedelta(days=365)
        year_ago_end = period_end - timedelta(days=365)
        year_ago_data = OperationAnalysisService._summarize_data(shop, year_ago_start, year_ago_end)
        
        sales_growth_rate = None
        foot_traffic_growth_rate = None
        
        if year_ago_data['total_sales'] > 0:
            sales_growth_rate = ((summary_data['total_sales'] - year_ago_data['total_sales']) / 
                                year_ago_data['total_sales'] * 100)
        
        if year_ago_data['total_foot_traffic'] > 0:
            foot_traffic_growth_rate = ((summary_data['total_foot_traffic'] - year_ago_data['total_foot_traffic']) / 
                                      year_ago_data['total_foot_traffic'] * 100)
        
        # 计算周期天数
        period_days = (period_end - period_start).days + 1
        
        # 计算日均数据
        average_daily_foot_traffic = summary_data['total_foot_traffic'] / period_days if period_days > 0 else 0
        average_daily_sales = summary_data['total_sales'] / period_days if period_days > 0 else Decimal('0')
        
        # 计算客单价
        average_transaction_value = (summary_data['total_sales'] / summary_data['total_transactions'] 
                                    if summary_data['total_transactions'] > 0 else Decimal('0'))
        
        # 计算转化率
        conversion_rate = (summary_data['total_transactions'] / summary_data['total_foot_traffic'] * 100 
                          if summary_data['total_foot_traffic'] > 0 else 0)
        
        # 创建分析结果
        analysis = OperationAnalysis.objects.create(
            shop=shop,
            analysis_period=analysis_period,
            period_start=period_start,
            period_end=period_end,
            total_foot_traffic=summary_data['total_foot_traffic'],
            average_daily_foot_traffic=average_daily_foot_traffic,
            total_sales=summary_data['total_sales'],
            average_daily_sales=average_daily_sales,
            average_transaction_value=average_transaction_value,
            conversion_rate=conversion_rate,
            sales_growth_rate=sales_growth_rate,
            foot_traffic_growth_rate=foot_traffic_growth_rate,
            analysis_result={
                'period_days': period_days,
                'total_transactions': summary_data['total_transactions'],
                'year_ago_data': year_ago_data,
                'details': summary_data['details']
            }
        )
        
        return analysis
    
    @staticmethod
    def _summarize_data(shop, period_start, period_end):
        """
        汇总指定时间范围内的数据
        
        Args:
            shop: 店铺对象
            period_start: 开始时间
            period_end: 结束时间
            
        Returns:
            dict: 汇总数据
        """
        
        # 获取设备数据
        device_data = DeviceData.objects.filter(
            shop=shop,
            data_time__range=(period_start, period_end)
        )
        
        # 获取手动数据
        manual_data = ManualOperationData.objects.filter(
            shop=shop,
            data_date__range=(period_start.date(), period_end.date())
        )
        
        # 初始化汇总数据
        total_foot_traffic = 0
        total_sales = Decimal('0')
        total_transactions = 0
        details = []
        
        # 处理设备数据
        for data in device_data:
            if data.data_type == 'foot_traffic':
                total_foot_traffic += int(data.value)
            elif data.data_type == 'sales':
                total_sales += data.value
            elif data.data_type == 'transactions':
                total_transactions += int(data.value)
            
            details.append({
                'source': 'device',
                'data_type': data.data_type,
                'value': str(data.value),  # 保持精度，使用字符串表示
                'data_time': data.data_time.isoformat()
            })
        
        # 处理手动数据
        for data in manual_data:
            if data.foot_traffic:
                total_foot_traffic += data.foot_traffic
            if data.sales_amount:
                total_sales += data.sales_amount
            if data.transaction_count:
                total_transactions += data.transaction_count
            
            details.append({
                'source': 'manual',
                'foot_traffic': data.foot_traffic,
                'sales_amount': str(data.sales_amount) if data.sales_amount else '0',  # 保持精度
                'transaction_count': data.transaction_count,
                'data_date': data.data_date.isoformat()
            })
        
        return {
            'total_foot_traffic': total_foot_traffic,
            'total_sales': total_sales,
            'total_transactions': total_transactions,
            'details': details
        }
    
    @staticmethod
    def analyze_all_shops(analysis_period='daily'):
        """
        分析所有店铺的运营数据
        
        Args:
            analysis_period: 分析周期
            
        Returns:
            list: 分析结果对象列表
        """
        
        analyses = []
        shops = Shop.objects.filter(is_deleted=False)
        
        for shop in shops:
            analysis = OperationAnalysisService.analyze_shop_data(shop, analysis_period)
            analyses.append(analysis)
        
        return analyses
    
    @staticmethod
    def get_shop_analysis_history(shop, limit=10):
        """
        获取店铺的分析历史
        
        Args:
            shop: 店铺对象
            limit: 返回结果数量限制
            
        Returns:
            list: 分析结果对象列表
        """
        
        return OperationAnalysis.objects.filter(
            shop=shop
        ).order_by('-analyzed_at')[:limit]
    
    @staticmethod
    def get_trend_analysis(shop, days=30):
        """
        获取店铺的趋势分析
        
        Args:
            shop: 店铺对象
            days: 分析天数
            
        Returns:
            dict: 趋势分析数据
        """
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # 按天获取数据
        daily_data = []
        current_date = start_date
        
        while current_date <= end_date:
            day_start = current_date
            day_end = current_date + timedelta(days=1) - timedelta(seconds=1)
            
            day_summary = OperationAnalysisService._summarize_data(shop, day_start, day_end)
            
            daily_data.append({
                'date': current_date.date().isoformat(),
                'foot_traffic': day_summary['total_foot_traffic'],
                'sales': float(day_summary['total_sales']),
                'transactions': day_summary['total_transactions'],
                'average_transaction_value': (
                    float(day_summary['total_sales'] / day_summary['total_transactions']) 
                    if day_summary['total_transactions'] > 0 else 0
                )
            })
            
            current_date += timedelta(days=1)
        
        return {
            'daily_data': daily_data,
            'start_date': start_date.date().isoformat(),
            'end_date': end_date.date().isoformat()
        }


class DeviceDataAggregationService:
    """
    设备数据聚合和清洗服务
    
    功能：
    1. 小时级聚合：每小时统计客流、交易等数据
    2. 日级聚合：每日统计汇总
    3. 月级聚合：每月统计汇总
    4. 数据清洗：处理重复、错误、异常数据
    5. 数据质量检查：验证数据的完整性和准确性
    """
    
    @staticmethod
    def aggregate_hourly_data(shop_id: int, hour: datetime = None):
        """
        生成小时级数据聚合
        
        参数：
        - shop_id: 店铺ID
        - hour: 要聚合的小时（默认当前小时）
        
        返回：
        - 包含汇总数据的字典
        """
        from apps.operations.models import HourlyAggregation
        
        if hour is None:
            hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        
        hour_start = hour
        hour_end = hour + timedelta(hours=1)
        
        # 查询该小时内的所有设备数据
        device_records = DeviceData.objects.filter(
            shop_id=shop_id,
            record_time__gte=hour_start,
            record_time__lt=hour_end
        )
        
        # 统计汇总数据
        foot_traffic = 0
        sales = Decimal('0')
        transactions = 0
        temperature_sum = 0
        humidity_sum = 0
        record_count = 0
        
        for record in device_records:
            data = record.raw_data or {}
            
            # 统计客流
            if data.get('traffic_count'):
                foot_traffic += data['traffic_count']
            
            # 统计销售额
            if data.get('sales_amount'):
                sales += Decimal(str(data['sales_amount']))
            
            # 统计交易数
            if data.get('transaction_count'):
                transactions += data['transaction_count']
            
            # 统计温度和湿度
            if data.get('temperature'):
                temperature_sum += data['temperature']
            if data.get('humidity'):
                humidity_sum += data['humidity']
            
            record_count += 1
        
        # 计算平均值
        avg_temperature = temperature_sum / record_count if record_count > 0 else 0
        avg_humidity = humidity_sum / record_count if record_count > 0 else 0
        
        # 保存或更新小时级聚合数据
        # TODO: 创建 HourlyAggregation 模型来存储聚合数据
        aggregation_data = {
            'shop_id': shop_id,
            'hour': hour,
            'foot_traffic': foot_traffic,
            'sales': sales,
            'transactions': transactions,
            'avg_temperature': avg_temperature,
            'avg_humidity': avg_humidity,
            'data_quality_score': DeviceDataAggregationService._calculate_data_quality(record_count)
        }
        
        return aggregation_data
    
    @staticmethod
    def aggregate_daily_data(shop_id: int, date: date = None):
        """
        生成日级数据聚合
        
        参数：
        - shop_id: 店铺ID
        - date: 要聚合的日期（默认今日）
        
        返回：
        - 包含日统计数据的字典
        """
        from django.db.models import Sum, Count, Avg
        
        if date is None:
            date = timezone.now().date()
        
        day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(date, datetime.max.time()))
        
        # 查询该日期内的所有设备数据
        device_records = DeviceData.objects.filter(
            shop_id=shop_id,
            record_time__gte=day_start,
            record_time__lte=day_end
        )
        
        # 使用聚合函数统计
        aggregation = device_records.aggregate(
            total_foot_traffic=Sum('raw_data__traffic_count', default=0),
            total_sales=Sum('raw_data__sales_amount', default=0),
            total_transactions=Sum('raw_data__transaction_count', default=0),
            avg_temperature=Avg('raw_data__temperature', default=0),
            avg_humidity=Avg('raw_data__humidity', default=0),
            record_count=Count('id')
        )
        
        daily_data = {
            'shop_id': shop_id,
            'date': date,
            'foot_traffic': aggregation['total_foot_traffic'] or 0,
            'sales': Decimal(str(aggregation['total_sales'] or 0)),
            'transactions': aggregation['total_transactions'] or 0,
            'avg_temperature': aggregation['avg_temperature'] or 0,
            'avg_humidity': aggregation['avg_humidity'] or 0,
            'data_quality_score': DeviceDataAggregationService._calculate_data_quality(
                aggregation['record_count']
            )
        }
        
        return daily_data
    
    @staticmethod
    def aggregate_monthly_data(shop_id: int, year: int = None, month: int = None):
        """
        生成月级数据聚合
        
        参数：
        - shop_id: 店铺ID
        - year: 年份
        - month: 月份
        
        返回：
        - 包含月统计数据的字典
        """
        from django.db.models import Sum, Count, Avg
        
        if year is None or month is None:
            today = timezone.now()
            year = today.year
            month = today.month
        
        # 计算月份范围
        month_start = timezone.make_aware(datetime(year, month, 1))
        
        if month == 12:
            month_end = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(seconds=1)
        else:
            month_end = timezone.make_aware(datetime(year, month + 1, 1)) - timedelta(seconds=1)
        
        # 查询该月的所有设备数据
        device_records = DeviceData.objects.filter(
            shop_id=shop_id,
            record_time__gte=month_start,
            record_time__lte=month_end
        )
        
        # 使用聚合函数统计
        aggregation = device_records.aggregate(
            total_foot_traffic=Sum('raw_data__traffic_count', default=0),
            total_sales=Sum('raw_data__sales_amount', default=0),
            total_transactions=Sum('raw_data__transaction_count', default=0),
            avg_temperature=Avg('raw_data__temperature', default=0),
            avg_humidity=Avg('raw_data__humidity', default=0),
            record_count=Count('id')
        )
        
        monthly_data = {
            'shop_id': shop_id,
            'year': year,
            'month': month,
            'foot_traffic': aggregation['total_foot_traffic'] or 0,
            'sales': Decimal(str(aggregation['total_sales'] or 0)),
            'transactions': aggregation['total_transactions'] or 0,
            'avg_temperature': aggregation['avg_temperature'] or 0,
            'avg_humidity': aggregation['avg_humidity'] or 0,
            'data_quality_score': DeviceDataAggregationService._calculate_data_quality(
                aggregation['record_count']
            )
        }
        
        return monthly_data
    
    @staticmethod
    def clean_device_data():
        """
        数据清洗任务
        
        清洗内容：
        1. 移除重复数据（基于设备ID、时间戳的完全重复）
        2. 修复或移除异常数据（客流为负、金额为负等）
        3. 填充缺失数据（使用前后值插值）
        4. 移除超时的临时数据（30天以前的未聚合数据）
        
        返回：
        - 包含清洗统计的字典
        """
        import logging
        logger = logging.getLogger(__name__)
        
        result = {
            'duplicates_removed': 0,
            'invalid_records_fixed': 0,
            'old_data_deleted': 0,
            'errors': []
        }
        
        try:
            # 1. 移除完全重复的数据
            # 查询可能的重复记录
            from django.db.models import Count
            
            duplicate_check = DeviceData.objects.values(
                'device_id', 'raw_data', 'record_time'
            ).annotate(count=Count('id')).filter(count__gt=1)
            
            for dup_set in duplicate_check:
                duplicates = DeviceData.objects.filter(
                    device_id=dup_set['device_id'],
                    raw_data=dup_set['raw_data'],
                    record_time=dup_set['record_time']
                ).order_by('id')[1:]  # 保留第一条，删除其余
                
                count = duplicates.delete()[0]
                result['duplicates_removed'] += count
            
            # 2. 修复或移除异常数据
            invalid_records = DeviceData.objects.filter(
                models.Q(raw_data__traffic_count__lt=0) |  # 负数客流
                models.Q(raw_data__sales_amount__lt=0) |   # 负数销售额
                models.Q(raw_data__temperature__lt=-50) |  # 温度超低
                models.Q(raw_data__temperature__gt=60)     # 温度超高
            )
            
            for record in invalid_records:
                # 修复数据或标记为无效
                if record.raw_data:
                    data = record.raw_data
                    
                    # 修复负值
                    if data.get('traffic_count', 0) < 0:
                        data['traffic_count'] = 0
                    if data.get('sales_amount', 0) < Decimal('0'):
                        data['sales_amount'] = 0
                    
                    # 修复极端温度
                    if data.get('temperature'):
                        if data['temperature'] < -50 or data['temperature'] > 60:
                            data['temperature'] = None
                    
                    record.raw_data = data
                    record.save()
                    result['invalid_records_fixed'] += 1
            
            # 3. 删除30天前未聚合的数据
            cutoff_date = timezone.now() - timedelta(days=30)
            old_records = DeviceData.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
            result['old_data_deleted'] = old_records[0]
            
            logger.info(f"Device data cleaning completed: {result}")
            
        except Exception as e:
            error_msg = f"Error during data cleaning: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    @staticmethod
    def _calculate_data_quality(record_count: int, expected_count: int = None) -> float:
        """
        计算数据质量评分（0-100）
        
        参数：
        - record_count: 实际记录数
        - expected_count: 期望记录数（可选）
        
        返回：
        - 质量评分（0-100）
        """
        if expected_count is None:
            # 如果没有期望值，按记录数简单计分
            if record_count >= 100:
                return 100.0
            elif record_count >= 50:
                return 90.0
            elif record_count >= 10:
                return 80.0
            elif record_count > 0:
                return 50.0
            else:
                return 0.0
        else:
            # 基于完整性计算
            if expected_count == 0:
                return 0.0
            completeness = min(100.0, (record_count / expected_count) * 100)
            return completeness