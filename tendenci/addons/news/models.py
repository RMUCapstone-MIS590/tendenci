import uuid
from datetime import datetime
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes import generic

from tagging.fields import TagField
from tendenci.core.base.fields import SlugField
from timezones.fields import TimeZoneField
from tendenci.core.perms.models import TendenciBaseModel
from tendenci.core.perms.object_perms import ObjectPermission
from tendenci.core.categories.models import CategoryItem
from tendenci.addons.news.managers import NewsManager
from tinymce import models as tinymce_models
from tendenci.core.meta.models import Meta as MetaTags
from tendenci.addons.news.module_meta import NewsMeta
from tendenci.apps.entities.models import Entity

class News(TendenciBaseModel):
    guid = models.CharField(max_length=40)
    slug = SlugField(_('URL Path'), unique=True)
    timezone = TimeZoneField(_('Time Zone'))
    headline = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    body = tinymce_models.HTMLField()
    source = models.CharField(max_length=300, blank=True)
    first_name = models.CharField(_('First Name'), max_length=100, blank=True)
    last_name = models.CharField(_('Last Name'), max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    fax = models.CharField(max_length=50, blank=True)
    email = models.CharField(max_length=120, blank=True)
    website = models.CharField(max_length=300, blank=True)
    release_dt = models.DateTimeField(_('Release Date/Time'), null=True, blank=True)
    syndicate = models.BooleanField(_('Include in RSS feed'), default=True)
    design_notes = models.TextField(_('Design Notes'), blank=True)
    tags = TagField(blank=True)

    #for podcast feeds
    enclosure_url = models.CharField(_('Enclosure URL'), max_length=500, blank=True) # for podcast feeds
    enclosure_type = models.CharField(_('Enclosure Type'),max_length=120, blank=True) # for podcast feeds
    enclosure_length = models.IntegerField(_('Enclosure Length'), default=0) # for podcast feeds

    use_auto_timestamp = models.BooleanField(_('Auto Timestamp'))
    entity = models.ForeignKey(Entity,null=True)
        
    # html-meta tags
    meta = models.OneToOneField(MetaTags, null=True)
    
    categories = generic.GenericRelation(CategoryItem,
                                          object_id_field="object_id",
                                          content_type_field="content_type")
    
    perms = generic.GenericRelation(ObjectPermission,
                                          object_id_field="object_id",
                                          content_type_field="content_type")

    objects = NewsManager()

    class Meta:
        permissions = (("view_news","Can view news"),)
        verbose_name_plural = "News"

    def get_meta(self, name):
        """
        This method is standard across all models that are
        related to the Meta model.  Used to generate dynamic
        meta information niche to this model.
        """
        return NewsMeta().get_meta(self, name)

    @models.permalink
    def get_absolute_url(self):
        return ("news.detail", [self.slug])

    def __unicode__(self):
        return self.headline

    def save(self, *args, **kwargs):
        if not self.id:
            self.guid = str(uuid.uuid1())
        super(News, self).save(*args, **kwargs)

    @property
    def category_set(self):
        items = {}
        for cat in self.categories.select_related('category__name', 'parent__name'):
            if cat.category:
                items["category"] = cat.category
            elif cat.parent:
                items["sub_category"] = cat.parent
        return items