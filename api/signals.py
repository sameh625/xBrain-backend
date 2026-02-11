"""
Django Signals for Explaino API

Handles automatic creation of related models
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, PointsWallet


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Automatically create a PointsWallet when a new User is created
    
    This ensures every user has a wallet from the moment they sign up.
    Initial balance is set to 0 (can be configured later).
    """
    if created:
        PointsWallet.objects.create(user=instance, balance=0)
