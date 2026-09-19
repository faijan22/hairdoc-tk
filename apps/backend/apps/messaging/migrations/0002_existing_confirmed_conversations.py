from django.db import migrations


def create_existing_conversations(apps, schema_editor):
    Appointment = apps.get_model("consultations", "Appointment")
    Conversation = apps.get_model("messaging", "Conversation")
    ConversationMember = apps.get_model("messaging", "ConversationMember")
    for appointment in Appointment.objects.filter(status="CONFIRMED").iterator():
        conversation, _ = Conversation.objects.get_or_create(consultation_id=appointment.case_id)
        ConversationMember.objects.get_or_create(conversation_id=conversation.id, user_id=appointment.client_id, defaults={"role": "CLIENT"})
        ConversationMember.objects.get_or_create(conversation_id=conversation.id, user_id=appointment.expert_id, defaults={"role": "EXPERT"})


class Migration(migrations.Migration):
    dependencies = [("messaging", "0001_initial")]
    operations = [migrations.RunPython(create_existing_conversations, migrations.RunPython.noop)]
