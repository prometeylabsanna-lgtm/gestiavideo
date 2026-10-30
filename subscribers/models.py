from django.db import models
from django.db.models.functions import Lower


class Subscriber(models.Model):
    email = models.EmailField("E-mail", unique=True)
    created_at = models.DateTimeField("Дата створення", auto_now_add=True)
    source = models.CharField("Джерело", max_length=64, default="coming-soon")
    lang = models.CharField("Мова", max_length=8, default="uk")
    ip_hash = models.CharField("Хеш IP", max_length=64, blank=True)
    user_agent = models.CharField("User-Agent", max_length=255, blank=True)

    class Meta:
        verbose_name = "Підписник"
        verbose_name_plural = "Підписники"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="subscribers_email_lower_uniq",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
