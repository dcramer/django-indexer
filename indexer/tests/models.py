from django.db import models

from indexer.models import BaseIndex

class IndexerObject(models.Model):
    name = models.CharField(max_length=32)

class TestIndex(BaseIndex):
    model = IndexerObject
