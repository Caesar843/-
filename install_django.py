import subprocess
import sys

print("正在安装Django...")

try:
    # 使用pip安装Django
    result = subprocess.run([
        sys.executable, '-m', 'pip', 'install', 'django'
    ], check=True, capture_output=True, text=True)
    
    print("✅ Django安装成功！")
    print("输出：")
    print(result.stdout)
    
    # 验证安装
    result = subprocess.run([
        sys.executable, '-m', 'django', '--version'
    ], check=True, capture_output=True, text=True)
    
    print(f"\n✅ Django版本：{result.stdout.strip()}")
    
except subprocess.CalledProcessError as e:
    print(f"❌ 安装失败！")
    print(f"错误输出：{e.stderr}")
    print(f"返回码：{e.returncode}")
except Exception as e:
    print(f"❌ 发生意外错误：{e}")

input("\n按 Enter 键退出...")
