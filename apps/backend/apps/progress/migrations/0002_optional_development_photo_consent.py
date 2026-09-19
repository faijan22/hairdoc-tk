from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_legaldocument_attachment_user_deleted_at_and_more"), ("progress", "0001_initial")]
    operations = [
        migrations.AlterField(model_name="progressphoto", name="consent_accepted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(model_name="progressphoto", name="consent_document", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="progress_photos", to="accounts.legaldocument")),
    ]
