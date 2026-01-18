# 数据备份与恢复 - 快速开始指南

## 🚀 5 分钟快速入门

### 1️⃣ 访问备份管理中心（1 分钟）

```
http://127.0.0.1:8000/backup/
```

如果显示 404，确保：
- 已登录为管理员
- Django 开发服务器正在运行

### 2️⃣ 创建第一个备份（2 分钟）

#### 方式 A：Web 界面创建
1. 进入 `/backup/` 页面
2. 点击蓝色"创建备份"按钮
3. 选择"全量备份"
4. 保持所有数据类型都选中
5. 点击"开始备份"
6. 等待完成（通常 1-2 分钟）

#### 方式 B：命令行创建
```bash
cd D:\Python经典程序合集\商场店铺智能运营管理系统设计与实现

# 执行全量备份
.venv\Scripts\python.exe manage.py backup_database

# 或指定备份类型
.venv\Scripts\python.exe manage.py backup_database --type=FULL
```

### 3️⃣ 查看备份（1 分钟）

1. 返回 `/backup/` 页面
2. 看到新创建的备份在列表顶部
3. 点击备份名称查看详情
4. 查看文件大小、创建时间等信息

### 4️⃣ 下载备份文件（1 分钟）

在备份详情页面：
1. 点击绿色"下载备份文件"按钮
2. 备份文件将保存到本地（建议保存到安全位置）
3. 文件格式：`backup_full_YYYYMMDD_HHMMSS.tar.gz`

---

## ⚙️ 常用操作

### 创建不同类型的备份

#### 全量备份（推荐每周执行一次）
```bash
.venv\Scripts\python.exe manage.py backup_database --type=FULL
```
特点：备份所有数据，文件较大，但恢复快速

#### 增量备份（推荐每天执行）
```bash
.venv\Scripts\python.exe manage.py backup_database --type=INCREMENTAL
```
特点：仅备份新增/修改数据，文件较小，快速完成

#### 选择性备份（备份特定数据）
```bash
# 仅备份店铺和合约数据
.venv\Scripts\python.exe manage.py backup_database \
    --type=FULL \
    --data-types=SHOP,CONTRACT
```

可选的数据类型：
- `SHOP` - 店铺信息
- `CONTRACT` - 合约数据
- `OPERATION` - 运营数据
- `FINANCE` - 财务记录
- `LOG` - 事务日志

### 恢复数据

#### ⚠️ 恢复前必读

**警告**：恢复操作会用备份文件覆盖当前数据！
- 确保当前数据已备份
- 确保要恢复的备份是正确的
- 恢复过程中系统可能不可用

#### 恢复步骤

1. 进入 `/backup/` 找到要恢复的备份
2. 点击备份名称进入详情页
3. 点击红色"恢复数据"按钮
4. 仔细阅读所有警告信息
5. 勾选确认框（两个都要勾选）
6. 点击"确认恢复"
7. 等待恢复完成（通常 2-5 分钟）
8. 恢复完成后刷新页面

### 验证备份完整性

```bash
# 方式 A：通过 Web 界面
# 进入备份详情页面，点击"验证备份"按钮

# 方式 B：通过命令行（未来功能）
# .venv\Scripts\python.exe manage.py verify_backup <backup_id>
```

验证内容：
- ✓ 文件是否存在
- ✓ 文件大小是否匹配
- ✓ SHA256 哈希值是否正确

### 清理过期备份

```bash
# 预览将删除的备份（不实际删除）
.venv\Scripts\python.exe manage.py cleanup_backups --days=30

# 实际删除 30 天前的备份
.venv\Scripts\python.exe manage.py cleanup_backups --days=30 --confirm
```

---

## 📊 监控备份状态

### 备份统计信息

访问 `/backup/` 页面可以看到：
- **总备份数** - 系统中备份总数
- **成功** - 成功完成的备份数（绿色）
- **失败** - 失败的备份数（红色）
- **总大小** - 所有备份占用的总空间

### 备份状态说明

| 状态 | 含义 | 操作 |
|------|------|------|
| ✓ 成功 (SUCCESS) | 备份完成，可恢复 | 下载、恢复、验证、删除 |
| ✗ 失败 (FAILED) | 备份过程出错 | 查看错误日志、重新备份、删除 |
| ⟳ 进行中 (RUNNING) | 备份正在进行 | 等待完成 |
| ◯ 待处理 (PENDING) | 备份待启动 | 等待启动 |

### 查看操作日志

在备份详情页面底部，可以看到所有操作的详细日志：
- 备份时间和耗时
- 文件大小和哈希值
- 恢复记录
- 所有错误信息

---

## 🔧 故障排除

