# Copyright (C) 2012 Eduardo Robles Elvira <edulix AT wadobo DOT com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import requests

from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.conf.urls import patterns, url, include
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives, EmailMessage, send_mass_mail
from django.utils import simplejson as json
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.utils.translation import check_for_language
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404, render_to_response
from django.template.loader import render_to_string
from django.views.generic import TemplateView, ListView, CreateView, RedirectView
from django.views.generic.edit import UpdateView, FormView
from django.views.i18n import set_language as django_set_language
from django import http
from django.db import transaction

from actstream.actions import follow, unfollow, is_following
from actstream.models import (object_stream, election_stream, Action,
    user_stream, actor_stream)
from actstream.signals import action

from guardian.shortcuts import *

from haystack.query import EmptySearchQuerySet
from haystack.forms import ModelSearchForm, FacetedSearchForm
from haystack.query import SearchQuerySet
from haystack.views import SearchView as HaystackSearchView

from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora
from agora_site.agora_core.models import (Agora, Election, Profile, CastVote,
                                          Authority)

from agora_site.agora_core.backends.fnmt import fnmt_data_from_pem
from agora_site.agora_core.forms import *
from agora_site.agora_core.tasks import *
from agora_site.misc.utils import *

class FormActionView(TemplateView):
    '''
    This is a TemplateView which doesn't allow get, only post calls (with
    CSRF) for security reasons.
    '''

    def go_next(self, request):
        '''
        Returns a redirect to the page that was being shown
        '''
        next = request.REQUEST.get('next', None)
        if not next:
            next = request.META.get('HTTP_REFERER', None)
        if not next:
            next = '/'
        return http.HttpResponseRedirect(next)

    def get(self, request, *args, **kwargs):
        # Nice try :-P but that can only be done via POST
        messages.add_message(self.request, messages.ERROR, _('You tried to '
            'execute an action improperly.'))
        return redirect('/')

class SetLanguageView(FormActionView):
    """
    Extends django's set_language view to save the user's language in his
    profile and do it in post (to prevent CSRF)
    """

    def post(self, request, language, *args, **kwargs):
        if request.user.is_authenticated():
            request.user.lang_code = language
            request.user.save()

        next = request.REQUEST.get('next', None)
        if not next:
            next = request.META.get('HTTP_REFERER', None)
        if not next:
            next = '/'
        response = http.HttpResponseRedirect(next)
        if request.method == 'POST':
            if language and check_for_language(language):
                if hasattr(request, 'session'):
                    request.session['django_language'] = language
                else:
                    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
        return response


class HomeView(TemplateView):
    '''
    Shows main page. It's different for non-logged in users and logged in users:
    for the former, we show a carousel of news nicely geolocated in a map; for
    the later, we show the user's activity stream along with the calendar of
    relevant elections and the like at the sidebar.
    '''
    template_name = 'agora_core/home_activity.html'
    template_name_logged_in = 'agora_core/home_loggedin_activity.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated() and not request.user.is_anonymous():
            # change template
            self.template_name = self.template_name_logged_in
        return super(HomeView, self).get(request, *args, **kwargs)


class AgoraView(TemplateView):
    '''
    Shows an agora main page
    '''
    template_name = 'agora_core/agora_activity.html'

    def get_context_data(self, **kwargs):
        context = super(AgoraView, self).get_context_data(**kwargs)
        context['agora'] = self.agora
        return context

    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]

        self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        return super(AgoraView, self).dispatch(*args, **kwargs)

class AgoraBiographyView(TemplateView):
    '''
    Shows the biography of an agora
    '''
    template_name = 'agora_core/agora_bio.html'

    def get_context_data(self, username, agoraname, **kwargs):
        context = super(AgoraBiographyView, self).get_context_data(**kwargs)
        context['agora'] = agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        return context


class AgoraElectionsView(TemplateView):
    '''
    Shows the list of elections of an agora
    '''
    template_name = 'agora_core/agora_elections.html'

    def get_context_data(self, *args, **kwargs):
        context = super(AgoraElectionsView, self).get_context_data(**kwargs)
        self.kwargs = kwargs

        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]

        self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)

        context['agora'] = self.agora
        context['filter'] = self.kwargs["election_filter"]
        return context


class AgoraMembersView(TemplateView):
    '''
    Shows the biography of an agora
    '''
    template_name = 'agora_core/agora_members.html'

    def get_context_data(self, **kwargs):
        context = super(AgoraMembersView, self).get_context_data(**kwargs)
        self.kwargs = kwargs

        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]

        self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        context['agora'] = self.agora
        context['filter'] = self.kwargs["members_filter"]

        return context

class ElectionDelegatesView(TemplateView):
    '''
    Shows the biography of an agora
    '''
    template_name = 'agora_core/election_delegates.html'

    def get(self, request, *args, **kwargs):
        self.kwargs = kwargs
        return super(ElectionDelegatesView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ElectionDelegatesView, self).get_context_data(**kwargs)

        username = kwargs["username"]
        agoraname = kwargs["agoraname"]
        electionname = kwargs["electionname"]
        self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        context['election'] = self.election
        context['vote_form'] = VoteForm(self.request, self.election)
        context['permissions'] = self.election.get_perms(self.request.user)
        context['agora_perms'] = self.election.agora.get_perms(self.request.user)

        if self.request.user.is_authenticated():
            context['vote_from_user'] = self.election.get_vote_for_voter(
                self.request.user)
        return context

class  ElectionVotesView(ElectionDelegatesView):
    template_name = 'agora_core/election_votes.html'

    def get_queryset(self):
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]
        electionname = self.kwargs["electionname"]
        self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)
        return self.election.get_all_votes().all()

