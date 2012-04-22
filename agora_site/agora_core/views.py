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

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf.urls import patterns, url, include
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, CreateView
from django import http

from actstream.models import model_stream
from actstream.signals import action
from endless_pagination.views import AjaxListView

from agora_site.agora_core.models import Agora, Election, Profile
from agora_site.agora_core.forms import CreateAgoraForm, CreateElectionForm
from agora_site.misc.utils import RequestCreateView

class AgoraView(TemplateView):
    '''
    Shows an agora main page
    '''
    template_name = 'agora_core/agora_activity.html'

    def get_context_data(self, username, agoraname, **kwargs):
        context = super(AgoraView, self).get_context_data(**kwargs)
        context['agora'] = agora = get_object_or_404(Agora, name=agoraname,
            creator__username=username)
        context['activity'] = model_stream(agora)
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
    page_template='agora_core/user_list_page.html'

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

        action.send(self.request.user, verb='created', action_object=agora)

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
                target=election.agora)
        else:
            messages.add_message(self.request, messages.SUCCESS, _('Creation of '
                'Election <a href="%(election_url)s">%(electionname)s</a> in '
                '<a href="%(agora_url)s">%(username)s/%(agoraname)s</a> '
                'successful! Now it <strong>awaits the agora administrators '
                'approval</strong>.') % extra_data)

            action.send(self.request.user, verb='proposed', action_object=election,
                target=election.agora)
            # TODO: send notification to agora admins

        action.send(self.request.user, verb='created', action_object=election,
            target=election.agora)

        return reverse('election-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name, electionname=election.name))

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
        context['activity'] = model_stream(election)
        return context


class ExtraContextMetaMixin(object):

    def as_view(self, *args, **kwargs):
        context = super(ExtraContextMetaMixin, self).as_views(*args, **kwargs)
        return context