### 问题 1：无法访问备份管理页面

**症状**：访问 `/backup/` 显示 403 Forbidden 或 404 Not Found

**解决**：
1. 确保以管理员身份登录
2. 确保用户是 Staff 用户或 Superuser
3. 检查 Django 服务是否正在运行

```bash
# 重启 Django 服务
.venv\Scripts\python.exe manage.py runserver
```

### 问题 2：备份失败

**症状**：备份显示 FAILED 状态

**解决**：
1. 进入备份详情页面
2. 查看"错误信息"部分
3. 常见原因：
   - 磁盘空间不足：清理 backups 目录
   - 权限不足：检查 backups 目录权限
   - 数据库连接：检查数据库服务

```bash
# 检查备份目录空间
dir backups

# 修改目录权限（Windows）
icacls backups /grant:r "%username%":(OI)(CI)F
```

### 问题 3：恢复出错

**症状**：恢复过程中出现错误

**解决**：
1. 检查备份文件是否损坏（使用"验证备份"）
2. 从其他备份点恢复
3. 查看详情页面的操作日志

### 问题 4：备份文件很大

**症状**：备份文件大小超过 1 GB

**解决**：
1. 使用增量备份替代全量备份
2. 只备份需要的数据类型
3. 考虑定期删除历史数据

```bash
# 仅备份关键数据
.venv\Scripts\python.exe manage.py backup_database \
    --data-types=SHOP,CONTRACT,FINANCE
```

---

## 📋 最佳实践

### 备份计划

| 频率 | 类型 | 时间 | 保留期 |
|------|------|------|--------|
| **每天** | 增量 | 凌晨 2 点 | 7 天 |
| **每周** | 全量 | 周一凌晨 | 4 周 |
| **每月** | 全量 | 月初 | 1 年 |

### 备份命令脚本

创建 `backup_schedule.bat`（Windows）：

```batch
@echo off
cd D:\Python经典程序合集\商场店铺智能运营管理系统设计与实现

REM 每天凌晨 2 点自动运行的增量备份
.venv\Scripts\python.exe manage.py backup_database --type=INCREMENTAL --description="自动增量备份"

REM 周一 3 点清理 7 天前的备份
.venv\Scripts\python.exe manage.py cleanup_backups --days=7 --confirm
```

创建 `backup_schedule.sh`（Linux）：

```bash
#!/bin/bash
cd /var/www/store_management

# 每天凌晨 2 点增量备份
python manage.py backup_database --type=INCREMENTAL

# 周一 3 点清理旧备份
python manage.py cleanup_backups --days=7 --confirm
```

### 安全备份流程

1. **创建备份** - 执行备份命令
2. **验证备份** - 使用"验证备份"功能检查
3. **下载备份** - 将备份下载到本地
4. **异地保存** - 将备份存储到外部硬盘或云存储
5. **定期测试** - 定期从备份恢复以验证有效性

---

## 🎯 下一步

### 配置定时自动备份

使用 Windows 任务计划程序或 crontab：

#### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器（每天凌晨 2 点）
4. 设置操作：
   ```
   程序: D:\...\\.venv\Scripts\python.exe
   参数: manage.py backup_database --type=INCREMENTAL
   ```

#### Linux crontab

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨 2 点备份）
0 2 * * * cd /var/www/store_management && python manage.py backup_database --type=INCREMENTAL
```

### 配置远程备份存储（未来）

计划支持的远程存储：
- AWS S3
- 阿里云 OSS
- 其他云存储服务

### 启用备份文件加密（未来）

```python
# 在 settings.py 中启用
BACKUP_ENCRYPTION = True  # 当前值为 False
```

---

## 📞 获取帮助

### 文档资源

- **完整功能指南**：BACKUP_FEATURE_GUIDE.md
- **实现总结**：BACKUP_IMPLEMENTATION_SUMMARY.md
- **验证清单**：BACKUP_VERIFICATION_CHECKLIST.md

### 常见问题

查看备份详情页面的操作日志部分，可以找到：
- ✓ 备份成功的详细信息
- ✓ 失败的错误原因
- ✓ 恢复过程的统计数据

### 管理后台

访问 `/admin/backup/` 可以：
- 查看所有备份记录
- 按状态和日期筛选
- 查看详细的备份和恢复日志

---

## ✅ 快速检查清单

在使用备份功能前，请确认：

- [ ] 已登录为管理员
- [ ] Django 服务正在运行
- [ ] 备份目录（backups/）存在且有写入权限
- [ ] 数据库连接正常
- [ ] 磁盘空间充足（至少 50 GB）

---

**祝您使用愉快！🎉**

任何问题，请查看上述文档或联系系统管理员。

