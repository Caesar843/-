from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.contrib import messages
from apps.reports.services import ReportService
from apps.user_management.permissions import RoleRequiredMixin, ShopDataAccessMixin


class ReportView(RoleRequiredMixin, ShopDataAccessMixin, TemplateView):
    """
    报表视图
    -------------  
    处理报表生成和导出请求
    """
    
    template_name = 'reports/report_list.html'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'FINANCE', 'SHOP']
    
    def get_context_data(self, **kwargs):
        """
        获取上下文数据，根据角色过滤可用的报表类型和店铺
        """
        context = super().get_context_data(**kwargs)
        
        # 获取查询参数
        report_type = self.request.GET.get('report_type', 'shop_operation')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        shop_id = self.request.GET.get('shop_id')
        export_format = self.request.GET.get('export_format')
        
        # 处理默认日期（最近30天）
        if not start_date:
            start_date = (timezone.now() - timedelta(days=30)).date().strftime('%Y-%m-%d')
        if not end_date:
            end_date = timezone.now().date().strftime('%Y-%m-%d')
        
        # 获取用户角色
        user_role = self.request.user.profile.role.role_type
        
        # 获取店铺列表，根据角色过滤
        from apps.store.models import Shop
        if user_role == 'SHOP':
            # 店铺用户只能看到自己的店铺
            shops = Shop.objects.filter(id=self.request.user.profile.shop.id)
            # 自动设置shop_id为当前用户的店铺
            shop_id = str(self.request.user.profile.shop.id)
        else:
            # 其他角色可以看到所有店铺
            shops = Shop.objects.filter(is_deleted=False)
        
        # 根据角色设置可用的报表类型
        available_report_types = []
        if user_role in ['SUPER_ADMIN', 'MANAGEMENT']:
            # 超级管理员和管理层可以访问所有报表
            available_report_types = [
                ('shop_operation', '店铺运营报表'),
                ('rent_collection', '租金收缴报表'),
                ('business_type', '业态分析报表'),
                ('operation_efficiency', '运营效率报表')
            ]
        elif user_role in ['OPERATION', 'FINANCE']:
            # 运营专员和财务管理员可以访问部分报表
            available_report_types = [
                ('shop_operation', '店铺运营报表'),
                ('rent_collection', '租金收缴报表')
            ]
        elif user_role == 'SHOP':
            # 店铺用户只能访问自己的运营报表
            available_report_types = [
                ('shop_operation', '店铺运营报表')
            ]
        
        # 获取报表数据
        report_data = self._get_report_data(report_type, start_date, end_date, shop_id)
        
        # 添加到上下文
        context['report_type'] = report_type
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['shop_id'] = shop_id
        context['report_data'] = report_data
        context['export_formats'] = ['excel', 'csv', 'pdf']
        context['shops'] = shops
        context['available_report_types'] = available_report_types
        context['now'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return context
    
    def post(self, request, *args, **kwargs):
        """
        处理报表生成和导出请求
        """
        # 获取表单数据
        report_type = request.POST.get('report_type', 'shop_operation')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        shop_id = request.POST.get('shop_id')
        export_format = request.POST.get('export_format')
        
        if export_format:
            # 处理导出请求
            return self._export_report(report_type, start_date, end_date, shop_id, export_format)
        else:
            # 处理生成报表请求
            return redirect(f"?report_type={report_type}&start_date={start_date}&end_date={end_date}&shop_id={shop_id}")
    
    def _get_report_data(self, report_type, start_date, end_date, shop_id):
        """
        获取报表数据
        """
        # 解析日期
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # 根据报表类型获取数据
        if report_type == 'shop_operation':
            return ReportService.get_shop_operation_summary(start_date_obj, end_date_obj, shop_id)
        elif report_type == 'rent_collection':
            return ReportService.get_rent_collection_report(start_date_obj, end_date_obj, shop_id)
        elif report_type == 'business_type':
            return ReportService.get_business_type_analysis(start_date_obj, end_date_obj)
        elif report_type == 'operation_efficiency':
            return ReportService.get_operation_efficiency_report(start_date_obj, end_date_obj)
        else:
            return {}
    
    def _export_report(self, report_type, start_date, end_date, shop_id, export_format):
        """
        导出报表
        """
        # 获取报表数据
        report_data = self._get_report_data(report_type, start_date, end_date, shop_id)
        
        # 根据导出格式生成文件
        if export_format == 'excel':
            return self._export_excel(report_data, report_type)
        elif export_format == 'csv':
            return self._export_csv(report_data, report_type)
        elif export_format == 'pdf':
            return self._export_pdf(report_data, report_type)
        else:
            return HttpResponse('不支持的导出格式', status=400)
    
    def _export_excel(self, report_data, report_type):
        """
        导出Excel文件
        """
        # 生成Excel文件
        excel_file = ReportService.export_to_excel(report_data, report_type)
        
        # 设置响应头
        response = HttpResponse(excel_file.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="report_{report_type}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        
        return response
    
    def _export_csv(self, report_data, report_type):
        """
        导出CSV文件
        """
        # 生成CSV文件
        csv_file = ReportService.export_to_csv(report_data, report_type)
        
        # 设置响应头
        response = HttpResponse(csv_file.getvalue(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="report_{report_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        return response
    
    def _export_pdf(self, report_data, report_type):
        """
        导出PDF文件
        """
        # 生成PDF文件
        pdf_file = ReportService.export_to_pdf(report_data, report_type)
        
        # 设置响应头
        response = HttpResponse(pdf_file.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{report_type}_{timezone.now().strftime("%Y%m%d")}.pdf"'
        
        return response
