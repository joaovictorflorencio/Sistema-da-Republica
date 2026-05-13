from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def migrar_divisoes_existentes(apps, schema_editor):
    DivisaoDespesa = apps.get_model('core', 'DivisaoDespesa')

    for divisao in DivisaoDespesa.objects.select_related('despesa', 'morador').all():
        if divisao.morador_id == divisao.despesa.paga_por_id:
            divisao.valor_pago = divisao.valor_devido
            divisao.status = 'QUITADO'
        elif divisao.quitado:
            divisao.valor_pago = divisao.valor_devido
            divisao.status = 'QUITADO'
        else:
            divisao.valor_pago = Decimal('0.00')
            divisao.status = 'PENDENTE'

        divisao.save(update_fields=['valor_pago', 'status'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_morador_eh_admin'),
    ]

    operations = [
        migrations.AddField(
            model_name='divisaodespesa',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDENTE', 'Pendente'),
                    ('PARCIAL', 'Parcial'),
                    ('QUITADO', 'Quitado'),
                ],
                default='PENDENTE',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='divisaodespesa',
            name='valor_pago',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.CreateModel(
            name='PagamentoDivisao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_aplicado', models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    'divisao',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='pagamentos_aplicados',
                        to='core.divisaodespesa',
                    ),
                ),
                (
                    'pagamento',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='itens',
                        to='core.pagamento',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Aplicacao de pagamento',
                'verbose_name_plural': 'Aplicacoes de pagamento',
                'ordering': ['divisao__despesa__data_despesa', 'id'],
            },
        ),
        migrations.RunPython(migrar_divisoes_existentes, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='divisaodespesa',
            name='quitado',
        ),
        migrations.AddConstraint(
            model_name='divisaodespesa',
            constraint=models.CheckConstraint(
                condition=models.Q(('valor_pago__gte', 0)),
                name='divisao_valor_pago_gte_zero',
            ),
        ),
        migrations.AddConstraint(
            model_name='pagamentodivisao',
            constraint=models.UniqueConstraint(
                fields=('pagamento', 'divisao'),
                name='unique_pagamento_divisao',
            ),
        ),
        migrations.AddConstraint(
            model_name='pagamentodivisao',
            constraint=models.CheckConstraint(
                condition=models.Q(('valor_aplicado__gt', 0)),
                name='pagamento_divisao_valor_gt_zero',
            ),
        ),
    ]
