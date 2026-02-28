from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_management', '0005_shop_binding_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='shopbindingrequest',
            name='review_reason',
            field=models.TextField(blank=True, null=True, verbose_name='Review reason'),
        ),
    ]
