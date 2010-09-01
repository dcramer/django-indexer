from django.db import models

from uuidfield.fields import UUIDField

from indexer.manager import *

__all__ = ('Index',)

class Index(models.Model):
    id          = UUIDField(auto=True, primary_key=True)
    app_label   = models.CharField(max_length=32)
    module_name = models.CharField(max_length=32)
    column      = models.CharField(max_length=32)
    value       = models.CharField(max_length=128)
    object_id   = models.CharField(max_length=32)
    
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