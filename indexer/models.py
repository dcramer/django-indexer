from django.db import models

from indexer.manager import IndexManager, BaseIndexManager

__all__ = ('BaseIndex', 'Index')

class BaseIndex(models.Model):
    object_id   = models.PositiveIntegerField()
    column      = models.CharField(max_length=32)
    value       = models.CharField(max_length=128)
    
    objects     = BaseIndexManager()
    
    _indexes     = set()
    model       = None
    
    class Meta:
        abstract = True
        unique_together = (('column', 'value', 'object_id'),)

    def __unicode__(self):
        return "%s=%s where pk is %s" % (self.column, self.value, self.object_id)

    @classmethod
    def get_model(cls):
        return cls.model

    @classmethod
    def handle_save(cls, sender, instance, created, **kwargs):
        """Handles updating this model's indexes."""
        for column, index_to in cls._indexes:
            cls.objects.save_in_index(instance, column, index_to)

    @classmethod
    def handle_delete(cls, sender, instance, **kwargs):
        """Handles updating this model's indexes."""
        cls.objects.remove_from_index(instance)

class Index(models.Model):
    app_label   = models.CharField(max_length=32)
    module_name = models.CharField(max_length=32)
    column      = models.CharField(max_length=32)
    value       = models.CharField(max_length=128)
    object_id   = models.PositiveIntegerField()
    
    objects     = IndexManager()
    
    indexes = {}
    
    class Meta:
        unique_together = (('app_label', 'module_name', 'column', 'value', 'object_id'),)

    def __unicode__(self):
        return "%s=%s in %s_%s where pk is %s" % (self.column, self.value, self.app_label, self.module_name, self.object_id)

    @classmethod
    def handle_save(cls, sender, instance, created, **kwargs):
        """Handles updating this model's indexes."""
        for column, index_to in Index.indexes[sender]:
            cls.objects.save_in_index(instance, column, index_to)

    @classmethod
    def handle_delete(cls, sender, instance, **kwargs):
        """Handles updating this model's indexes."""
        cls.objects.remove_from_index(instance)