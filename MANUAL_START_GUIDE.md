# 手动启动项目指南

## 1. 检查项目结构

确保项目目录包含以下关键文件：
- `manage.py` - Django管理脚本
- `config/settings.py` - 项目配置文件
- `.venv/` - 虚拟环境目录

## 2. 手动激活虚拟环境

**Windows系统：**

1. 打开命令提示符（CMD）或PowerShell
2. 切换到项目目录：
   ```bash
   cd /d "d:\Python经典程序合集\商场店铺智能运营管理系统设计与实现"
   ```
3. 激活虚拟环境：
   ```bash
   .venv\Scripts\activate
   ```

**激活成功的标志：**
命令提示符前会显示 `(.venv)` 前缀

## 3. 检查Django安装

在激活的虚拟环境中运行：
```bash
python -m django --version
```

如果显示Django版本号（如 `6.0.1`），则安装成功。

## 4. 手动启动开发服务器

```bash
python manage.py runserver 8001
```

**预期输出：**
```
Performing system checks...

System check identified no issues (0 silenced).
January 15, 2026 - 13:36:51
Django version 6.0.1, using settings 'config.settings'
Starting development server at http://127.0.0.1:8001/
Quit the server with CTRL-BREAK.
```

## 5. 访问项目

打开浏览器，访问：
```
http://127.0.0.1:8001/
```

## 6. 常见问题排查

### 问题1：端口被占用

**解决方案：**
1. 检查端口占用情况：
   ```bash
   netstat -ano | findstr :8001
   ```
2. 终止占用端口的进程：
   ```bash
   taskkill /PID <进程ID> /F
   ```
3. 或使用其他端口：
   ```bash
   python manage.py runserver 8002
   ```

### 问题2：Django未安装

**解决方案：**
```bash
pip install django
```

### 问题3：缺少依赖包

**解决方案：**
如果项目有 `requirements.txt` 文件：
```bash
pip install -r requirements.txt
```

否则安装Django：
```bash
pip install django
```

### 问题4：数据库迁移问题

**解决方案：**
```bash
python manage.py migrate
```

## 7. 强制停止服务器

如果服务器无法正常停止，使用：
```bash
taskkill /F /IM python.exe
```

## 8. 项目配置检查

### 检查 `config/settings.py` 中的关键配置：

- `DEBUG = True` （开发环境应为True）
- `ALLOWED_HOSTS = ['*']` （开发环境可以使用通配符）
- `INSTALLED_APPS` 包含所有必要的应用

### 检查 `config/urls.py`：

确保包含正确的URL路由配置。

## 9. 项目功能验证

### 检查报表模块是否正确配置：

1. 报表应用已添加到 `INSTALLED_APPS`
2. 报表URL已正确配置
3. 模板文件存在于 `templates/reports/` 目录

## 10. 联系支持

如果按照上述步骤仍然无法启动项目，请提供：
1. 完整的错误信息
2. 命令提示符的完整输出
3. 项目目录结构
4. 虚拟环境激活状态

---

**注意：** 本指南适用于开发环境，生产环境部署需要更严格的配置。