from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("subscribers", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="subscriber",
            name="user_agent",
        ),
    ]
