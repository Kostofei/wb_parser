# Generated by Django 5.2.3 on 2025-07-05 14:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parser', '0007_alter_item_rating_count'),
    ]

    operations = [
        migrations.RenameField(
            model_name='item',
            old_name='rating_count',
            new_name='reviews_count',
        ),
    ]
