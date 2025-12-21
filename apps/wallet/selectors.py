from django.db.models import Sum, Q
from .models import Wallet, WalletTransaction, Deposit, Withdrawal
from datetime import datetime, timedelta


class WalletQueries:
    """Query methods for wallet data"""
    
    @staticmethod
    def get_daily_totals(date=None):
        """Get daily totals for all wallets"""
        if date is None:
            date = datetime.now().date()
        
        start_date = datetime.combine(date, datetime.min.time())
        end_date = start_date + timedelta(days=1)
        
        # Get deposit totals
        deposit_total = Deposit.objects.filter(
            created_at__range=(start_date, end_date),
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get withdrawal totals
        withdrawal_total = Withdrawal.objects.filter(
            created_at__range=(start_date, end_date),
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get bet totals
        bet_total = WalletTransaction.objects.filter(
            created_at__range=(start_date, end_date),
            type='BET'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get win totals
        win_total = WalletTransaction.objects.filter(
            created_at__range=(start_date, end_date),
            type='WIN'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'date': date,
            'deposit_total': abs(deposit_total),
            'withdrawal_total': abs(withdrawal_total),
            'bet_total': abs(bet_total),
            'win_total': win_total,
            'net_gaming_revenue': abs(bet_total) - win_total,
        }
    
    @staticmethod
    def get_user_financial_summary(user, days=30):
        """Get financial summary for a user"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        transactions = WalletTransaction.objects.filter(
            wallet__user=user,
            created_at__range=(start_date, end_date)
        )
        
        # Calculate totals by type
        summary = transactions.values('type').annotate(
            total_amount=Sum('amount'),
            count=Sum(1)
        )
        
        result = {}
        for item in summary:
            result[item['type']] = {
                'total_amount': item['total_amount'],
                'count': item['count']
            }
        
        return result