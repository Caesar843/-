import logging
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd
from io import BytesIO, StringIO
from apps.data_governance.models import DailyFinanceAgg
from apps.store.models import Shop, Contract
from apps.operations.models import DeviceData, ManualOperationData, OperationAnalysis
from apps.finance.models import FinanceRecord

logger = logging.getLogger(__name__)


class ReportService:
    """
    报表服务层
    -------------  
    提供各种报表数据生成和导出功能
    """
    
    @staticmethod
    def get_shop_operation_summary(start_date, end_date, shop_id=None):
        """
        获取店铺运营数据汇总
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            shop_id: 店铺ID，None表示全部店铺
            
        Returns:
            dict: 运营数据汇总
        """
        # 获取店铺列表
        if shop_id:
            shops = Shop.objects.filter(id=shop_id, is_deleted=False)
        else:
            shops = Shop.objects.filter(is_deleted=False)
        
        summary_data = []
        total_foot_traffic = 0
        total_sales = Decimal('0')
        total_transactions = 0
        
        for shop in shops:
            # 获取运营数据
            manual_datas = ManualOperationData.objects.filter(
                shop=shop,
                data_date__range=[start_date, end_date]
            )
            
            # 汇总数据
            shop_foot_traffic = sum(data.foot_traffic or 0 for data in manual_datas)
            shop_sales = sum(data.sales_amount or Decimal('0') for data in manual_datas)
            shop_transactions = sum(data.transaction_count or 0 for data in manual_datas)
            
            # 计算客单价和转化率
            avg_transaction_value = (shop_sales / shop_transactions) if shop_transactions > 0 else Decimal('0')
            conversion_rate = (shop_transactions / shop_foot_traffic * 100) if shop_foot_traffic > 0 else 0
            
            summary_data.append({
                'shop_name': shop.name,
                'business_type': shop.get_business_type_display(),
                'area': shop.area,
                'rent': shop.rent,
                'foot_traffic': shop_foot_traffic,
                'sales_amount': shop_sales,
                'transaction_count': shop_transactions,
                'avg_transaction_value': avg_transaction_value,
                'conversion_rate': conversion_rate
            })
            
            # 累加总计
            total_foot_traffic += shop_foot_traffic
            total_sales += shop_sales
            total_transactions += shop_transactions
        
        # 计算总计
        total_avg_transaction_value = (total_sales / total_transactions) if total_transactions > 0 else Decimal('0')
        total_conversion_rate = (total_transactions / total_foot_traffic * 100) if total_foot_traffic > 0 else 0
        
        return {
            'summary_data': summary_data,
            'total_foot_traffic': total_foot_traffic,
            'total_sales': total_sales,
            'total_transactions': total_transactions,
            'total_avg_transaction_value': total_avg_transaction_value,
            'total_conversion_rate': total_conversion_rate,
            'start_date': start_date,
            'end_date': end_date
        }
    
    @staticmethod
    def get_rent_collection_report(start_date, end_date, shop_id=None):
        """
        获取租金收缴情况报表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            shop_id: 店铺ID，None表示全部店铺
            
        Returns:
            dict: 租金收缴情况
        """
        if shop_id:
            shop_qs = Shop.objects.filter(id=shop_id, is_deleted=False)
        else:
            shop_qs = Shop.objects.filter(is_deleted=False)

        shops = list(shop_qs)
        shop_ids = [shop.id for shop in shops]

        offline_agg_summary = None
        agg_paid_amount = Decimal('0')
        agg_rent_paid_amount = Decimal('0')
        agg_map = {}
        if getattr(settings, "ENABLE_OFFLINE_AGG", False) and shop_ids:
            agg_rows = DailyFinanceAgg.objects.filter(
                shop_id__in=shop_ids,
                agg_date__range=[start_date, end_date],
            ).values('shop_id').annotate(
                paid_amount=Sum('paid_amount'),
                rent_paid_amount=Sum('rent_paid_amount'),
            )

            for row in agg_rows:
                agg_paid_amount += row['paid_amount'] or Decimal('0')
                agg_rent_paid_amount += row['rent_paid_amount'] or Decimal('0')
                agg_map[row['shop_id']] = {
                    'paid_amount': row['paid_amount'] or Decimal('0'),
                    'rent_paid_amount': row['rent_paid_amount'] or Decimal('0'),
                }

            offline_agg_summary = {
                'paid_amount': agg_paid_amount,
                'rent_paid_amount': agg_rent_paid_amount,
                'source': 'daily_finance_agg'
            }

        report_data = []
        total_rent_due = Decimal('0')
        total_rent_collected = Decimal('0')

        for shop in shops:
            contracts = Contract.objects.filter(
                shop=shop,
                status__in=[Contract.Status.ACTIVE, Contract.Status.EXPIRED],
                end_date__gte=start_date
            )

            for contract in contracts:
                contract_start = max(contract.start_date, start_date)
                contract_end = min(contract.end_date, end_date)
                
                months = (contract_end.year - contract_start.year) * 12 + (contract_end.month - contract_start.month) + 1
                rent_due = contract.monthly_rent * months

                finance_records = FinanceRecord.objects.filter(
                    contract=contract,
                    fee_type=FinanceRecord.FeeType.RENT,
                    status=FinanceRecord.Status.PAID,
                    paid_at__date__range=[start_date, end_date]
                )
                rent_collected = sum(record.amount for record in finance_records)

                rent_outstanding = rent_due - rent_collected

                shop_agg = agg_map.get(shop.id)
                report_data.append({
                    'shop_name': shop.name,
                    'contract_id': contract.id,
                    'start_date': contract_start,
                    'end_date': contract_end,
                    'monthly_rent': contract.monthly_rent,
                    'months': months,
                    'rent_due': rent_due,
                    'rent_collected': rent_collected,
                    'rent_outstanding': rent_outstanding,
                    'collection_rate': (rent_collected / rent_due * 100) if rent_due > 0 else 0,
                    'aggregated_shop_paid': shop_agg['paid_amount'] if shop_agg else None,
                    'aggregated_shop_rent_paid': shop_agg['rent_paid_amount'] if shop_agg else None,
                })

                total_rent_due += rent_due
                total_rent_collected += rent_collected

        result = {
            'report_data': report_data,
            'total_rent_due': total_rent_due,
            'total_rent_collected': agg_rent_paid_amount if offline_agg_summary else total_rent_collected,
            'total_rent_outstanding': total_rent_due - (agg_rent_paid_amount if offline_agg_summary else total_rent_collected),
            'total_collection_rate': (
                (agg_rent_paid_amount if offline_agg_summary else total_rent_collected)
                / total_rent_due * 100
            ) if total_rent_due > 0 else 0,
            'start_date': start_date,
            'end_date': end_date,
        }

        if offline_agg_summary:
            result['offline_agg_summary'] = offline_agg_summary

        return result
    
    @staticmethod
    def get_business_type_analysis(start_date, end_date):
        """
        获取业态分布分析报表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: 业态分布分析
        """
        # 获取所有店铺
        shops = Shop.objects.filter(is_deleted=False)
        
        # 按业态分组
        business_type_data = {}
        total_shops = len(shops)
        total_area = sum(shop.area for shop in shops)
        total_foot_traffic = 0
        total_sales = Decimal('0')
        
        for shop in shops:
            # 获取业态
            business_type = shop.get_business_type_display()
            
            # 获取运营数据
            manual_datas = ManualOperationData.objects.filter(
                shop=shop,
                data_date__range=[start_date, end_date]
            )
            
            # 汇总数据
            foot_traffic = sum(data.foot_traffic or 0 for data in manual_datas)
            sales = sum(data.sales_amount or Decimal('0') for data in manual_datas)
            
            if business_type not in business_type_data:
                business_type_data[business_type] = {
                    'shop_count': 0,
                    'area': Decimal('0'),
                    'foot_traffic': 0,
                    'sales': Decimal('0')
                }
            
            business_type_data[business_type]['shop_count'] += 1
            business_type_data[business_type]['area'] += shop.area
            business_type_data[business_type]['foot_traffic'] += foot_traffic
            business_type_data[business_type]['sales'] += sales
            
            # 累加总计
            total_foot_traffic += foot_traffic
            total_sales += sales
        
        # 计算百分比
        for business_type, data in business_type_data.items():
            data['shop_percentage'] = (data['shop_count'] / total_shops * 100) if total_shops > 0 else 0
            data['area_percentage'] = (data['area'] / total_area * 100) if total_area > 0 else 0
        
        return {
            'business_type_data': business_type_data,
            'total_shops': total_shops,
            'total_area': total_area,
            'total_foot_traffic': total_foot_traffic,
            'total_sales': total_sales,
            'start_date': start_date,
            'end_date': end_date
        }
    
    @staticmethod
    def get_operation_efficiency_report(start_date, end_date):
        """
        获取事务处理效率报表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: 事务处理效率
        """
        # 这里可以根据实际业务逻辑实现
        # 例如：合同处理时间、报修处理时间等
        
        # 暂时返回模拟数据
        report_data = [
            {
                'transaction_type': '合同创建',
                'total_transactions': 15,
                'avg_processing_time': 2.5,
                'min_processing_time': 1.0,
                'max_processing_time': 5.0
            },
            {
                'transaction_type': '合同激活',
                'total_transactions': 12,
                'avg_processing_time': 1.8,
                'min_processing_time': 0.5,
                'max_processing_time': 4.0
            },
            {
                'transaction_type': '合同终止',
                'total_transactions': 3,
                'avg_processing_time': 3.2,
                'min_processing_time': 1.5,
                'max_processing_time': 6.0
            },
            {
                'transaction_type': '店铺创建',
                'total_transactions': 8,
                'avg_processing_time': 2.1,
                'min_processing_time': 0.8,
                'max_processing_time': 4.5
            }
        ]
        
        return {
            'report_data': report_data,
            'start_date': start_date,
            'end_date': end_date
        }
    
    @staticmethod
    def export_to_excel(data, report_type):
        """
        导出数据到Excel格式
        
        Args:
            data: 报表数据
            report_type: 报表类型
            
        Returns:
            BytesIO: Excel文件内容
        """
        if report_type == 'shop_operation':
            return ReportService._export_shop_operation_excel(data)
        elif report_type == 'rent_collection':
            return ReportService._export_rent_collection_excel(data)
        elif report_type == 'business_type':
            return ReportService._export_business_type_excel(data)
        elif report_type == 'operation_efficiency':
            return ReportService._export_operation_efficiency_excel(data)
        else:
            raise ValueError(f"不支持的报表类型: {report_type}")
    
    @staticmethod
    def _export_shop_operation_excel(data):
        """
        导出店铺运营数据到Excel
        """
        df = pd.DataFrame(data['summary_data'])
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='运营汇总', index=False)
        
        output.seek(0)
        return output
    
    @staticmethod
    def _export_rent_collection_excel(data):
        """
        导出租金收缴情况到Excel
        """
        df = pd.DataFrame(data['report_data'])
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='租金收缴', index=False)
        
        output.seek(0)
        return output
    
    @staticmethod
    def _export_business_type_excel(data):
        """
        导出业态分布分析到Excel
        """
        df = pd.DataFrame.from_dict(data['business_type_data'], orient='index')
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='业态分析')
        
        output.seek(0)
        return output
    
    @staticmethod
    def _export_operation_efficiency_excel(data):
        """
        导出事务处理效率到Excel
        """
        df = pd.DataFrame(data['report_data'])
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='效率分析', index=False)
        
        output.seek(0)
        return output
    
    @staticmethod
    def export_to_csv(data, report_type):
        """
        导出数据到CSV格式
        
        Args:
            data: 报表数据
            report_type: 报表类型
            
        Returns:
            StringIO: CSV文件内容
        """
        if report_type == 'shop_operation':
            df = pd.DataFrame(data['summary_data'])
        elif report_type == 'rent_collection':
            df = pd.DataFrame(data['report_data'])
        elif report_type == 'business_type':
            df = pd.DataFrame.from_dict(data['business_type_data'], orient='index')
        elif report_type == 'operation_efficiency':
            df = pd.DataFrame(data['report_data'])
        else:
            raise ValueError(f"不支持的报表类型: {report_type}")
        
        # 创建CSV文件
        output = StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        
        output.seek(0)
        return output
    
    @staticmethod
    def export_to_pdf(data, report_type):
        """
        导出数据到PDF格式
        
        Args:
            data: 报表数据
            report_type: 报表类型
            
        Returns:
            BytesIO: PDF文件内容
        """
        # 这里可以使用pdfkit或其他库实现PDF导出
        # 暂时返回模拟数据
        output = BytesIO()
        output.write(b'%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>endobj\n4 0 obj<< /Length 55 >>stream\nBT /F1 24 Tf 100 700 Td (PDF Export Not Implemented Yet) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000101 00000 n \n0000000179 00000 n \ntrailer<< /Size 5 /Root 1 0 R >>\nstartxref\n280\n%%EOF')
        output.seek(0)
        return output
