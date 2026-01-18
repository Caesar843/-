import os
import sys
import time

# 设置Django环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    # 导入Django
    import django
    django.setup()
    print("✅ Django初始化成功")
    
    # 导入并运行开发服务器
    from django.core.management import execute_from_command_line
    
    print("\n🚀 正在启动Django开发服务器...")
    print("访问地址: http://127.0.0.1:8001/")
    print("按 Ctrl+C 停止服务器")
    print("\n" + "="*50)
    
    # 执行runserver命令
    execute_from_command_line(['manage.py', 'runserver', '8001', '--noreload'])
    
except Exception as e:
    print(f"❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()
    input("\n按 Enter 键退出...")
