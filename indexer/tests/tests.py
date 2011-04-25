from django.test import TestCase

from indexer.tests.models import IndexerObject, TestIndex

class BaseIndexTestCase(TestCase):
    def setUp(self):
        # XXX: gotta ensure indexes are taken down
        TestIndex._indexes = set()
        TestIndex.objects.all().delete()
    
    def test_index_registration(self):
        TestIndex.objects.register_index('name')
        
        self.assertEquals(len(TestIndex._indexes), 1)
        self.assertEquals(list(TestIndex._indexes)[0], ('name', None))

    def test_index_signals(self):
        obj1 = IndexerObject.objects.create(name='foo')
        
        TestIndex.objects.register_index('name')
        
        self.assertEquals(TestIndex.objects.count(), 0)

        results = list(TestIndex.objects.get_for_index(name='foo'))
        
        self.assertEquals(len(results), 0)

        # Force backfill
        TestIndex.objects.create_index('name')

        self.assertEquals(TestIndex.objects.count(), 1)
        
        results = list(TestIndex.objects.get_for_index(name='foo'))
        
        self.assertEquals(len(results), 1)
        self.assertEquals(results[0], obj1)
    
        obj1.delete()
        
        self.assertEquals(TestIndex.objects.count(), 0)

        results = list(TestIndex.objects.get_for_index(name='foo'))
        
        self.assertEquals(len(results), 0)
        