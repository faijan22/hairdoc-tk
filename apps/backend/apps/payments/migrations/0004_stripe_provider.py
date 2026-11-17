from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0003_square_provider")]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="provider",
            field=models.CharField(default="STRIPE", max_length=24),
        ),
        migrations.AlterField(
            model_name="webhookevent",
            name="provider",
            field=models.CharField(default="STRIPE", max_length=24),
        ),
    ]
