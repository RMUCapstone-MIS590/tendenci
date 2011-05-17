from datetime import datetime
from operator import or_, and_

from django.template import Library, TemplateSyntaxError, Variable
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AnonymousUser

from base.template_tags import ListNode, parse_tag_kwargs
from stories.models import Story

register = Library()


@register.inclusion_tag("stories/options.html", takes_context=True)
def stories_options(context, user, story):
    context.update({
        "opt_object": story,
        "user": user,
    })
    return context


@register.inclusion_tag("stories/nav.html", takes_context=True)
def stories_nav(context, user, story=None):
    context.update({
        "nav_object": story,
        "user": user,
    })
    return context


@register.inclusion_tag("stories/search-form.html", takes_context=True)
def stories_search(context):
    return context


class ListStoriesNode(ListNode):
    model = Story

    def __init__(self, context_var, *args, **kwargs):
        self.context_var = context_var
        self.kwargs = kwargs

        if not self.model:
            raise AttributeError(_('Model attribute must be set'))
        if not issubclass(self.model, models.Model):
            raise AttributeError(_('Model attribute must derive from Model'))
        if not hasattr(self.model.objects, 'search'):
            raise AttributeError(_('Model.objects does not have a search method'))

    def render(self, context):
        tags = u''
        query = u''
        user = AnonymousUser()
        limit = 3
        order = u''
        randomize = False

        if 'random' in self.kwargs:
            randomize = bool(self.kwargs['random'])

        if 'tags' in self.kwargs:
            try:
                tags = Variable(self.kwargs['tags'])
                tags = unicode(tags.resolve(context))
            except:
                tags = self.kwargs['tags']

            tags = tags.replace('"', '')
            tags = tags.split(',')
            
            print tags

        if 'user' in self.kwargs:
            try:
                user = Variable(self.kwargs['user'])
                user = user.resolve(context)
            except:
                user = self.kwargs['user']
        else:
            # check the context for an already existing user
            if 'user' in context:
                user = context['user']

        if 'limit' in self.kwargs:
            try:
                limit = Variable(self.kwargs['limit'])
                limit = limit.resolve(context)
            except:
                limit = self.kwargs['limit']

        limit = int(limit)

        if 'query' in self.kwargs:
            try:
                query = Variable(self.kwargs['query'])
                query = query.resolve(context)
            except:
                query = self.kwargs['query']  # context string

        if 'order' in self.kwargs:
            try:
                order = Variable(self.kwargs['order'])
                order = order.resolve(context)
            except:
                order = self.kwargs['order']

        # process tags
        for tag in tags:
            tag = tag.strip()
            query = '%s "tag:%s"' % (query, tag)

        # get the list of staff
        items = self.model.objects.search(user=user, query=query)
        objects = []

        # Custom filter for stories
        date_query = reduce(or_, [Q(end_dt__gte = datetime.now()), Q(expires=False)])
        date_query = reduce(and_, [Q(start_dt__lte = datetime.now()), date_query])
        items = items.filter(date_query)

        # if order is not specified it sorts by relevance
        if items:
            if order:
                items = items.order_by(order)

            if randomize:
                objects = [item.object for item in random.sample(items, items.count())][:limit]
            else:
                objects = [item.object for item in items[:limit]]

            context[self.context_var] = objects
        return ""

@register.tag
def list_stories(parser, token):
    """
    Example:

    {% list_stories as stories user=user limit=3 %}
    {% for story in stories %}
        {{ story.title }}
    {% endfor %}
    """
    args, kwargs = [], {}
    bits = token.split_contents()
    context_var = bits[2]

    if len(bits) < 3:
        message = "'%s' tag requires more than 3" % bits[0]
        raise TemplateSyntaxError(message)

    if bits[1] != "as":
        message = "'%s' second argument must be 'as" % bits[0]
        raise TemplateSyntaxError(message)

    kwargs = parse_tag_kwargs(bits)

    if 'order' not in kwargs:
        kwargs['order'] = '-start_dt'

    return ListStoriesNode(context_var, *args, **kwargs)
