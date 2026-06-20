from django.db import migrations

SIGNUP_POINTS_BONUS = 50


def top_up_existing_wallets(apps, schema_editor):
    """Top up every existing wallet to at least the signup bonus.

    Users with more than the bonus (e.g. anyone who already earned by being
    a meet attendee) keep their higher balance — we only raise the floor."""
    PointsWallet = apps.get_model('api', 'PointsWallet')
    PointsWallet.objects.filter(balance__lt=SIGNUP_POINTS_BONUS).update(
        balance=SIGNUP_POINTS_BONUS,
    )


def noop_reverse(apps, schema_editor):
    """No reverse — we don't know what each user's original balance was."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_seenpost_seenquestion_question_answerer_and_more'),
    ]

    operations = [
        migrations.RunPython(top_up_existing_wallets, noop_reverse),
    ]
