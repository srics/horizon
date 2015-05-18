from django.core.urlresolvers import reverse
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api

import yaml


class OnBoardVNF(forms.SelfHandlingForm):
    name = forms.CharField(max_length=80, label=_("Name"), required=False)
    source_type = forms.ChoiceField(
        label=_('TOSCA Template Source'),
        required=False,
        choices=[('file', _('TOSCA Template File')),
                 ('raw', _('Direct Input'))],
        widget=forms.Select(
            attrs={'class': 'switchable', 'data-slug': 'source'}))

    toscal_file = forms.FileField(
        label=_("TOSCA Template File"),
        help_text=_("A local TOSCA template file to upload."),
        widget=forms.FileInput(
            attrs={'class': 'switched', 'data-switch-on': 'source',
                   'data-source-file': _('TOSCA Template File')}),
        required=False)

    direct_input = forms.CharField(
        label=_('TOSCA YAML'),
        help_text=_('The YAML formatted contents of a TOSCA template.'),
        widget=forms.widgets.Textarea(
            attrs={'class': 'switched', 'data-switch-on': 'source',
                   'data-source-raw': _('TOSCA YAML')}),
        required=False)


    def __init__(self, request, *args, **kwargs):
        super(OnBoardVNF, self).__init__(request, *args, **kwargs)

    def clean(self):
        data = super(OnBoardVNF, self).clean()

        # The key can be missing based on particular upload
        # conditions. Code defensively for it here...
        toscal_file = data.get('toscal_file', None)
        toscal_raw = data.get('direct_input', None)

        if toscal_raw and toscal_file:
            raise ValidationError(
                _("Cannot specify both file and direct input."))
        if not toscal_raw and not toscal_file:
            raise ValidationError(
                _("No input was provided for the namespace content."))
        try:
            if toscal_file:
                toscal_str = self.files['toscal_file'].read()
            else:
                toscal_str = data['direct_input']
            #toscal = yaml.loads(toscal_str)
            data['tosca'] = toscal_str
        except Exception as e:
            msg = _('There was a problem loading the namespace: %s.') % e
            raise forms.ValidationError(msg)

        return data

    def handle(self, request, data):
        try:
            toscal = data['tosca']
            print "VNFD TOSCA: " + toscal
            tosca_arg = { 'vnfd': {'vnfd': toscal}}
            vnfd_instance = api.tacker.create_vnfd(request, tosca_arg)
            print "VNFD Instance: " + str(vnfd_instance)
            print "VNFD name: " + vnfd_instance['vnfd']['name']
            messages.success(request,
                             _('VNF Catalog entry %s has been created.') % vnfd_instance['vnfd']['name'])
            return toscal
        except Exception as e:
            msg = _('Unable to create TOSCA. %s')
            msg %= e.message.split('Failed validating', 1)[0]
            exceptions.handle(request, message=msg)
            return False
