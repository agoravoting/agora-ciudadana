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

from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, RedirectView
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy  as _

from endless_pagination.views import AjaxListView

from agora_site.agora_core.views import *
from agora_site.misc.utils import RequestCreateView

urlpatterns = patterns('',
    url(r'^$', HomeView.as_view(), name='home'),

    url(r'^misc/set-language/(?P<language>[\-\w]+)/?$', SetLanguageView.as_view(), name="set-language"),

    url(r'^agora/new/?$', CreateAgoraView.as_view(), name='agora-new'),

    url(r'^agoras/list/?$', SearchView.as_view(searchmodel="agoras"), name='agora-list'),

    url(r'^elections/list/?$', SearchView.as_view(searchmodel="elections"), name='election-list'),

    url(r'^user/list/?$', SearchView.as_view(searchmodel="profiles"), name='user-list'),

    url(r'^agora/list/?$', SearchView.as_view(searchmodel="agoras"), name='agora-list'),

    url(r'^search/?$', SearchView.as_view(), name='search-view'),

    url(r'^contact/?$', ContactView.as_view(), name='contact'),

    url(r'^user/(?P<username>[\.\w]+)/?$', UserView.as_view(), name='user-view'),

    url(r'^user/(?P<username>[\.\w]+)/biography/?$', UserBiographyView.as_view(), name='user-bio'),

    url(r'^user/(?P<username>[\.\w]+)/elections/(?P<election_filter>open|participated|requested)/?$',
        UserElectionsView.as_view(), name='user-elections'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/?$',
        AgoraView.as_view(), name='agora-view'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/elections/(?P<election_filter>open|all|approved|requested|tallied)/?$',
        AgoraElectionsView.as_view(), name='agora-elections'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/biography/?$',
        AgoraBiographyView.as_view(), name='agora-bio'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/admin/?$',
        AgoraAdminView.as_view(), name='agora-admin'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/members/(?P<members_filter>all|delegates)/?$',
        AgoraMembersView.as_view(), name='agora-members'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/comments/?$',
        AgoraCommentsView.as_view(), name='agora-comments'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/comments/post/?$',
        AgoraPostCommentView.as_view(), name='agora-comments-post'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/action/delegate/(?P<delegate_username>[\.\w]+)/?$',
        AgoraActionChooseDelegateView.as_view(), name='agora-action-choose-delegate'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/action/join/?$',
        AgoraActionJoinView.as_view(), name='agora-action-join'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/action/leave/?$',
        AgoraActionLeaveView.as_view(), name='agora-action-leave'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/action/leave-admin/?$',
        AgoraActionRemoveAdminMembershipView.as_view(),
        name='agora-action-leave-admin'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/new/?$',
        CreateElectionView.as_view(), name='election-new'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/?$',
        ElectionView.as_view(), name='election-view'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/edit/?$',
        EditElectionView.as_view(), name='election-edit'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/comments/?$',
        ElectionCommentsView.as_view(), name='election-comments'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/comments/post/?$',
        ElectionPostCommentView.as_view(), name='election-comments-post'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/delegates/?$',
        ElectionDelegatesView.as_view(), name='election-delegates'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/delegate/(?P<delegate_username>[\.\w]+)/?$',
        ElectionChooseDelegateView.as_view(), name='election-delegate'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/votes/?$',
        ElectionVotesView.as_view(), name='election-votes'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/action/start/?$',
        StartElectionView.as_view(), name='election-action-start'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/action/stop/?$',
        StopElectionView.as_view(), name='election-action-stop'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/action/archive/?$',
        ArchiveElectionView.as_view(), name='election-action-archive'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/action/vote/?$',
        VoteView.as_view(), name='election-vote'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/action/cancel_vote/?$',
        CancelVoteView.as_view(), name='election-cancel-vote'),
)

# Some redirects
urlpatterns += patterns('',
    url(r'^misc/link/twitter$', RedirectView.as_view(
        url= "https://twitter.com/#!/agoraciudadana"), name='twitter'
    ),

    url(r'^misc/link/facebook$', RedirectView.as_view(
        url= "https://www.facebook.com/pages/Partido-de-Internet-PDI/168786883166140"),
        name='facebook'
    ),

    url(r'^misc/link/identica$', RedirectView.as_view(
        url= "https://identi.ca/search/notice?q=agoraciudadana"), name='identica'
    ),

    url(r'^misc/link/google-plus$', RedirectView.as_view(
        url= "https://plus.google.com/s/agora%20ciudadana"), name='google-plus'
    ),

    url(r'^misc/link/libre-software$', RedirectView.as_view(
        url= "https://github.com/agoraciudadana/agora-ciudadana"), name='libre-software'
    ),

    url(r'^misc/link/blog$', RedirectView.as_view(
        url= "https://agoraciudadana.org"), name='blog'
    ),

    url(r'^misc/link/status$', RedirectView.as_view(
        url= "https://agoraciudadana.org"), name='status'
    ),
)

urlpatterns += patterns('django.contrib.flatpages.views',
    url(r'^misc/page/about/?$', 'flatpage', {'url': '/about/'}, name='about'),

    url(r'^misc/page/libre-software/?$', 'flatpage',
        {'url': '/libre-software/'}, name='libre-software'),

    url(r'^misc/page/terms-of-service/?$', 'flatpage',
        {'url': '/terms-of-service/'}, name='terms-of-service'),

    url(r'^misc/page/privacy-policy/?$', 'flatpage',
        {'url': '/privacy-policy/'}, name='privacy-policy'),

    url(r'^misc/page/security/?$', 'flatpage', {'url': '/security/'},
        name='security'),
)