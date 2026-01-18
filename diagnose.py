import os
import sys
import subprocess
import time

# 诊断脚本
print("=== Django项目诊断脚本 ===")

# 1. 检查Python版本
print("\n1. 检查Python版本：")
print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")

# 2. 检查项目目录
print("\n2. 检查项目目录：")
current_dir = os.getcwd()
print(f"当前目录: {current_dir}")
print(f"是否存在manage.py: {os.path.exists('manage.py')}")

# 3. 检查虚拟环境
print("\n3. 检查虚拟环境：")
venv_path = os.path.join(current_dir, '.venv')
print(f"虚拟环境路径: {venv_path}")
print(f"虚拟环境是否存在: {os.path.exists(venv_path)}")

# 4. 尝试启动服务器
print("\n4. 尝试启动服务器（后台运行）：")
try:
    # 使用subprocess启动服务器
    process = subprocess.Popen(
        [sys.executable, 'manage.py', 'runserver', '8001'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待3秒让服务器启动
    time.sleep(3)
    
    # 检查进程是否还在运行
    if process.poll() is None:
        print("✅ 服务器启动成功，进程ID:", process.pid)
        
        # 尝试获取一些输出
        stdout, stderr = process.communicate(timeout=1)
        print("\n服务器输出：")
        print(stdout[:500] + "..." if len(stdout) > 500 else stdout)
        
        if stderr:
            print("\n服务器错误：")
            print(stderr[:500] + "..." if len(stderr) > 500 else stderr)
        
        # 终止进程
        process.terminate()
        process.wait()
    else:
        print("❌ 服务器启动失败，退出码:", process.returncode)
        stdout, stderr = process.communicate()
        print("\n错误输出：")
        print(stderr)
        
except Exception as e:
    print(f"❌ 启动服务器时出错: {e}")

# 5. 检查Django设置
print("\n5. 检查Django设置：")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    import django
    django.setup()
    print("✅ Django设置加载成功")
    
    # 检查已安装的应用
    from django.conf import settings
    print(f"已安装的应用数量: {len(settings.INSTALLED_APPS)}")
    print("应用列表:", settings.INSTALLED_APPS[-5:])  # 显示最后5个应用
    
except Exception as e:
    print(f"❌ 加载Django设置时出错: {e}")

print("\n=== 诊断完成 ===")
