# Generated by Django 3.0.3 on 2020-03-07 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_coupon_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coupon',
            name='code',
            field=models.CharField(default=0, max_length=15),
        ),
    ]
