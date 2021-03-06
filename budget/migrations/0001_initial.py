# Generated by Django 2.1.7 on 2019-03-03 19:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, unique=True, verbose_name="Name"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Bank",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, unique=True, verbose_name="Name"),
                ),
                (
                    "date_col_name",
                    models.CharField(max_length=255, verbose_name="Date Header"),
                ),
                (
                    "amt_col_name",
                    models.CharField(max_length=255, verbose_name="Amount Header"),
                ),
                (
                    "desc_col_name",
                    models.CharField(max_length=255, verbose_name="Description Header"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        max_length=255, unique=True, verbose_name="Category"
                    ),
                ),
                (
                    "budget",
                    models.DecimalField(
                        decimal_places=2,
                        default=0.0,
                        max_digits=9,
                        verbose_name="Monthly Target",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Pattern",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "pattern",
                    models.CharField(
                        max_length=255, unique=True, verbose_name="Match Pattern"
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="budget.Category",
                        to_field="category",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Subcategory",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        max_length=255, unique=True, verbose_name="Subcategory"
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="budget.Category",
                        to_field="category",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(verbose_name="Transaction Date")),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=9, verbose_name="Amount"
                    ),
                ),
                ("description", models.TextField(verbose_name="Description")),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="budget.Account",
                        to_field="name",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="budget.Category",
                        to_field="category",
                    ),
                ),
                (
                    "subcategory",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="budget.Subcategory",
                        to_field="subcategory",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Upload",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "upload_time",
                    models.DateTimeField(auto_now_add=True, verbose_name="Uploaded"),
                ),
                ("csv", models.FileField(upload_to="csvs")),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="budget.Account",
                        to_field="name",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="transaction",
            name="upload_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="budget.Upload"
            ),
        ),
        migrations.AddField(
            model_name="pattern",
            name="subcategory",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="budget.Subcategory",
                to_field="subcategory",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="bank",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="budget.Bank"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="transaction",
            unique_together={("account", "date", "amount", "description")},
        ),
    ]
