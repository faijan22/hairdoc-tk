from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0002_alter_order_status_refund_unique_provider_refund_id")]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="provider_order_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="payment",
            name="provider",
            field=models.CharField(default="SQUARE", max_length=24),
        ),
        migrations.AlterField(
            model_name="webhookevent",
            name="provider",
            field=models.CharField(default="SQUARE", max_length=24),
        ),
    ]
