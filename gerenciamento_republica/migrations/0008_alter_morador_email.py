from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_despesa_quitada_por'),
    ]

    operations = [
        migrations.AlterField(
            model_name='morador',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]
