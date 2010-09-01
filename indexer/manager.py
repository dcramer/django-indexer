from django.db.models.manager import Manager
from django.db import connection
from django.core.cache import cache

from indexer.utils import Proxy

import uuid

COLUMN_SEPARATOR = '__'

class LazyIndexLookup(Proxy):
    __slots__ = ('__data__', '__instance__')

    def __init__(self, model, model_class, **pairs):
        object.__setattr__(self, '__data__', (model, model_class, pairs))
        object.__setattr__(self, '__instance__', None)

    def _get_current_object(self):
        """
        Return the current object.  This is useful if you want the real object
        behind the proxy at a time for performance reasons or because you want
        to pass the object into a different context.
        """
        inst = self.__instance__
        if inst is not None:
            return inst
        model, model_class, pairs = self.__data__
        
        app_label = model_class._meta.app_label
        module_name = model_class._meta.module_name
        cache_key_base = ':'.join([app_label, module_name])

        base_qs = model.objects.filter(app_label=app_label, module_name=module_name)

        # TODO: this should just do subqueries or something, we can't
        # cache 8000000000 keys in one index
        list_of_pks = None
        for column, value in pairs.iteritems():
            cache_key = '%s:%s=%s' % (cache_key_base, column, value)
            data = cache.get(cache_key)
            if data is None:
                data = list(base_qs.filter(column=column, value=value).values('object_id'))
                data = [d['object_id'] for d in data]
                cache.set(cache_key, data)
            if list_of_pks is None:
                list_of_pks = data
            else:
                list_of_pks = [d for d in list_of_pks if d in data]
            
        qs = model_class.objects.filter(pk__in=list_of_pks)
        object.__setattr__(self, '__instance__', qs)
        return qs
    _current_object = property(_get_current_object)

class IndexManager(Manager):
    def get_for_model(self, model_class, **kwargs):
        if len(kwargs) < 1:
            raise ValueError
        
        return LazyIndexLookup(self.model, model_class, **kwargs)
    
    def register_model(self, model_class, column):
        """Registers a model and an index for it."""
        if model_class not in self.model.indexes:
            self.model.indexes[model_class] = set([column])
        else:
            self.model.indexes[model_class].add(column)
    
    def remove_from_index(self, instance):
        app_label = instance._meta.app_label
        module_name = instance._meta.module_name
        tbl = self.model._meta.db_table
        cursor = connection.cursor()
        try:
            cursor.execute('begin')
            cursor.execute('delete from `%s` WHERE `app_label` = %%s AND `module_name` = %%s AND `object_id` = %%s' % (tbl,), [app_label, module_name, instance.pk])
            cursor.execute('commit')
            # TODO: Delete each cache for instance
            # cache.delete('%s:%s:%s=%s' % (app_label, module_name, column))
        finally:
            cursor.close()
    
    def save_in_index(self, instance, column):
        """Updates an index for an instance.
        
        You may pass column as base__sub to access
        values stored deeper in the hierarchy."""

        app_label = instance._meta.app_label
        module_name = instance._meta.module_name
        tbl = self.model._meta.db_table
        value = instance
        for bit in column.split(COLUMN_SEPARATOR):
            value = value.get(bit)
        cursor = connection.cursor()
        try:
            cursor.execute('begin')
            if not value:
                cursor.execute('delete from `%s` WHERE `app_label` = %%s AND `module_name` = %%s AND `object_id` = %%s AND `column` = %%s' % (tbl,), [app_label, module_name, instance.pk, column])
            else:
                cursor.execute('insert into `%s` (`id`, `app_label`, `module_name`, `object_id`, `column`, `value`) values (%%s, %%s, %%s, %%s, %%s, %%s) on duplicate key update `value` = values(`value`)' % (tbl,), [uuid.uuid4().hex, app_label, module_name, instance.pk, column, value])
            cursor.execute('commit')
            # TODO: this needs to take the original value and wipe its cache as well
            cache.delete('%s:%s:%s=%s' % (app_label, module_name, column, value))
        finally:
            cursor.close()
    
    def create_index(self, model_class, column):
        """Creates and prepopulates an index.
        
        You may pass column as base__sub to access
        values stored deeper in the hierarchy."""
        
        # make sure the index exists
        self.register_model(model_class, column)
        app_label = model_class._meta.app_label
        module_name = model_class._meta.module_name
        column_bits = column.split(COLUMN_SEPARATOR)
        cursor = connection.cursor()
        try:
            cursor.execute('set autocommit = 1')
            for m in model_class.objects.all():
                value = m
                for bit in column_bits:
                    value = value.get(bit)
                if not value:
                    continue
                cursor.execute('insert into `%s` (`id`, `app_label`, `module_name`, `object_id`, `column`, `value`) values (%%s, %%s, %%s, %%s, %%s, %%s) on duplicate key update `value` = values(`value`)' %(self.model._meta.db_table,), [uuid.uuid4().hex, app_label, module_name, m.pk, column, value])
        finally:
            cursor.close()