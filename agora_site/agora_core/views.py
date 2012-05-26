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

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf.urls import patterns, url, include
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives, EmailMessage, send_mail, send_mass_mail
from django.utils import simplejson as json
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import TemplateView, ListView, CreateView, FormView
from django.views.i18n import set_language as django_set_language
from django import http

from actstream.actions import follow, unfollow, is_following
from actstream.models import object_stream, election_stream, Action, user_stream
from actstream.signals import action
from endless_pagination.views import AjaxListView

from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora
from agora_site.agora_core.models import Agora, Election, Profile, CastVote
from agora_site.agora_core.forms import (CreateAgoraForm, CreateElectionForm,
    VoteForm)
from agora_site.misc.utils import (RequestCreateView, geolocate_ip,
    get_protocol, get_base_email_context, send_mass_html_mail)

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

        return django_set_language(self.request)

class HomeView(AjaxListView):
    '''
    Shows main page. It's different for non-logged in users and logged in users:
    for the former, we show a carousel of news nicely geolocated in a map; for
    the later, we show the user's activity stream along with the calendar of
    relevant elections and the like at the sidebar.
    '''
    template_name = 'agora_core/home_activity.html'
    template_name_logged_in = 'agora_core/home_loggedin_activity.html'
    page_template = 'agora_core/agora_activity_page.html'

    def get_queryset(self):
        if self.request.user.is_authenticated() and not self.request.user.is_anonymous():
            # change template
            self.template_name = self.template_name_logged_in
            return user_stream(self.request.user)
        else:
            return Action.objects.public()[:10]


class AgoraView(AjaxListView):
    '''
    Shows an agora main page
    '''
    template_name = 'agora_core/agora_activity.html'
    page_template = 'agora_core/agora_activity_page.html'

    def get_queryset(self):
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]

        self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        return object_stream(self.agora)

    def get(self, request, *args, **kwargs):
        self.kwargs = kwargs
        return super(AgoraView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AgoraView, self).get_context_data(**kwargs)
        context['agora'] = self.agora
        return context

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

class AgoraMembersView(AjaxListView):
    '''
    Shows the biography of an agora
    '''
    template_name = 'agora_core/agora_members.html'
    page_template = 'agora_core/user_list_page.html'

    def get_queryset(self):
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]

        self.agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        return self.agora.members.all()

    def get(self, request, *args, **kwargs):
        self.kwargs = kwargs
        return super(AgoraMembersView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AgoraMembersView, self).get_context_data(**kwargs)
        context['agora'] = self.agora

        return context

class ElectionDelegatesView(AjaxListView):
    '''
    Shows the biography of an agora
    '''
    template_name = 'agora_core/election_delegates.html'
    page_template = 'agora_core/delegate_list_page.html'

    def get_queryset(self):
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]
        electionname = self.kwargs["electionname"]
        self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)
        return self.election.get_votes_from_delegates().all()

    def get(self, request, *args, **kwargs):
        self.kwargs = kwargs
        return super(ElectionDelegatesView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ElectionDelegatesView, self).get_context_data(**kwargs)
        context['election'] = self.election
        context['vote_form'] = VoteForm(self.request.POST, self.election)
        return context

