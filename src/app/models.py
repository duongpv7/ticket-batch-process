from django.db import models


class BatchProgress(models.Model):
    BATCH_PROGESS_STATE_INIT = "INIT"
    BATCH_PROGESS_STATE_RUNNING = "RUNNING"
    BATCH_PROGESS_STATE_FINISHED = "FINISHED"
    BATCH_PROGESS_STATE_ERROR = "ERROR"

    batch_key = models.CharField(max_length=255)
    last_value = models.BigIntegerField()
    state = models.CharField(max_length=32)
    error = models.TextField()


class Ticket(models.Model):
    token = models.UUIDField(null=True, default=None)
