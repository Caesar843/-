from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_management', '0006_shop_binding_request_review_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='shopbindingrequest',
            name='requested_shop_id',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='店铺编号'),
        ),
        migrations.AddField(
            model_name='shopbindingrequest',
            name='identity_type',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='绑定身份'),
        ),
        migrations.AddField(
            model_name='shopbindingrequest',
            name='mall_name',
            field=models.CharField(blank=True, max_length=120, null=True, verbose_name='所在商场/园区/区域'),
        ),
        migrations.AddField(
            model_name='shopbindingrequest',
            name='industry_category',
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name='行业类目'),
        ),
        migrations.AddField(
            model_name='shopbindingrequest',
            name='address',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='店铺地址'),
        ),
        migrations.AddField(
            model_name='shopbindingrequest',
            name='contact_name',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='联系人姓名'),
        ),
        migrations.AddField(
            model_name='shopbindingrequest',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='联系邮箱'),
        ),
        migrations.AddField(
            model_name='shopbindingrequest',
            name='role_requested',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='期望角色'),
        ),
        migrations.AddField(
            model_name='shopbindingrequest',
            name='authorization_note',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='授权说明'),
        ),
    ]