class ElectionChooseDelegateView(AjaxListView):
    '''
    Shows the biography of an agora
    '''
    template_name = 'agora_core/election_choose_delegate.html'
    page_template = 'agora_core/delegate_list_page.html'

    def get_queryset(self):
        return self.election.get_votes_from_delegates().all()

    def get(self, request, *args, **kwargs):
        return super(ElectionChooseDelegateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ElectionChooseDelegateView, self).get_context_data(**kwargs)
        context['election'] = self.election
        context['delegate'] = self.delegate
        context['vote'] = self.vote
        context['vote_form'] = VoteForm(self.request.POST, self.election)
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.kwargs = kwargs
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]
        electionname = self.kwargs["electionname"]
        delegate_username = self.kwargs["delegate_username"]
        self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        # TODO: if election is closed, show the delegate view for the agora
        # instead. Also, you cannot delegate to yourself
        #if not self.election.ballot_is_open()\
            #or delegation_username == self.request.username:
            #return reverse('agora-delegate', username, agoraname, delegate_username)

        self.delegate = get_object_or_404(User, username=delegate_username)
        self.vote = get_object_or_404(CastVote, is_counted=True,
            election=self.election, invalidated_at_date=None,
            voter=self.delegate)

        return super(ElectionChooseDelegateView, self).dispatch(*args, **kwargs)

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

    def get_success_url(self):
        '''
        After creating the agora, show it
        '''
        agora = self.object

        messages.add_message(self.request, messages.SUCCESS, _('Creation of '
            'Agora %(agoraname)s successful! Now start to configure and use '
            'it.') % dict(agoraname=agora.name))

        action.send(self.request.user, verb='created', action_object=agora,
            ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        follow(self.request.user, agora, actor_only=False)

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
            username=election.agora.creator.username,
            agoraname=election.agora.name,
            election_url=election.url,
            agora_url=reverse('agora-view', kwargs=dict(
                username=election.agora.creator.username,
                agoraname=election.agora.name))
        )

        if election.is_approved:
            messages.add_message(self.request, messages.SUCCESS, _('Creation of '
                'Election <a href="%(election_url)s">%(electionname)s</a> in '
                '<a href="%(agora_url)s">%(username)s/%(agoraname)s</a> '
                'successful!') % extra_data)

            action.send(self.request.user, verb='created', action_object=election,
                target=election.agora, ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))
        else:
            messages.add_message(self.request, messages.SUCCESS, _('Creation of '
                'Election <a href="%(election_url)s">%(electionname)s</a> in '
                '<a href="%(agora_url)s">%(username)s/%(agoraname)s</a> '
                'successful! Now it <strong>awaits the agora administrators '
                'approval</strong>.') % extra_data)

            action.send(self.request.user, verb='proposed', action_object=election,
                target=election.agora, ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        context = get_base_email_context(self.request)

        context.update(dict(
            election=election,
            action_user_url='/%s' % election.creator.username,
        ))

        for admin in election.agora.admins.all():
            context['to'] = admin

            email = EmailMultiAlternatives(
                subject=_('Election %s created') % election.pretty_name,
                body=render_to_string('agora_core/emails/election_created.txt',
                    context),
                to=[admin.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/election_created.html',
                    context), "text/html")
            email.send()

        follow(self.request.user, election, actor_only=False)

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

class ElectionView(TemplateView):
    '''
    Shows an election main page
    '''
    template_name = 'agora_core/election_activity.html'

    def get_context_data(self, username, agoraname, electionname, **kwargs):
        context = super(ElectionView, self).get_context_data(**kwargs)
        context['election'] = election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)
        context['vote_form'] = VoteForm(self.request.POST, election)
        context['activity'] = election_stream(election)
        return context

class StartElectionView(FormActionView):
    def post(self, request, username, agoraname, electionname, *args, **kwargs):
        election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)

        if not election.has_perms('begin_election', request.user):
            messages.add_message(self.request, messages.ERROR, _('You don\'t '
                'have permission to begin the election.'))
            return self.go_next(request)

        election.voting_starts_at_date = datetime.datetime.now()
        election.create_hash()
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

        # NOTE: for now, electorate is dynamic and just taken from the election's
        # agora members' list
        for voter in election.agora.members.all():
            context['to'] = voter
            try:
                context['delegate'] = get_delegate_in_agora(voter, election.agora)
            except:
                pass
            datatuples.append((
                _('Vote in election %s') % election.pretty_name,
                render_to_string('agora_core/emails/election_started.txt',
                    context),
                render_to_string('agora_core/emails/election_started.html',
                    context),
                None,
                [voter.email]))

        # Also notify third party delegates
        for voter in election.agora.active_nonmembers_delegates():
            context['to'] = voter
            datatuples.append((
                _('Vote in election %s') % election.pretty_name,
                render_to_string('agora_core/emails/election_started.txt',
                    context),
                render_to_string('agora_core/emails/election_started.html',
                    context),
                None,
                [voter.email]))

        send_mass_html_mail(datatuples)

        if not is_following(self.request.user, election):
            follow(self.request.user, election, actor_only=False)

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

        election.voting_extended_until_date = election.voting_ends_at_date = datetime.datetime.now()
        election.save()
        election.compute_result()

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
            context['to'] = vote.voter
            try:
                context['delegate'] = get_delegate_in_agora(vote.voter, election.agora)
            except:
                pass
            datatuples.append((
                _('Election results for %s') % election.pretty_name,
                render_to_string('agora_core/emails/election_results.txt',
                    context),
                render_to_string('agora_core/emails/election_results.html',
                    context),
                None,
                [vote.voter.email]))

        send_mass_html_mail(datatuples)

        action.send(self.request.user, verb='published results', action_object=election,
            target=election.agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=geolocate_ip(request.META.get('REMOTE_ADDR')))

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(StopElectionView, self).dispatch(*args, **kwargs)