class CreateAgoraView(RequestCreateView):
    '''
    Creates a new agora
    '''
    template_name = 'agora_core/create_agora_form.html'
    form_class = CreateAgoraForm

    def get(self, request, *args, **kwargs):
        if not Agora.static_has_perms('create', request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have permission to create agoras'))

            return http.HttpResponseRedirect(reverse('home'))

        return super(CreateAgoraView, self).get(request, *args, **kwargs)


    def post(self, request, *args, **kwargs):
        if not Agora.static_has_perms('create', request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have permission to create agoras'))

            return http.HttpResponseRedirect(reverse('home'))

        return super(CreateAgoraView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        '''
        After creating the agora, show it
        '''
        agora = self.object

        messages.add_message(self.request, messages.SUCCESS, _('Creation of '
            'Agora %(agoraname)s successful! Now start to configure and use '
            'it.') % dict(agoraname=agora.name))

        return reverse('agora-view',
            kwargs=dict(username=agora.creator.username, agoraname=agora.name))

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(CreateAgoraView, self).dispatch(*args, **kwargs)


class CreateElectionView(RequestCreateView):
    '''
    Creates a new agora
    '''
    template_name = 'agora_core/create_election_form.html'
    form_class = CreateElectionForm

    def get_form_kwargs(self):
        form_kwargs = super(CreateElectionView, self).get_form_kwargs()
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]
        form_kwargs["agora"] = self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        return form_kwargs

    def get_success_url(self):
        '''
        After creating the election, show it
        '''
        election = self.object

        extra_data = dict(electionname=election.pretty_name,
            election_url=election.get_link(),
            agora_url=election.agora.get_full_name('link')
        )

        if election.is_approved:
            messages.add_message(self.request, messages.SUCCESS, _('Creation of '
                'Election <a href="%(election_url)s">%(electionname)s</a> in '
                '%(agora_url)s successful!') % extra_data)
        else:
            messages.add_message(self.request, messages.SUCCESS, _('Creation of '
                'Election <a href="%(election_url)s">%(electionname)s</a> in '
                '%(agora_url)s successful! Now it <strong>awaits the agora '
                'administrators approval</strong>.') % extra_data)

        return reverse('election-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name, electionname=election.name))

    def get_context_data(self, **kwargs):
        context = super(CreateElectionView, self).get_context_data(**kwargs)

        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]
        context['agora'] = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(CreateElectionView, self).dispatch(*args, **kwargs)

class AgoraView(TemplateView):
    '''
    Shows an agora main page
    '''
    template_name = 'agora_core/agora_activity.html'

    def get_context_data(self, **kwargs):
        context = super(AgoraView, self).get_context_data(**kwargs)
        context['agora'] = self.agora
        return context

    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]

        self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        return super(AgoraView, self).dispatch(*args, **kwargs)

class ElectionView(TemplateView):
    '''
    Shows an election main page
    '''
    template_name = 'agora_core/election_activity.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ElectionView, self).get_context_data(**kwargs)
        context['election'] = self.election
        context['permissions'] = self.election.get_perms(self.request.user)
        context['agora_perms'] = self.election.agora.get_perms(self.request.user)

        if self.request.user.is_authenticated():
            context['vote_from_user'] = self.election.get_vote_for_voter(
                self.request.user)
        return context

    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs

        username = kwargs['username']
        agoraname = kwargs['agoraname']
        electionname = kwargs['electionname']
        self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)
        return super(ElectionView, self).dispatch(*args, **kwargs)


class VotingBoothView(TemplateView):
    '''
    Shows an election voting booth
    '''
    template_name = 'agora_core/voting_booth.html'

    def get_context_data(self, *args, **kwargs):
        context = super(VotingBoothView, self).get_context_data(**kwargs)
        context['election'] = self.election
        return context

    def get(self, request, *args, **kwargs):
        if not self.election.has_perms('emit_direct_vote', request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have permissions to vote on <em>%(electionname)s</em>.') %\
                dict(electionname=self.election.pretty_name))
            return http.HttpResponseRedirect(self.election.get_link())
        return super(VotingBoothView, self).get(request, *args, **kwargs)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs

        username = kwargs['username']
        agoraname = kwargs['agoraname']
        electionname = kwargs['electionname']
        self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)
        return super(VotingBoothView, self).dispatch(*args, **kwargs)

