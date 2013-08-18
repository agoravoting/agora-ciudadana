# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Agora.delegation_policy'
        db.add_column('agora_core_agora', 'delegation_policy',
                      self.gf('django.db.models.fields.CharField')(default='ALLOW_DELEGATION', max_length=50),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Agora.delegation_policy'
        db.delete_column('agora_core_agora', 'delegation_policy')


    models = {
        'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'geolocation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipaddr': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'agora_core.agora': {
            'Meta': {'unique_together': "(('name', 'creator'),)", 'object_name': 'Agora'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'administrated_agoras'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'archived_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'biography': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'comments_policy': ('django.db.models.fields.CharField', [], {'default': "'ANYONE_CAN_COMMENT'", 'max_length': '50'}),
            'created_at_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_agoras'", 'to': "orm['auth.User']"}),
            'delegation_election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'delegation_agora'", 'null': 'True', 'to': "orm['agora_core.Election']"}),
            'delegation_policy': ('django.db.models.fields.CharField', [], {'default': "'ALLOW_DELEGATION'", 'max_length': '50'}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'SIMPLE_DELEGATION'", 'max_length': '50'}),
            'eligibility': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'extra_data': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'is_vote_secret': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'agoras'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'membership_policy': ('django.db.models.fields.CharField', [], {'default': "'ANYONE_CAN_JOIN'", 'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'pretty_name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'agora_core.castvote': {
            'Meta': {'unique_together': "(('election', 'voter', 'casted_at_date'),)", 'object_name': 'CastVote'},
            'action_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'null': 'True'}),
            'casted_at_date': ('django.db.models.fields.DateTimeField', [], {}),
            'data': ('agora_site.misc.utils.JSONField', [], {}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cast_votes'", 'to': "orm['agora_core.Election']"}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'is_counted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_direct': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tiny_hash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cast_votes'", 'to': "orm['auth.User']"})
        },
        'agora_core.delegateelectioncount': {
            'Meta': {'unique_together': "(('election', 'delegate'),)", 'object_name': 'DelegateElectionCount'},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'count_percentage': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'created_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 8, 18, 0, 0)', 'auto_now_add': 'True', 'blank': 'True'}),
            'delegate': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'delegate_election_counts'", 'to': "orm['auth.User']"}),
            'delegate_vote': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'delegate_election_count'", 'null': 'True', 'to': "orm['agora_core.CastVote']"}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'delegate_election_counts'", 'to': "orm['agora_core.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'agora_core.election': {
            'Meta': {'object_name': 'Election'},
            'agora': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'elections'", 'null': 'True', 'to': "orm['agora_core.Agora']"}),
            'approved_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'archived_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'comments_policy': ('django.db.models.fields.CharField', [], {'default': "'ANYONE_CAN_COMMENT'", 'max_length': '50'}),
            'created_at_date': ('django.db.models.fields.DateTimeField', [], {}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_elections'", 'to': "orm['auth.User']"}),
            'delegated_votes': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'delegated_votes'", 'symmetrical': 'False', 'to': "orm['agora_core.CastVote']"}),
            'delegated_votes_frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'SIMPLE_DELEGATION'", 'max_length': '50'}),
            'electorate': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'elections'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'eligibility': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'extra_data': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_vote_secret': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified_at_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'parent_election': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'children_elections'", 'null': 'True', 'to': "orm['agora_core.Election']"}),
            'pretty_name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'questions': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'result': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'result_tallied_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'tiny_hash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'voters_frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'voting_extended_until_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'})
        },
        'agora_core.profile': {
            'Meta': {'object_name': 'Profile'},
            'biography': ('django.db.models.fields.TextField', [], {}),
            'email_updates': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'extra': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lang_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '5'}),
            'last_activity_read_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['agora_core']