class VoteView(CreateView):
    '''
    Creates a new agora
    '''
    template_name = 'agora_core/vote_form.html'
    form_class = VoteForm

    def get_form_kwargs(self):
        form_kwargs = super(VoteView, self).get_form_kwargs()
        username = self.kwargs["username"]
        agoraname = self.kwargs["agoraname"]
        electionname = self.kwargs["electionname"]
        form_kwargs["request"] = self.request
        form_kwargs["election"] = self.election = get_object_or_404(Election,
            name=electionname, agora__name=agoraname,
            agora__creator__username=username)
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
            follow(self.request.user, self.election, actor_only=False)

        return reverse('election-view',
            kwargs=dict(username=self.election.agora.creator.username,
                agoraname=self.election.agora.name, electionname=self.election.name))

    def get_context_data(self, **kwargs):
        context = super(VoteView, self).get_context_data(**kwargs)
        form = kwargs['form']
        context['vote_form'] = form
        context['election'] = form.election
        context['activity'] = election_stream(form.election)
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
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
            is_direct=False, invalidated_at_date=None)
        for old_vote in old_votes:
            old_vote.invalidated_at_date = datetime.datetime.now()
            old_vote.save()

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
        vote.is_public = True
        vote.casted_at_date = datetime.datetime.now()
        vote.create_hash()
        vote.save()

        action.send(self.request.user, verb='delegated', action_object=vote,
            target=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=geolocate_ip(request.META.get('REMOTE_ADDR')))

        vote.action_id = Action.objects.filter(actor_object_id=self.request.user.id,
            verb='delegated', action_object_object_id=vote.id,
            target_object_id=agora.id).order_by('-timestamp').all()[0].id

        # TODO: send an email to the user
        messages.add_message(self.request, messages.SUCCESS, _('You delegated '
            'your vote in %(agora)s to %(username)s! Now you could share this '
            'in Facebook, Google Plus, Twitter, etc.') % dict(
                agora=agora.creator.username+'/'+agora.name,
                username=delegate.username))

        if not is_following(self.request.user, delegate):
            follow(self.request.user, delegate, actor_only=False)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionChooseDelegateView, self).dispatch(*args, **kwargs)

class AgoraActionJoinView(FormActionView):
    def post(self, request, username, agoraname, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)

        if not agora.has_perms('join', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have permission to join this agora.'))
            return self.go_next(request)

        if request.user in agora.members.all():
            messages.add_message(request, messages.ERROR, _('Guess what, you '
                'are already a member of %(agora)s!' %\
                    dict(agora=username+'/'+agoraname)))
            return self.go_next(request)

        agora.members.add(request.user)
        agora.save()

        action.send(request.user, verb='joined', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=geolocate_ip(request.META.get('REMOTE_ADDR')))

        # TODO: send an email to the user
        messages.add_message(request, messages.SUCCESS, _('You joined '
            '%(agora)s. Now you could take a look at what elections are '
            'available at this agora') % dict(
                agora=agora.creator.username+'/'+agora.name))

        if not is_following(request.user, agora):
            follow(request.user, agora, actor_only=False)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionJoinView, self).dispatch(*args, **kwargs)


class AgoraActionLeaveView(FormActionView):
    def post(self, request, username, agoraname, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)

        if not agora.has_perms('leave', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have permission to leave this agora.'))
            return self.go_next(request)

        if request.user not in agora.members.all():
            messages.add_message(request, messages.ERROR, _('Guess what, you '
                'are already not a member of %(agora)s!' %\
                    dict(agora=username+'/'+agoraname)))
            return self.go_next(request)

        agora.members.remove(request.user)
        agora.save()

        action.send(request.user, verb='left', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=geolocate_ip(request.META.get('REMOTE_ADDR')))

        # TODO: send an email to the user
        messages.add_message(request, messages.SUCCESS, _('You left '
            '%(agora)s.') % dict(agora=agora.creator.username+'/'+agora.name))

        if is_following(self.request.user, agora):
            unfollow(self.request.user, agora)

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionLeaveView, self).dispatch(*args, **kwargs)

class AgoraActionRemoveAdminMembershipView(FormActionView):
    def post(self, request, username, agoraname, *args, **kwargs):
        agora = get_object_or_404(Agora,
            name=agoraname, creator__username=username)

        if not agora.has_perms('leave', request.user):
            messages.add_message(request, messages.ERROR, _('Sorry, you '
                'don\'t have permission to leave this agora.'))
            return self.go_next(request)

        if request.user not in agora.admins.all():
            messages.add_message(request, messages.ERROR, _('Guess what, you '
                'are already not an admin member of %(agora)s!' %\
                    dict(agora=username+'/'+agoraname)))
            return self.go_next(request)

        agora.admins.remove(request.user)
        agora.save()

        action.send(request.user, verb='removed admin membership',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=geolocate_ip(request.META.get('REMOTE_ADDR')))

        # TODO: send an email to the user
        messages.add_message(request, messages.SUCCESS, _('You removed your '
            'admin membership at %(agora)s.') % dict(agora=agora.creator.username+'/'+agora.name))

        return self.go_next(request)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AgoraActionRemoveAdminMembershipView, self).dispatch(*args, **kwargs)
