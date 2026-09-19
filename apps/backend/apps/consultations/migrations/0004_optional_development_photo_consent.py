from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_legaldocument_attachment_user_deleted_at_and_more"), ("consultations", "0003_consultationservice_expert_appointment_and_more")]
    operations = [
        migrations.AlterField(model_name="consultationphoto", name="consent_accepted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(model_name="consultationphoto", name="consent_document", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="consultation_photos", to="accounts.legaldocument")),
    ]