class EditElectionView(UpdateView):
    '''
    Creates a new agora
    '''
    template_name = 'agora_core/election_edit.html'
    form_class = ElectionEditForm
    model = Election

    def post(self, request, *args, **kwargs):
        if not self.election.has_perms('edit_details', self.request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have edit permissions on <em>%(electionname)s</em>.') %\
                dict(electionname=self.election.pretty_name))

            url = reverse('election-view',
                kwargs=dict(username=election.agora.creator.username,
                    agoraname=election.agora.name, electionname=election.name))
            return http.HttpResponseRedirect(url)
        return super(EditElectionView, self).post(request, *args, **kwargs)


    def get(self, request, *args, **kwargs):
        if not self.election.has_perms('edit_details', self.request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have edit permissions on <em>%(electionname)s</em>.') %\
                dict(electionname=self.election.pretty_name))

            url = reverse('election-view',
                kwargs=dict(username=self.election.agora.creator.username,
                    agoraname=self.election.agora.name, electionname=self.election.name))
            return http.HttpResponseRedirect(url)
        return super(EditElectionView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        '''
        After creating the agora, show it
        '''
        messages.add_message(self.request, messages.SUCCESS, _('Election '
            '%(electionname)s edited.') % dict(electionname=self.election.pretty_name))

        action.send(self.request.user, verb='edited', action_object=self.election,
            ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        return reverse('election-view',
            kwargs=dict(username=self.election.agora.creator.username,
                agoraname=self.election.agora.name,
                electionname=self.election.name))

    def get_object(self):
        return self.election

    def get_context_data(self, *args, **kwargs):
        context = super(EditElectionView, self).get_context_data(**kwargs)
        context['object_list'] = []
        context['permissions'] = self.election.get_perms(self.request.user)
        return context

    def get_form_kwargs(self):
        kwargs = super(EditElectionView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        username = kwargs['username']
        agoraname = kwargs['agoraname']
        electionname = kwargs['electionname']
        self.election = get_object_or_404(Election, name=electionname,
            agora__name=agoraname, agora__creator__username=username)

        return super(EditElectionView, self).dispatch(*args, **kwargs)


class ApproveElectionView(FormActionView):
    def post(self, request, username, agoraname, electionname, *args, **kwargs):
        election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        if not election.has_perms('approve_election', request.user):
            messages.add_message(self.request, messages.ERROR, _('You don\'t '
                'have permission to approve the election.'))
            return self.go_next(request)

        election.is_approved = True
        election.save()

        action.send(self.request.user, verb='approved', action_object=election,
            target=election.agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ApproveElectionView, self).dispatch(*args, **kwargs)


class FreezeElectionView(FormActionView):
    def post(self, request, username, agoraname, electionname, *args, **kwargs):
        election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        if not election.has_perms('freeze_election', request.user):
            messages.add_message(self.request, messages.ERROR, _('You don\'t '
                'have permission to freeze the election.'))
            return self.go_next(request)

        election.frozen_at_date = timezone.now()
        election.save()

        action.send(self.request.user, verb='frozen', action_object=election,
            target=election.agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(FreezeElectionView, self).dispatch(*args, **kwargs)


class StartElectionView(FormActionView):
    def post(self, request, username, agoraname, electionname, *args, **kwargs):
        election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        if not election.has_perms('begin_election', request.user):
            messages.add_message(self.request, messages.ERROR, _('You don\'t '
                'have permission to start the election.'))
            return self.go_next(request)

        election.voting_starts_at_date = timezone.now()
        if not election.is_frozen():
            election.frozen_at_date = election.voting_starts_at_date
        election.save()
        transaction.commit()

        kwargs=dict(
            election_id=election.id,
            is_secure=self.request.is_secure(),
            site_id=Site.objects.get_current().id,
            remote_addr=self.request.META.get('REMOTE_ADDR'),
            user_id=self.request.user.id
        )
        start_election.apply_async(kwargs=kwargs, task_id=election.task_id(start_election))

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(StartElectionView, self).dispatch(*args, **kwargs)


class StopElectionView(FormActionView):
    def post(self, request, username, agoraname, electionname, *args, **kwargs):
        election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        if not election.has_perms('end_election', request.user):
            messages.add_message(self.request, messages.ERROR, _('You don\'t '
                'have permission to stop the election.'))
            return self.go_next(request)

        election.voting_extended_until_date = election.voting_ends_at_date = timezone.now()
        election.save()
        transaction.commit()

        kwargs=dict(
            election_id=election.id,
            is_secure=self.request.is_secure(),
            site_id=Site.objects.get_current().id,
            remote_addr=self.request.META.get('REMOTE_ADDR'),
            user_id=request.user.id
        )
        end_election.apply_async(kwargs=kwargs, task_id=election.task_id(end_election))

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(StopElectionView, self).dispatch(*args, **kwargs)


class ArchiveElectionView(FormActionView):
    def post(self, request, username, agoraname, electionname, *args, **kwargs):
        election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        if not election.has_perms('archive_election', request.user):
            messages.add_message(self.request, messages.ERROR, _('You don\'t '
                'have permission to archive the election.'))
            return self.go_next(request)

        if election.archived_at_date != None:
            messages.add_message(self.request, messages.ERROR, _('Election is '
                'already archived.'))
            return self.go_next(request)

        election.archived_at_date = timezone.now()

        if election.has_started() and not election.has_ended():
            election.voting_ends_at_date = election.archived_at_date
            election.voting_extended_until_date = election.archived_at_date

        if not election.is_frozen():
            election.frozen_at_date = election.archived_at_date

        election.save()

        context = get_base_email_context(self.request)

        context.update(dict(
            election=election,
            election_url=reverse('election-view',
                kwargs=dict(username=election.agora.creator.username,
                    agoraname=election.agora.name, electionname=election.name)),
            agora_url=reverse('agora-view',
                kwargs=dict(username=election.agora.creator.username,
                    agoraname=election.agora.name)),
        ))

        # List of emails to send. tuples are of format:
        #
        # (subject, text, html, from_email, recipient)
        datatuples = []

        for vote in election.get_all_votes():

            if not vote.voter.email or not vote.voter.get_profile().email_updates:
                continue

            context['to'] = vote.voter
            try:
                context['delegate'] = get_delegate_in_agora(vote.voter, election.agora)
            except:
                pass
            datatuples.append((
                _('Election archived: %s') % election.pretty_name,
                render_to_string('agora_core/emails/election_archived.txt',
                    context),
                render_to_string('agora_core/emails/election_archived.html',
                    context),
                None,
                [vote.voter.email]))

        send_mass_html_mail(datatuples)

        action.send(self.request.user, verb='archived', action_object=election,
            target=election.agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ArchiveElectionView, self).dispatch(*args, **kwargs)


class VoteView(CreateView):
    '''
    Creates a new agora
    '''
    template_name = 'agora_core/vote_form.html'
    form_class = VoteForm

    def get_form_kwargs(self):
        form_kwargs = super(VoteView, self).get_form_kwargs()
        form_kwargs["request"] = self.request
        form_kwargs["election"] = self.election
        return form_kwargs

    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS, _('Your vote was '
            'correctly casted! Now you could share this election in Facebook, '
            'Google Plus, Twitter, etc.'))

        # NOTE: The form is in charge in this case of creating the related action

        context = get_base_email_context(self.request)

        context.update(dict(
            to=self.request.user,
            election=self.election,
            election_url=reverse('election-view',
                kwargs=dict(username=self.election.agora.creator.username,
                    agoraname=self.election.agora.name, electionname=self.election.name)),
            agora_url=reverse('agora-view',
                kwargs=dict(username=self.election.agora.creator.username,
                    agoraname=self.election.agora.name)),
        ))

        if self.request.user.email and self.request.user.get_profile().email_updates:
            email = EmailMultiAlternatives(
                subject=_('Vote casted for election %s') % self.election.pretty_name,
                body=render_to_string('agora_core/emails/vote_casted.txt',
                    context),
                to=[self.request.user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/vote_casted.html',
                    context), "text/html")
            email.send()

        if not is_following(self.request.user, self.election):
            follow(self.request.user, self.election, actor_only=False, request=self.request)

        return reverse('election-view',
            kwargs=dict(username=self.election.agora.creator.username,
                agoraname=self.election.agora.name, electionname=self.election.name))

    def get_context_data(self, **kwargs):
        context = super(VoteView, self).get_context_data(**kwargs)
        form = kwargs['form']
        context['vote_form'] = form
        context['election'] = form.election
        context['permissions'] = form.election.get_perms(self.request.user)
        context['agora_perms'] = form.election.agora.get_perms(self.request.user)
        context['object_list'] = election_stream(form.election)
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        username = kwargs["username"]
        agoraname = kwargs["agoraname"]
        electionname = kwargs["electionname"]
        self.election = get_object_or_404(Election, name=electionname,
            agora__name=agoraname, agora__creator__username=username)

        # check if ballot is open
        if not self.election.ballot_is_open():
            messages.add_message(self.request, messages.ERROR, _('Sorry, '
                'election is closed and thus you cannot vote.'))
            election_url = reverse('election-view',
                kwargs=dict(username=username, agoraname=agoraname,
                    electionname=electionname))
            return http.HttpResponseRedirect(election_url)

        return super(VoteView, self).dispatch(*args, **kwargs)

class AgoraActionChooseDelegateView(FormActionView):
    def post(self, request, username, agoraname, delegate_username, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)
        delegate = get_object_or_404(User, username=delegate_username)

        if delegate_username == self.request.user.username:
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
                'you cannot delegate to yourself ;-).'))
            return self.go_next(request)

        if self.request.user not in agora.members.all():
            if not agora.has_perms('join', self.request.user):
                messages.add_message(self.request, messages.ERROR, _('Sorry, '
                    'but you cannot delegate if you\'re not a member of the '
                    'agora first.'))
                return self.go_next(request)
            # Join agora if possible
            AgoraActionJoinView().post(request, username, agoraname)

        # invalidate older votes from the same voter to the same election
        old_votes = agora.delegation_election.cast_votes.filter(
            is_direct=False, invalidated_at_date=None, voter=self.request.user)
        for old_vote in old_votes:
            old_vote.invalidated_at_date = timezone.now()
            old_vote.save()

        # Forge the delegation vote
        vote = CastVote()
        vote.data = {
            "a": "delegated-vote",
            "answers": [
                {
                    "a": "plaintext-delegate",
                    "choices": [
                        {
                            'user_id': delegate.id, # id of the User in which the voter delegates
                            'username': delegate.username,
                            'user_name': delegate.first_name, # data of the User in which the voter delegates
                        }
                    ]
                }
            ],
            "election_hash": {"a": "hash/sha256/value", "value": agora.delegation_election.hash},
            "election_uuid": agora.delegation_election.uuid
        }

        vote.voter = self.request.user
        vote.election = agora.delegation_election
        vote.is_counted = self.request.user in agora.members.all()
        vote.is_direct = False
        vote.is_public = not agora.is_vote_secret
        vote.casted_at_date = timezone.now()
        vote.create_hash()
        vote.save()

        # Create the delegation action
        action.send(self.request.user, verb='delegated', action_object=vote,
            target=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        vote.action_id = Action.objects.filter(actor_object_id=self.request.user.id,
            verb='delegated', action_object_object_id=vote.id,
            target_object_id=agora.id).order_by('-timestamp').all()[0].id


        # Send the email to the voter (and maybe to the delegate too!)
        context = get_base_email_context(self.request)
        context.update(dict(
            agora=agora,
            delegate=delegate,
            vote=vote
        ))

        # Mail to the voter
        if vote.voter.get_profile().has_perms('receive_email_updates'):
            context['to'] = vote.voter

            email = EmailMultiAlternatives(
                subject=_('%(site)s - You delegated your vote in %(agora)s') %\
                    dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/user_delegated.txt',
                    context),
                to=[vote.voter.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/user_delegated.html',
                    context), "text/html")
            email.send()

        if vote.is_public and delegate.get_profile().has_perms('receive_email_updates'):
            context['to'] = delegate

            email = EmailMultiAlternatives(
                subject=_('%(site)s - You have a new delegation in %(agora)s') %\
                    dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/new_delegation.txt',
                    context),
                to=[delegate.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/new_delegation.html',
                    context), "text/html")
            email.send()

        messages.add_message(self.request, messages.SUCCESS, _('You delegated '
            'your vote in %(agora)s to %(username)s! Now you could share this '
            'in Facebook, Google Plus, Twitter, etc.') % dict(
                agora=agora.creator.username+'/'+agora.name,
                username=delegate.username))

        if not is_following(self.request.user, delegate) and vote.is_public:
            follow(self.request.user, delegate, actor_only=False, request=self.request)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionChooseDelegateView, self).dispatch(*args, **kwargs)


class AgoraActionJoinView(FormActionView):
    def post(self, request, username, agoraname, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)

        if request.user in agora.members.all():
            messages.add_message(request, messages.ERROR, _('Guess what, you '
                'are already a member of %(agora)s!' %\
                    dict(agora=username+'/'+agoraname)))
            return self.go_next(request)

        can_join = agora.has_perms('join', request.user)
        can_request_membership = agora.has_perms('request_membership', request.user)

        if not can_join and not can_request_membership:
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have permission to join this agora.'))
            return self.go_next(request)

        if can_join:
            agora.members.add(request.user)
            agora.save()

            action.send(request.user, verb='joined', action_object=agora,
                ipaddr=request.META.get('REMOTE_ADDR'),
                geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

            # TODO: send an email to the user
            messages.add_message(request, messages.SUCCESS, _('You joined '
                '%(agora)s. Now you could take a look at what elections are '
                'available at this agora') % dict(
                    agora=agora.creator.username+'/'+agora.name))

            if not is_following(request.user, agora):
                follow(request.user, agora, actor_only=False, request=request)
        elif can_request_membership:
            assign('requested_membership', request.user, agora)

            action.send(request.user, verb='requested membership', action_object=agora,
                ipaddr=request.META.get('REMOTE_ADDR'),
                geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

            messages.add_message(request, messages.SUCCESS, _('You requested '
                'membership in %(agora)s. Soon the admins of this agora will '
                'decide on your request.') % dict(
                    agora=agora.creator.username+'/'+agora.name))

            # Mail to the admins
            context = get_base_email_context(self.request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('%(username)s has requested membership at '
                    '%(agora)s. Please review this pending request') % dict(
                        username=request.user.username,
                        agora=agora.get_full_name()
                    ),
                extra_urls=(
                    (_('List of membership requests'),
                    reverse('agora-members',
                        kwargs=dict(
                            username=agora.creator,
                            agoraname=agora.name,
                            members_filter="membership_requests"
                        ))
                    ),
                ),
            ))
            for admin in agora.admins.all():
                if not admin.get_profile().has_perms('receive_email_updates'):
                    continue

                context['to'] = admin

                email = EmailMultiAlternatives(
                    subject=_('%(site)s - New membership request at %(agora)s') %\
                        dict(
                            site=Site.objects.get_current().domain,
                            agora=agora.get_full_name()
                        ),
                    body=render_to_string('agora_core/emails/agora_notification.txt',
                        context),
                    to=[admin.email])

                email.attach_alternative(
                    render_to_string('agora_core/emails/agora_notification.html',
                        context), "text/html")
                email.send()

            if not is_following(request.user, agora):
                follow(request.user, agora, actor_only=False, request=request)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionJoinView, self).dispatch(*args, **kwargs)


class AgoraActionRequestAdminMembershipView(FormActionView):
    def post(self, request, username, agoraname, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)

        if request.user not in agora.members.all():
            messages.add_message(request, messages.ERROR, _('Sorry but you need'
                ' to be a member of %(agora)s to request admin membership!' %\
                    dict(agora=username+'/'+agoraname)))
            return self.go_next(request)

        if not agora.has_perms('request_admin_membership', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have permission to request admin membership in this agora.'))
            return self.go_next(request)

        assign('requested_admin_membership', request.user, agora)

        action.send(request.user, verb='requested admin membership', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the admins
        context = get_base_email_context(self.request)
        context.update(dict(
            agora=agora,
            other_user=request.user,
            notification_text=_('%(username)s has requested admin membership '
                'at %(agora)s. Please review this pending request') % dict(
                    username=request.user.username,
                    agora=agora.get_full_name()
                ),
            extra_urls=(
                (_('List of admin membership requests'),
                reverse('agora-members',
                    kwargs=dict(
                        username=agora.creator,
                        agoraname=agora.name,
                        members_filter="admin_membership_requests"
                    ))
                ),
            ),
        ))
        for admin in agora.admins.all():
            if not admin.get_profile().has_perms('receive_email_updates'):
                continue

            context['to'] = admin

            email = EmailMultiAlternatives(
                subject=_('%(site)s - New admin membership request at %(agora)s') %\
                    dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[admin.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        messages.add_message(request, messages.SUCCESS, _('You requested '
            'admin membership in %(agora)s. Soon the admins of this agora will '
            'decide on your request.') % dict(
                agora=agora.creator.username+'/'+agora.name))
        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionRequestAdminMembershipView, self).dispatch(*args, **kwargs)


class AgoraActionCancelAdminMembershipRequestView(FormActionView):
    def post(self, request, username, agoraname, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)

        if not agora.has_perms('cancel_admin_membership_request', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have permission to cancel admin membership request in this agora.'))
            return self.go_next(request)

        remove_perm('requested_admin_membership', request.user, agora)

        action.send(request.user, verb='cancelled requested admin membership', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('Your admin '
            'membership in %(agora)s was cancelled.') % dict(
                agora=agora.creator.username+'/'+agora.name))

        # Mail to the admins
        context = get_base_email_context(self.request)
        context.update(dict(
            agora=agora,
            other_user=request.user,
            notification_text=_('%(username)s has cancelled his/her requested '
                'admin membership at %(agora)s.') % dict(
                    username=request.user.username,
                    agora=agora.get_full_name()
                )
        ))
        for admin in agora.admins.all():
            if not admin.get_profile().has_perms('receive_email_updates'):
                continue

            context['to'] = admin

            email = EmailMultiAlternatives(
                subject=_('%(site)s - %(username)s cancelled his/her admin '
                    'membership request at %(agora)s') % dict(
                            username=request.user.username,
                            site=Site.objects.get_current().domain,
                            agora=agora.get_full_name()
                        ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[admin.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionCancelAdminMembershipRequestView, self).dispatch(*args, **kwargs)


class AgoraActionAcceptMembershipRequestView(FormActionView):
    def post(self, request, username, agoraname, username2, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)
        user = get_object_or_404(User, username=username2)

        if not agora.has_perms('admin', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have admin permissions in this agora.'))
            return self.go_next(request)

        if not agora.has_perms('cancel_membership_request', user):
            messages.add_message(request, messages.ERROR, _('Sorry, you cannot '
                'accept this user\'s  membership request.'))
            return self.go_next(request)

        remove_perm('requested_membership', user, agora)
        agora.members.add(user)
        agora.save()

        action.send(request.user, verb='accepted membership request', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('You accepted  '
            '%(username)s membership request in %(agora)s.') % dict(
                username=username2,
                agora=agora.creator.username+'/'+agora.name))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            context = get_base_email_context(self.request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your membership has been accepted at '
                    '%(agora)s. Congratulations!') % dict(
                        agora=agora.get_full_name()
                    ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - you are now member of %(agora)s') % dict(
                            site=Site.objects.get_current().domain,
                            agora=agora.get_full_name()
                        ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionAcceptMembershipRequestView, self).dispatch(*args, **kwargs)


class AgoraActionMakeAdminView(FormActionView):
    def post(self, request, username, agoraname, username2, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)
        user = get_object_or_404(User, username=username2)

        if not agora.has_perms('admin', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have admin permissions in this agora.'))
            return self.go_next(request)

        if not agora.has_perms('leave', user):
            messages.add_message(request, messages.ERROR, _('Sorry, you cannot '
                'make admin to this user.'))
            return self.go_next(request)

        agora.admins.add(user)
        agora.save()

        action.send(request.user, verb='made admin', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('You made admin to '
            '%(username)s admin in %(agora)s.') % dict(
                username=username2,
                agora=agora.creator.username+'/'+agora.name))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            context = get_base_email_context(self.request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('You\'ve been promoted to admin at '
                    '%(agora)s. Congratulations!') % dict(
                        agora=agora.get_full_name()
                    ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - you\'ve been promoted to admin at '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionMakeAdminView, self).dispatch(*args, **kwargs)


class AgoraActionAcceptAdminMembershipRequestView(FormActionView):
    def post(self, request, username, agoraname, username2, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)
        user = get_object_or_404(User, username=username2)

        if not agora.has_perms('admin', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have admin permissions in this agora.'))
            return self.go_next(request)

        if not agora.has_perms('cancel_admin_membership_request', user):
            messages.add_message(request, messages.ERROR, _('Sorry, you cannot '
                'accept this user\'s  admin membership request.'))
            return self.go_next(request)

        remove_perm('requested_admin_membership', user, agora)
        agora.admins.add(user)
        agora.save()

        action.send(request.user, verb='accepted admin membership request', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('You accepted  '
            '%(username)s admin membership request in %(agora)s.') % dict(
                username=username2,
                agora=agora.creator.username+'/'+agora.name))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            context = get_base_email_context(self.request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your admin membership has been accepted '
                    ' so you\'ve been promoted to admin at %(agora)s. '
                    'Congratulations!') % dict(
                            agora=agora.get_full_name()
                        ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - you\'ve been promoted to admin at '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionAcceptAdminMembershipRequestView, self).dispatch(*args, **kwargs)


class AgoraActionLeaveView(FormActionView):
    def post(self, request, username, agoraname, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)

        can_leave = agora.has_perms('leave', request.user)
        can_cancel_mem_request = agora.has_perms('cancel_membership_request',
            request.user)

        if not can_leave and not can_cancel_mem_request:
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have permission to leave this agora.'))
            return self.go_next(request)

        if can_leave:
            agora.members.remove(request.user)
            agora.save()
            action.send(request.user, verb='left', action_object=agora,
                ipaddr=request.META.get('REMOTE_ADDR'),
                geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

            # TODO: send an email to the user
            messages.add_message(request, messages.SUCCESS, _('You left '
                '%(agora)s.') % dict(agora=agora.creator.username+'/'+agora.name))
        else:
            remove_perm('requested_membership', request.user, agora)

            action.send(request.user, verb='cancelled his/her membership request',
                action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
                geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

            # TODO: send an email to the user
            messages.add_message(request, messages.SUCCESS, _('You '
            'cancelled your membership request at %(agora)s.') %\
                dict(agora=agora.creator.username+'/'+agora.name))


        if is_following(self.request.user, agora):
            unfollow(self.request.user, agora, request=self.request)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionLeaveView, self).dispatch(*args, **kwargs)


class AgoraActionDismissMembershipRequestView(FormActionView):
    def post(self, request, username, agoraname, username2, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)
        user = get_object_or_404(User, username=username2)

        if not agora.has_perms('admin', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have admin permissions in this agora.'))
            return self.go_next(request)

        if not agora.has_perms('cancel_membership_request', user):
            messages.add_message(request, messages.ERROR, _('Sorry, you cannot '
                'dismiss this user\'s  membership request.'))
            return self.go_next(request)

        remove_perm('requested_membership', user, agora)

        action.send(request.user, verb='dismissed membership request',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('You '
            'dismissed %(username)s membership request at %(agora)s.') % dict(
                username=username2,
                agora=agora.creator.username+'/'+agora.name))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            context = get_base_email_context(self.request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your membership request at %(agora)s '
                    'has been dismissed. Sorry about that!') % dict(
                            agora=agora.get_full_name()
                        ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - membership request dismissed at '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        if is_following(self.request.user, agora):
            unfollow(self.request.user, agora, request=self.request)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionDismissMembershipRequestView, self).dispatch(*args, **kwargs)


class AgoraActionDismissAdminMembershipRequestView(FormActionView):
    def post(self, request, username, agoraname, username2, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)
        user = get_object_or_404(User, username=username2)

        if not agora.has_perms('admin', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have admin permissions in this agora.'))
            return self.go_next(request)

        if not agora.has_perms('cancel_admin_membership_request', user):
            messages.add_message(request, messages.ERROR, _('Sorry, you cannot '
                'dismiss this user\'s  admin membership request.'))
            return self.go_next(request)

        remove_perm('requested_admin_membership', user, agora)

        action.send(request.user, verb='dismissed admin membership request',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('You '
            'dismissed %(username)s admin membership request at %(agora)s.') % dict(
                username=username2,
                agora=agora.creator.username+'/'+agora.name))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            context = get_base_email_context(self.request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your admin membership request at %(agora)s '
                    ' has been dismissed. Sorry about that!') % dict(
                            agora=agora.get_full_name()
                        ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - admin membership request dismissed at '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        if is_following(self.request.user, agora):
            unfollow(self.request.user, agora, request=self.request)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionDismissAdminMembershipRequestView, self).dispatch(*args, **kwargs)



class AgoraActionRemoveMembershipView(FormActionView):
    def post(self, request, username, agoraname, username2, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)
        user = get_object_or_404(User, username=username2)

        if not agora.has_perms('admin', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have admin permissions in this agora.'))
            return self.go_next(request)

        if not agora.has_perms('leave', user):
            messages.add_message(request, messages.ERROR, _('Sorry, this user '
                'doesn\'t have permission to leave this agora.'))
            return self.go_next(request)

        agora.members.remove(user)
        agora.save()
        action.send(request.user, verb='removed membership', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('You removed '
            'membership from %(agora)s to %(username)s.') % dict(
                username=username2,
                agora=agora.creator.username+'/'+agora.name))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            context = get_base_email_context(self.request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your have been removed from membership '
                    'from %(agora)s . Sorry about that!') % dict(
                            agora=agora.get_full_name()
                        ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - membership removed from '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        if is_following(self.request.user, agora):
            unfollow(self.request.user, agora, request=self.request)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionRemoveMembershipView, self).dispatch(*args, **kwargs)


class AgoraActionLeaveAdminView(FormActionView):
    def post(self, request, username, agoraname, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)

        if not agora.has_perms('leave_admin', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have permission to leave this agora.'))
            return self.go_next(request)

        agora.admins.remove(request.user)
        agora.save()

        action.send(request.user, verb='removed admin membership',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # TODO: send an email to the user
        messages.add_message(request, messages.SUCCESS, _('You removed your '
            'admin membership at %(agora)s.') % dict(agora=agora.creator.username+'/'+agora.name))

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionLeaveAdminView, self).dispatch(*args, **kwargs)


class AgoraActionRemoveAdminMembershipView(FormActionView):
    def post(self, request, username, agoraname, username2, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)
        user = get_object_or_404(User, username=username2)

        if not agora.has_perms('admin', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have admin permissions in this agora.'))
            return self.go_next(request)

        if not agora.has_perms('leave_admin', user):
            messages.add_message(request, messages.ERROR, _('Sorry, this user '
                'doesn\'t have permission to leave this agora.'))
            return self.go_next(request)

        agora.admins.remove(user)
        agora.save()

        action.send(request.user, verb='removed admin membership',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('You removed  '
            'admin membership from %(agora)s to %(username)s.') % dict(
                username=username2,
                agora=agora.creator.username+'/'+agora.name))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            context = get_base_email_context(self.request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your have been removed from admin '
                    'membership from %(agora)s . Sorry about that!') % dict(
                            agora=agora.get_full_name()
                        ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - admin membership removed from '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()        

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionRemoveAdminMembershipView, self).dispatch(*args, **kwargs)


class ElectionCommentsView(ElectionView):
    template_name = 'agora_core/election_comments.html'

    def get_queryset(self):
        return object_stream(self.election, verb='commented')

    def get_context_data(self, *args, **kwargs):
        context = super(ElectionCommentsView, self).get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated():
            context['form'] = PostCommentForm(request=self.request,
                target_object=self.election)
            context['form'].helper.form_action = reverse('election-comments-post',
                kwargs=dict(username=self.election.agora.creator.username,
                    agoraname=self.election.agora.name,
                    electionname=self.election.name))
        return context
				
class  ElectionVotesGraphView(ElectionDelegatesView):
    template_name = 'agora_core/election_votes_graph.html'

    def get_queryset(self):
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]
        electionname = self.kwargs["electionname"]
        self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)
        return self.election.get_all_votes().all()

class ElectionPostCommentView(RequestCreateView):
    template_name = 'agora_core/election_comments.html'
    form_class = PostCommentForm

    def get_context_data(self, *args, **kwargs):
        context = super(ElectionPostCommentView, self).get_context_data(*args, **kwargs)
        context['election'] = self.election
        context['vote_form'] = VoteForm(self.request, self.election)
        context['permissions'] = self.election.get_perms(self.request.user)
        context['agora_perms'] = self.election.agora.get_perms(self.request.user)
        context['object_list'] = object_stream(self.election, verb='commented')
        return context

    def get_form_kwargs(self):
        kwargs = super(ElectionPostCommentView, self).get_form_kwargs()
        kwargs['target_object'] = self.election
        return kwargs

    def get_success_url(self):
        '''
        After creating the comment, post the action and show last comments
        '''
        comment = self.object

        messages.add_message(self.request, messages.SUCCESS, _('Your comment '
            'was successfully posted.'))

        if not is_following(self.request.user, self.election):
            follow(self.request.user, self.election, actor_only=False, request=self.request)

        return reverse('election-comments',
            kwargs=dict(username=self.election.agora.creator.username,
                agoraname=self.election.agora.name,
                electionname=self.election.name))

    def post(self, request, *args, **kwargs):
        if not self.election.has_perms('comment', self.request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have comment permissions on <em>%(electionname)s</em>.') %\
                dict(electionname=self.election.pretty_name))

            url = reverse('election-view',
                kwargs=dict(username=election.agora.creator.username,
                    agoraname=election.agora.name, electionname=election.name))
            return http.HttpResponseRedirect(url)
        return super(ElectionPostCommentView, self).post(request, *args, **kwargs)

    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs

        username = kwargs['username']
        agoraname = kwargs['agoraname']
        electionname = kwargs['electionname']
        self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        return super(ElectionPostCommentView, self).dispatch(*args, **kwargs)


class AgoraCommentsView(AgoraView):
    template_name = 'agora_core/agora_comments.html'

    def get_queryset(self):
        return object_stream(self.agora, verb='commented')

    def get_context_data(self, *args, **kwargs):
        context = super(AgoraCommentsView, self).get_context_data(*args, **kwargs)
        context['agora'] = self.agora

        if self.request.user.is_authenticated():
            context['form'] = PostCommentForm(request=self.request,
                target_object=self.agora)
            context['form'].helper.form_action = reverse('agora-comments-post',
                kwargs=dict(username=self.agora.creator.username,
                    agoraname=self.agora.name))
        return context


class AgoraPostCommentView(RequestCreateView):
    template_name = 'agora_core/agora_comments.html'
    form_class = PostCommentForm

    def get_context_data(self, *args, **kwargs):
        context = super(AgoraPostCommentView, self).get_context_data(*args, **kwargs)
        context['agora'] = self.agora
        context['object_list'] = object_stream(self.agora, verb='commented')
        return context

    def get_form_kwargs(self):
        kwargs = super(AgoraPostCommentView, self).get_form_kwargs()
        kwargs['target_object'] = self.agora
        return kwargs

    def get_success_url(self):
        '''
        After creating the comment, post the action and show last comments
        '''
        comment = self.object

        messages.add_message(self.request, messages.SUCCESS, _('Your comment '
            'was successfully posted.'))

        action.send(self.request.user, verb='commented', target=self.agora,
            action_object=comment, ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        if not is_following(self.request.user, self.agora):
            follow(self.request.user, self.agora, actor_only=False, request=self.request)

        return reverse('agora-comments',
            kwargs=dict(username=self.agora.creator.username,
                agoraname=self.agora.name))

    def post(self, request, *args, **kwargs):
        if not self.agora.has_perms('comment', self.request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have comment permissions on %(agora)s.') %\
                dict(agora=self.agora.get_full_name('link')))
            return http.HttpResponseRedirect(agora.get_link())

        return super(AgoraPostCommentView, self).post(request, *args, **kwargs)

    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs

        username = kwargs['username']
        agoraname = kwargs['agoraname']
        self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        return super(AgoraPostCommentView, self).dispatch(*args, **kwargs)

class CancelVoteView(FormActionView):
    def post(self, request, username, agoraname, electionname, *args, **kwargs):
        election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        election_url=reverse('election-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name, electionname=election.name))

        if not election.ballot_is_open():
            messages.add_message(self.request, messages.ERROR, _('You can\'t '
                'cancel a vote in a closed election.'))
            return http.HttpResponseRedirect(election_url)

        vote = election.get_vote_for_voter(self.request.user)

        if not vote or not vote.is_direct:
            messages.add_message(self.request, messages.ERROR, _('You didn\'t '
                'participate in this election.'))
            return http.HttpResponseRedirect(election_url)

        vote.invalidated_at_date = timezone.now()
        vote.is_counted = False
        vote.save()

        context = get_base_email_context(self.request)
        context.update(dict(
            election=election,
            election_url=election_url,
            to=vote.voter,
            agora_url=reverse('agora-view',
                kwargs=dict(username=election.agora.creator.username,
                    agoraname=election.agora.name)),
        ))

        try:
            context['delegate'] = get_delegate_in_agora(vote.voter, election.agora)
        except:
            pass

        if vote.voter.email and vote.voter.get_profile().email_updates:
            email = EmailMultiAlternatives(
                subject=_('Vote cancelled for election %s') % election.pretty_name,
                body=render_to_string('agora_core/emails/vote_cancelled.txt',
                    context),
                to=[vote.voter.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/vote_cancelled.html',
                    context), "text/html")
            email.send()

        action.send(self.request.user, verb='vote cancelled', action_object=election,
            target=election.agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        return http.HttpResponseRedirect(election_url)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(CancelVoteView, self).dispatch(*args, **kwargs)

class UserView(TemplateView):
    '''
    Shows an user main page
    '''
    template_name = 'agora_core/user_activity.html'

    def get_context_data(self, *args, **kwargs):
        context = super(UserView, self).get_context_data(**kwargs)
        context['user_shown'] = self.user_shown
        return context

    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs

        username = kwargs['username']
        self.user_shown = get_object_or_404(User, username=username)
        return super(UserView, self).dispatch(*args, **kwargs)

class UserBiographyView(UserView):
    template_name = 'agora_core/user_bio.html'

    def get_context_data(self, *args, **kwargs):
        context = super(UserBiographyView, self).get_context_data(**kwargs)
        context['user_shown'] = self.user_shown
        return context

    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs

        username = kwargs['username']
        self.user_shown = get_object_or_404(User, username=username)
        return super(UserView, self).dispatch(*args, **kwargs)

class UserSettingsView(UpdateView):
    '''
    Creates a new agora
    '''
    template_name = 'agora_core/user_settings.html'
    form_class = UserSettingsForm
    model = User

    def get_success_url(self):
        '''
        After creating the agora, show it
        '''
        messages.add_message(self.request, messages.SUCCESS,
            _('User settings updated.'))

        action.send(self.request.user, verb='settings updated',
            ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        return reverse('user-view',
            kwargs=dict(username=self.request.user.username))

    def get_object(self):
        return self.request.user

    def get_context_data(self, *args, **kwargs):
        context = super(UserSettingsView, self).get_context_data(**kwargs)
        context['user_shown'] = self.request.user
        return context

    def get_form_kwargs(self):
        kwargs = super(UserSettingsView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserSettingsView, self).dispatch(*args, **kwargs)


class UserElectionsView(TemplateView):
    '''
    Shows the list of elections of an agora
    '''
    template_name = 'agora_core/user_elections.html'

    def get(self, request, *args, **kwargs):
        self.kwargs = kwargs
        return super(UserElectionsView, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(UserElectionsView, self).get_context_data(**kwargs)
        username = kwargs["username"]
        self.user_shown = get_object_or_404(User, username=username)

        context['user_shown'] = self.user_shown
        context['filter'] = self.kwargs["election_filter"]
        return context


class AgoraAdminView(UpdateView):
    '''
    Creates a new agora
    '''
    template_name = 'agora_core/agora_admin.html'
    form_class = AgoraAdminForm
    model = Agora

    def post(self, request, *args, **kwargs):
        if not self.agora.has_perms('admin', self.request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have admin permissions on %(agoraname)s.') %\
                dict(agoraname=self.agora.name))

            url = reverse('agora-view',
                kwargs=dict(username=agora.creator.username, agoraname=agora.name))
            return http.HttpResponseRedirect(url)
        return super(AgoraAdminView, self).post(request, *args, **kwargs)


    def get(self, request, *args, **kwargs):
        if not self.agora.has_perms('admin', self.request.user):
            messages.add_message(self.request, messages.ERROR, _('Sorry, but '
            'you don\'t have admin permissions on %(agoraname)s.') %\
                dict(agoraname=self.agora.name))

            url = reverse('agora-view',
                kwargs=dict(username=self.agora.creator.username, agoraname=self.agora.name))
            return http.HttpResponseRedirect(url)
        return super(AgoraAdminView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        '''
        After creating the agora, show it
        '''
        agora = self.object

        messages.add_message(self.request, messages.SUCCESS, _('Agora settings '
            'changed for %(agoraname)s.') % dict(agoraname=self.agora.name))

        action.send(self.request.user, verb='changed settings', action_object=agora,
            ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        return reverse('agora-view',
            kwargs=dict(username=agora.creator.username, agoraname=agora.name))

    def get_object(self):
        return self.agora

    def get_form_kwargs(self):
        kwargs = super(AgoraAdminView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super(AgoraAdminView, self).get_context_data(*args, **kwargs)
        context['MIN_NUM_AUTHORITIES'] = settings.MIN_NUM_AUTHORITIES
        context['MAX_NUM_AUTHORITIES'] = settings.MAX_NUM_AUTHORITIES
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        username = kwargs['username']
        agoraname = kwargs['agoraname']
        self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)

        return super(AgoraAdminView, self).dispatch(*args, **kwargs)

class AgoraListView(TemplateView):
    '''
    Lists all agoras
    '''
    template_name = 'agora_core/agora_list.html'

class ElectionListView(TemplateView):
    '''
    Lists all elections
    '''
    template_name = 'agora_core/election_list.html'

class UserListView(TemplateView):
    '''
    Lists all elections
    '''
    template_name = 'agora_core/user_listing.html'

class SearchView(TemplateView, HaystackSearchView):
    '''
    Generic search view for all kinds of indexed objects
    '''
    template_name = 'search/search.html'
    form_class = ModelSearchForm
    load_all = True
    searchqueryset = None
    searchmodel = None

    def get_queryset(self):
        return self.results

    def get_context_data(self, **kwargs):
        context = super(SearchView, self).get_context_data(**kwargs)
        context.update({
            'query': self.query,
            'form': self.form,
            'num_results': self.get_queryset().count()
        })
        return context

    def get(self, request, *args, **kwargs):
        self.request = request
        # [('agora_core.agora', u'Agoras'), ('agora_core.election', u'Elections'), ('agora_core.profile', u'Profiles')]
        self.form = self.build_form()
        self.query = self.get_query()

        if self.searchmodel != None and not self.query:
            if self.searchmodel == "agoras":
                self.results = Agora.objects.order_by('-created_at_date').all()
            elif self.searchmodel == "elections":
                self.results = Election.objects.exclude(url__startswith="http://example.com/delegation/has/no/url/").order_by('-last_modified_at_date')
            elif self.searchmodel == "profiles":
                self.results = Profile.objects.all()
        else:
            self.results = self.get_results()
        return super(SearchView, self).get(request, *args, **kwargs)


class ContactView(FormView):
    template_name = 'agora_core/contact_form.html'
    form_class = ContactForm

    def get_form_kwargs(self):
        kwargs = super(ContactView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_success_url(self):
        return reverse('home')


    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        form.send()
        return super(ContactView, self).form_valid(form)

class FNMTLoginView(TemplateView):
    '''
    Used to authenticate or register users using the FNMT client certificate
    '''
    template_name = "agora_core/fnmt_login.html"

    def go_next(self):
        '''
        Does its best effort to return a redirect to the page that was
        previously being shown
        '''
        next = self.request.REQUEST.get('next', None)
        if not next:
            next = settings.LOGIN_REDIRECT_URL
        return http.HttpResponseRedirect(next)

    def invalid_login(self):
        return super(FNMTLoginView, self).get(self.request)

    def get(self, request, *args, **kwargs):
        self.request = request

        if request.user.is_authenticated() and not request.user.is_anonymous():
            return self.go_next()

        # NOTE: nginx adds \t to the certificate because otherwise it would be not
        # possible to send it as a proxy header, so we have to remove those tabs.
        # A PEM certificate does never contain tabs, so this replace is safe anyway.
        # For more details see:
        # - https://www.ruby-forum.com/topic/155918 and
        # - http://nginx.org/en/docs/http/ngx_http_ssl_module.html
        cert_pem = self.request.META.get('X-Sender-SSL-Certificate', '').replace('\t', '')
        verify = self.request.META.get('X-Sender-SSL-Verify', 'NONE')
        if verify != "SUCCESS":
            return self.invalid_login()
        try:
            nif, full_name, email = fnmt_data_from_pem(cert_pem)

            user = authenticate(cert_pem=cert_pem, full_name=full_name,
                email=email, nif=nif)

            if user is None:
                return self.invalid_login()

            # show a form requesting the user its email
            if not email and not user.is_active:
                logout(request)
                return redirect(settings.AGORA_BASE_URL + reverse('register-complete-fnmt',
                    kwargs=dict(activation_key=user.userena_signup.activation_key)))

            login(request, user)
            return self.go_next()

        except:
            return self.invalid_login()


class AvailableAuthoritiesView(TemplateView):
    template_name = 'agora_core/available_authorities.html'


class UpdateAgoraDelegationElectionView(TemplateView):
    '''
    Receives updates from election-orchestra
    '''
    def post(self, request, agora_id, *args, **kwargs):
        try:
            data = json.loads(request.raw_post_data)
            agora = None
            agora = Agora.objects.get(id=agora_id)
            ssid = data['reference']['session_id']
            status = data['status']
            publickey = data['data']['publickey']
        except:
            return http.HttpResponse()

        if not isinstance(agora.delegation_status, dict) or\
                agora.delegation_status.get('status', '') == 'success' or\
                agora.delegation_status.get('session_id') != ssid:
            return http.HttpResponse()

        if status != 'success':
            agora.delegation_status['status'] = status
            agora.delegation_status['updated_at'] = timezone.now().isoformat()
            agora.save()
            return http.HttpResponse()

        director = get_object_or_404(Authority, pk=agora.delegation_status['director_id'])

        # The callback comes with all the needed data, but as it so happens that
        # it's not authenticated, so we get the data directly from the source
        pub_url = director.get_public_data(ssid, "publicKey_native")
        r = requests.post(director.url, data=json.dumps(payload), verify=False,
            cert=(settings.SSL_CERT_PATH,
                  settings.SSL_KEY_PATH))
        if r.status != 200 or r.text != publickey:
            return http.HttpResponse()

        agora.delegation_status['status'] = 'success'
        agora.delegation_status['pubkey'] = publickey
        agora.delegation_status['updated_at'] = timezone.now().isoformat()
        agora.save()
        return http.HttpResponse()

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(UpdateAgoraDelegationElectionView, self).dispatch(*args,
            **kwargs)