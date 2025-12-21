from django.db import models
from django.conf import settings
import uuid
from decimal import Decimal


class Game(models.Model):
    GAME_TYPES = (
        ('DICE', 'Dice'),
        ('ROULETTE', 'Roulette'),
        ('BLACKJACK', 'Blackjack'),
        ('SLOTS', 'Slots'),
        ('CRASH', 'Crash'),
        ('POKER', 'Poker'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=GAME_TYPES)
    config = models.JSONField(default=dict)  # Game-specific configuration
    min_bet = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.01'))
    max_bet = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('10000.00'))
    house_edge = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.01'))
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['type', 'active']),
        ]
    
    def __str__(self):
        return self.name


class GameRound(models.Model):
    ROUND_STATES = (
        ('CREATED', 'Created'),
        ('BETTING_OPEN', 'Betting Open'),
        ('BETTING_CLOSED', 'Betting Closed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.BigAutoField(primary_key=False, editable=False)
    state = models.CharField(max_length=20, choices=ROUND_STATES, default='CREATED')
    server_seed_hash = models.CharField(max_length=64)  # SHA256 hash
    server_seed = models.CharField(max_length=64, blank=True)  # Revealed after round
    client_seed = models.CharField(max_length=64, blank=True)
    nonce = models.IntegerField(default=0)
    outcome = models.JSONField(null=True, blank=True)  # Game outcome
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['game', '-created_at']),
            models.Index(fields=['state', 'started_at']),
            models.Index(fields=['-round_number']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.game.name} - Round {self.round_number}"


class Bet(models.Model):
    BET_RESULTS = (
        ('PENDING', 'Pending'),
        ('WIN', 'Win'),
        ('LOSS', 'Loss'),
        ('PUSH', 'Push'),
        ('CANCELLED', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game_round = models.ForeignKey(GameRound, on_delete=models.CASCADE, related_name='bets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bets')
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    bet_data = models.JSONField(default=dict)  # Game-specific bet parameters
    payout = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    result = models.CharField(max_length=10, choices=BET_RESULTS, default='PENDING')
    placed_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-placed_at']),
            models.Index(fields=['game_round']),
            models.Index(fields=['result']),
        ]
        ordering = ['-placed_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.amount} - {self.result}"