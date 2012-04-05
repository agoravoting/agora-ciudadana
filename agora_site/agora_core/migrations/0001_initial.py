# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Profile'
        db.create_table('agora_core_profile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('short_description', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('biography', self.gf('django.db.models.fields.TextField')()),
            ('user_type', self.gf('django.db.models.fields.CharField')(default='PASSWORD', max_length=50)),
            ('last_activity_read_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('extra', self.gf('agora_site.misc.utils.JSONField')(null=True)),
        ))
        db.send_create_signal('agora_core', ['Profile'])

        # Adding model 'Agora'
        db.create_table('agora_core_agora', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='created_agoras', to=orm['auth.User'])),
            ('delegation_election', self.gf('django.db.models.fields.related.ForeignKey')(related_name='delegation_agora', to=orm['auth.User'])),
            ('created_at_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, blank=True)),
            ('archived_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=70)),
            ('pretty_name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=140)),
            ('short_description', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('biography', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('image_url', self.gf('django.db.models.fields.URLField')(default='', max_length=200, blank=True)),
            ('is_vote_secret', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('election_type', self.gf('django.db.models.fields.CharField')(default='ONCE_CHOICE', max_length=50)),
            ('eligibility', self.gf('agora_site.misc.utils.JSONField')(null=True)),
            ('membership_policy', self.gf('django.db.models.fields.CharField')(default='ANYONE_CAN_JOIN', max_length=50)),
            ('extra_data', self.gf('agora_site.misc.utils.JSONField')(null=True)),
        ))
        db.send_create_signal('agora_core', ['Agora'])

        # Adding M2M table for field members on 'Agora'
        db.create_table('agora_core_agora_members', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('agora', models.ForeignKey(orm['agora_core.agora'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('agora_core_agora_members', ['agora_id', 'user_id'])

        # Adding M2M table for field admins on 'Agora'
        db.create_table('agora_core_agora_admins', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('agora', models.ForeignKey(orm['agora_core.agora'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('agora_core_agora_admins', ['agora_id', 'user_id'])

        # Adding model 'Election'
        db.create_table('agora_core_election', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('tiny_hash', self.gf('django.db.models.fields.CharField')(max_length=50, unique=True, null=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='created_elections', to=orm['auth.User'])),
            ('parent_election', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='children_elections', null=True, to=orm['agora_core.Election'])),
            ('created_at_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, blank=True)),
            ('last_modified_at_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('voting_starts_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_ends_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_extended_until_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('approved_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('frozen_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('archived_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('delegated_votes_frozen_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voters_frozen_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('result_tallied_at_date', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('result', self.gf('agora_site.misc.utils.JSONField')()),
            ('delegated_votes_result', self.gf('agora_site.misc.utils.JSONField')(null=True)),
            ('delegated_votes', self.gf('django.db.models.fields.related.ForeignKey')(related_name='related_elections', to=orm['agora_core.CastVote'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('short_description', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('choices', self.gf('agora_site.misc.utils.JSONField')()),
            ('is_vote_secret', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('election_type', self.gf('django.db.models.fields.CharField')(default='ONCE_CHOICE', max_length=50)),
            ('eligibility', self.gf('agora_site.misc.utils.JSONField')(null=True)),
            ('extra_data', self.gf('agora_site.misc.utils.JSONField')(null=True)),
        ))
        db.send_create_signal('agora_core', ['Election'])

        # Adding M2M table for field electorate on 'Election'
        db.create_table('agora_core_election_electorate', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('election', models.ForeignKey(orm['agora_core.election'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('agora_core_election_electorate', ['election_id', 'user_id'])

        # Adding model 'CastVote'
        db.create_table('agora_core_castvote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('voter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cast_votes', to=orm['auth.User'])),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cast_votes', to=orm['agora_core.Election'])),
            ('hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('tiny_hash', self.gf('django.db.models.fields.CharField')(max_length=50, unique=True, null=True)),
            ('data', self.gf('agora_site.misc.utils.JSONField')()),
            ('invalidated_at_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('casted_at_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('agora_core', ['CastVote'])

        # Adding unique constraint on 'CastVote', fields ['election', 'voter', 'casted_at_date']
        db.create_unique('agora_core_castvote', ['election_id', 'voter_id', 'casted_at_date'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'CastVote', fields ['election', 'voter', 'casted_at_date']
        db.delete_unique('agora_core_castvote', ['election_id', 'voter_id', 'casted_at_date'])

        # Deleting model 'Profile'
        db.delete_table('agora_core_profile')

        # Deleting model 'Agora'
        db.delete_table('agora_core_agora')

        # Removing M2M table for field members on 'Agora'
        db.delete_table('agora_core_agora_members')

        # Removing M2M table for field admins on 'Agora'
        db.delete_table('agora_core_agora_admins')

        # Deleting model 'Election'
        db.delete_table('agora_core_election')

        # Removing M2M table for field electorate on 'Election'
        db.delete_table('agora_core_election_electorate')

        # Deleting model 'CastVote'
        db.delete_table('agora_core_castvote')


    models = {
        'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'agora_core.agora': {
            'Meta': {'object_name': 'Agora'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'adminstrated_agoras'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'archived_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'biography': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'created_at_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_agoras'", 'to': "orm['auth.User']"}),
            'delegation_election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'delegation_agora'", 'to': "orm['auth.User']"}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'ONCE_CHOICE'", 'max_length': '50'}),
            'eligibility': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'extra_data': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'is_vote_secret': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'agoras'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'membership_policy': ('django.db.models.fields.CharField', [], {'default': "'ANYONE_CAN_JOIN'", 'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '70'}),
            'pretty_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '140'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'})
        },
        'agora_core.castvote': {
            'Meta': {'unique_together': "(('election', 'voter', 'casted_at_date'),)", 'object_name': 'CastVote'},
            'casted_at_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('agora_site.misc.utils.JSONField', [], {}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cast_votes'", 'to': "orm['agora_core.Election']"}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'tiny_hash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cast_votes'", 'to': "orm['auth.User']"})
        },
        'agora_core.election': {
            'Meta': {'object_name': 'Election'},
            'approved_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'archived_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'choices': ('agora_site.misc.utils.JSONField', [], {}),
            'created_at_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_elections'", 'to': "orm['auth.User']"}),
            'delegated_votes': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'related_elections'", 'to': "orm['agora_core.CastVote']"}),
            'delegated_votes_frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'delegated_votes_result': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'ONCE_CHOICE'", 'max_length': '50'}),
            'electorate': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'elections'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'eligibility': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'extra_data': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_vote_secret': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified_at_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'parent_election': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'children_elections'", 'null': 'True', 'to': "orm['agora_core.Election']"}),
            'result': ('agora_site.misc.utils.JSONField', [], {}),
            'result_tallied_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'tiny_hash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voters_frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'agora_core.profile': {
            'Meta': {'object_name': 'Profile'},
            'biography': ('django.db.models.fields.TextField', [], {}),
            'extra': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity_read_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'user_type': ('django.db.models.fields.CharField', [], {'default': "'PASSWORD'", 'max_length': '50'})
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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 4, 5, 16, 40, 44, 310482)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 4, 5, 16, 40, 44, 310405)'}),
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
