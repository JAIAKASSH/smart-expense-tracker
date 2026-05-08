from django.db import models
from django.contrib.auth.models import User


CATEGORY_CHOICES = [
    ('Food', 'Food'),
    ('Travel', 'Travel'),
    ('Shopping', 'Shopping'),
    ('Entertainment', 'Entertainment'),
    ('Health', 'Health'),
    ('Education', 'Education'),
    ('Utilities', 'Utilities'),
    ('Other', 'Other'),
]

CATEGORY_KEYWORDS = {
    'Food': ['pizza', 'burger', 'restaurant', 'cafe', 'coffee', 'lunch', 'dinner', 'breakfast',
             'grocery', 'groceries', 'food', 'eat', 'snack', 'swiggy', 'zomato', 'dominos', 'kfc', 'mcdonalds'],
    'Travel': ['uber', 'ola', 'taxi', 'bus', 'train', 'flight', 'petrol', 'fuel', 'metro',
               'travel', 'trip', 'hotel', 'airbnb', 'cab', 'auto', 'rapido'],
    'Shopping': ['amazon', 'flipkart', 'myntra', 'clothes', 'shirt', 'shoes', 'shopping',
                 'mall', 'store', 'buy', 'purchase', 'order'],
    'Entertainment': ['netflix', 'spotify', 'movie', 'cinema', 'game', 'gaming', 'concert',
                      'show', 'theatre', 'hotstar', 'prime', 'youtube'],
    'Health': ['medicine', 'doctor', 'hospital', 'pharmacy', 'gym', 'fitness', 'health',
               'clinic', 'dental', 'medical', 'yoga'],
    'Education': ['book', 'course', 'tuition', 'school', 'college', 'udemy', 'coursera',
                  'study', 'exam', 'fee', 'stationery'],
    'Utilities': ['electricity', 'water', 'internet', 'wifi', 'phone', 'bill', 'recharge',
                  'gas', 'rent', 'maintenance', 'subscription'],
}


def predict_category(description):
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return category
    return 'Other'


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.description} - ₹{self.amount} ({self.category})"
