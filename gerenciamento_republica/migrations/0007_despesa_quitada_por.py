import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_despesa_controle_de_pagamento'),
    ]

    operations = [
        migrations.AddField(
            model_name='despesa',
            name='quitada_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='despesas_quitadas',
                to='core.morador',
            ),
        ),
    ]
