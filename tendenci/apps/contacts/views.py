from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.mail.message import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser

from tendenci.apps.base.http import Http403
from tendenci.apps.site_settings.utils import get_setting
from tendenci.apps.contacts.models import Contact, Address, Phone, Email, URL
from tendenci.apps.contacts.forms import ContactForm, SubmitContactForm
from tendenci.apps.contacts.utils import listed_in_email_block
from tendenci.apps.perms.object_perms import ObjectPermission
from tendenci.apps.perms.utils import has_perm, has_view_perm, get_query_filters, get_notice_recipients
from tendenci.apps.event_logs.models import EventLog


try: from tendenci.apps.notification import models as notification
except: notification = None

@login_required
def details(request, id=None, template_name="contacts/view.html"):
    if not id: return HttpResponseRedirect(reverse('contacts'))
    contact = get_object_or_404(Contact, pk=id)
    
    if has_view_perm(request.user,'contacts.view_contact',contact):
        return render_to_response(template_name, {'contact': contact}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

def search(request, template_name="contacts/search.html"):
    if request.user.is_anonymous():
        raise Http403
    if not has_perm(request.user,'contacts.view_contact'):
        raise Http403

    query = request.GET.get('q', None)
    if get_setting('site', 'global', 'searchindex') and query:
        contacts = Contact.objects.search(query, user=request.user)
    else:
        filters = get_query_filters(request.user, 'contacts.view_contact')
        contacts = Contact.objects.filter(filters).distinct()
        if not request.user.is_anonymous():
            contacts = contacts.select_related()

    contacts = contacts.order_by('-create_dt')

    return render_to_response(template_name, {'contacts':contacts},
        context_instance=RequestContext(request))


def search_redirect(request):
    return HttpResponseRedirect(reverse('contacts'))

@login_required
def print_view(request, id, template_name="contacts/print-view.html"):
    contact = get_object_or_404(Contact, pk=id)

    if has_view_perm(request.user,'contacts.view_contact',contact):
        return render_to_response(template_name, {'contact': contact}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

@login_required
def add(request, form_class=ContactForm, template_name="contacts/add.html"):
    if has_perm(request.user,'contacts.add_contact'):

        if request.method == "POST":
            form = form_class(request.POST)
            if form.is_valid():           
                contact = form.save(commit=False)
                # set up the user information
                contact.creator = request.user
                contact.creator_username = request.user.username
                contact.owner = request.user
                contact.owner_username = request.user.username
                contact.allow_anonymous_view = False
                contact.save()

                ObjectPermission.objects.assign(contact.creator, contact) 
                
                return HttpResponseRedirect(reverse('contact', args=[contact.pk]))
        else:
            form = form_class()
            print form_class()
           
        return render_to_response(template_name, {'form':form}, 
            context_instance=RequestContext(request))
    else:
        raise Http403
    
@login_required
def delete(request, id, template_name="contacts/delete.html"):
    contact = get_object_or_404(Contact, pk=id)

    if has_perm(request.user,'contacts.delete_contact'):   
        if request.method == "POST":
            contact.delete()
            return HttpResponseRedirect(reverse('contact.search'))
    
        return render_to_response(template_name, {'contact': contact}, 
            context_instance=RequestContext(request))
    else:
        raise Http403

def index(request, form_class=SubmitContactForm, template_name="form.html"):

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email', None)
            first_name = form.cleaned_data.get('first_name', None)
            last_name = form.cleaned_data.get('last_name', None)
            
            if listed_in_email_block(email):
                # listed in the email blocks - it's a spam email we want to block
                # log the spam
                EventLog.objects.log()
                
                # redirect normally so they don't suspect
                return HttpResponseRedirect(reverse('form.confirmation'))
            
            address = form.cleaned_data.get('address', None)
            city = form.cleaned_data.get('city', None)
            state = form.cleaned_data.get('state', None)
            zipcode = form.cleaned_data.get('zipcode', None)
            country = form.cleaned_data.get('country', None)
            phone = form.cleaned_data.get('phone', None)
            
            url = form.cleaned_data.get('url', None)
            message = form.cleaned_data.get('message', None)

            contact_kwargs = {
                'first_name': first_name,
                'last_name': last_name,
                'message': message,
            } 
            contact = Contact(**contact_kwargs)
            contact.creator_id = 1 # TODO: decide if we should use tendenci base model
            contact.owner_id = 1 # TODO: decide if we should use tendenci base model
            contact.allow_anonymous_view = False
            contact.save()

            if address or city or state or zipcode or country:
                address_kwargs = {
                    'address': address,
                    'city': city,
                    'state': state,
                    'zipcode': zipcode,
                    'country': country,
                }
                obj_address = Address(**address_kwargs)
                obj_address.save() # saves object
                contact.addresses.add(obj_address) # saves relationship

            if phone:
                obj_phone = Phone(number=phone)
                obj_phone.save() # saves object
                contact.phones.add(obj_phone) # saves relationship

            if email:
                obj_email = Email(email=email)
                obj_email.save() # saves object
                contact.emails.add(obj_email) # saves relationship

            if url:
                obj_url = URL(url=url)
                obj_url.save() # saves object
                contact.urls.add(obj_url) # saves relationship

            site_name = get_setting('site', 'global', 'sitedisplayname')
            message_link = get_setting('site', 'global', 'siteurl')

            # send notification to administrators
            # get admin notice recipients
            recipients = get_notice_recipients('module', 'contacts', 'contactrecipients')
            if recipients:
                if notification:
                    extra_context = {
                    'reply_to': email,
                    'contact':contact,
                    'first_name':first_name,
                    'last_name':last_name,
                    'address':address,
                    'city':city,
                    'state':state,
                    'zipcode':zipcode,
                    'country':country,
                    'phone':phone,
                    'email':email,
                    'url':url,
                    'message':message,
                    'message_link':message_link,
                    'site_name':site_name,
                    }
                    notification.send_emails(recipients,'contact_submitted', extra_context)

            try: user = User.objects.filter(email=email)[0]
            except: user = None

            EventLog.objects.log(instance=contact)

            return HttpResponseRedirect(reverse('form.confirmation'))
        else:
            return render_to_response(template_name, {'form': form}, 
                context_instance=RequestContext(request))

    form = form_class()
    return render_to_response(template_name, {'form': form}, 
        context_instance=RequestContext(request))

def confirmation(request, form_class=SubmitContactForm, template_name="form-confirmation.html"):
    return render_to_response(template_name, context_instance=RequestContext(request))