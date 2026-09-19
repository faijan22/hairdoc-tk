from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("messaging", "0004_message_replies_and_deletion")]

    operations = [
        migrations.AlterField(
            model_name="realtimeticket",
            name="conversation",
            field=models.ForeignKey(
                to="messaging.conversation", on_delete=django.db.models.deletion.CASCADE,
                related_name="realtime_tickets", null=True, blank=True,
            ),
        ),
    ]
