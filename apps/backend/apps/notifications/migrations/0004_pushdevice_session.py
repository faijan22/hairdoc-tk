from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_legaldocument_attachment_user_deleted_at_and_more"),
        ("notifications", "0003_pushdelivery_receipt_checked_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="pushdevice",
            name="session",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="push_devices",
                to="accounts.devicesession",
            ),
        ),
    ]
