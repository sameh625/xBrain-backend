from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, PointsWallet


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        PointsWallet.objects.create(user=instance, balance=0)
