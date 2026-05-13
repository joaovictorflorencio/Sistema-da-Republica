from django.db import migrations, models


def definir_admin_inicial_por_republica(apps, schema_editor):
    Morador = apps.get_model('core', 'Morador')
    Republica = apps.get_model('core', 'Republica')

    for republica in Republica.objects.all():
        if republica.moradores.filter(eh_admin=True).exists():
            continue

        primeiro_morador = republica.moradores.order_by('data_entrada', 'id').first()
        if primeiro_morador:
            primeiro_morador.eh_admin = True
            primeiro_morador.save(update_fields=['eh_admin'])


def desfazer_admin_inicial_por_republica(apps, schema_editor):
    Morador = apps.get_model('core', 'Morador')
    Morador.objects.update(eh_admin=False)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_morador_usuario'),
    ]

    operations = [
        migrations.AddField(
            model_name='morador',
            name='eh_admin',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            definir_admin_inicial_por_republica,
            reverse_code=desfazer_admin_inicial_por_republica,
        ),
    ]
