from django.db import models
from django.contrib.auth.models import User

class SalesData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='sales_data/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class SharedChart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file_id = models.IntegerField()
    chart_type = models.CharField(max_length=50)
    unique_id = models.CharField(max_length=8, unique=True)  # Ensure this is unique

    def __str__(self):
        return f"{self.chart_type} shared by {self.user.username}"
    