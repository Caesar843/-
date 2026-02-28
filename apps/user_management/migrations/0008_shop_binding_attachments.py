from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user_management', '0007_shop_binding_request_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShopBindingAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='binding_attachments/%Y/%m/', verbose_name='文件')),
                ('original_name', models.CharField(max_length=255, verbose_name='原始文件名')),
                ('mime_type', models.CharField(max_length=100, verbose_name='文件类型')),
                ('size', models.PositiveIntegerField(verbose_name='文件大小')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='上传时间')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='user_management.shopbindingrequest', verbose_name='绑定申请')),
            ],
            options={
                'verbose_name': '绑定申请附件',
                'verbose_name_plural': '绑定申请附件',
                'ordering': ['-created_at'],
            },
        ),
    ]
