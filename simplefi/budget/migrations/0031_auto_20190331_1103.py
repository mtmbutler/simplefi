# Generated by Django 2.1.7 on 2019-03-31 18:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0030_auto_20190331_1101'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='category',
            options={'ordering': ['class_field_id', 'name'], 'verbose_name_plural': 'categories'},
        ),
        migrations.RenameField(
            model_name='pattern',
            old_name='subcategory',
            new_name='category',
        ),
    ]