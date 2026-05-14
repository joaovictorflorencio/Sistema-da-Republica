from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            'core',
            '0005_pagamentodivisao_remove_divisaodespesa_quitado_and_more',
        ),
    ]

    operations = [
        migrations.AddField(
            model_name='despesa',
            name='comprovante_pagamento',
            field=models.FileField(blank=True, null=True, upload_to='comprovantes/'),
        ),
        migrations.AddField(
            model_name='despesa',
            name='data_pagamento',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='despesa',
            name='data_vencimento',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='despesa',
            name='status_pagamento',
            field=models.CharField(
                choices=[('PENDENTE', 'Pendente'), ('PAGA', 'Paga')],
                default='PENDENTE',
                max_length=20,
            ),
        ),
    ]
