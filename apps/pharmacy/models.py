from django.db import models

# Create your models here.

class Medicine(models.Model):
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, help_text="e.g. Paracetamol")
    category = models.CharField(max_length=100) # Antibiotics, Painkillers, etc.
    quantity_in_stock = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10, help_text="Alert when stock hits this level")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.quantity_in_stock} left)"

class StockTransaction(models.Model):
    """Tracks every time stock is added or removed"""
    TRANSACTION_TYPES = [('IN', 'Restock'), ('OUT', 'Dispensed'), ('ADJ', 'Adjustment')]
    
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True) # e.g. "Dispensed for Ticket #BUK-101"