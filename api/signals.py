from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, PointsWallet

SIGNUP_POINTS_BONUS = 50


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        PointsWallet.objects.create(user=instance, balance=SIGNUP_POINTS_BONUS)
