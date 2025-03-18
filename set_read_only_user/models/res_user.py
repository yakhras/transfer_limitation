from odoo.tools import pycompat
from odoo.tools.translate import _
import logging

from odoo import api, models, fields, tools, _, SUPERUSER_ID
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    readonly_user = fields.Boolean('Read Only User', help='Set True Means This User Is Readonly.')

    def set_readonly_user(self):
        self.write({'readonly_user': True})

    def unset_readonly_user(self):
        self.write({'readonly_user': False})


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    @tools.ormcache_context('self.env.uid', 'self.env.su', 'model', 'mode', 'raise_exception', keys=('lang',))
    def check(self, model, mode='read', raise_exception=True):
        if self.env.su:
            # User root have all accesses
            return True

        assert isinstance(model, str), 'Not a model name: %s' % (model,)
        assert mode in ('read', 'write', 'create', 'unlink'), 'Invalid access mode'
        user = self.env['res.users'].with_user(SUPERUSER_ID).browse(self._uid)

        # TransientModel records have no access rights, only an implicit access rule
        if model not in self.env:
            _logger.error('Missing model %s', model)
        elif self.env[model].is_transient():
            return True

        # We check if a specific rule exists
        self._cr.execute("""SELECT MAX(CASE WHEN perm_{mode} THEN 1 ELSE 0 END) FROM ir_model_access a
                              JOIN ir_model m ON (m.id = a.model_id) JOIN res_groups_users_rel gu ON (gu.gid = a.group_id)
                             WHERE m.model = %s AND gu.uid = %s AND a.active IS TRUE""".format(mode=mode), (model, self._uid,))
        r = self._cr.fetchone()[0]

        if not r:
            # there is no specific rule. We check the generic rule
            self._cr.execute("""SELECT MAX(CASE WHEN perm_{mode} THEN 1 ELSE 0 END) FROM ir_model_access a JOIN ir_model m ON (m.id = a.model_id)
                                 WHERE a.group_id IS NULL AND m.model = %s AND a.active IS TRUE""".format(mode=mode), (model,))
            r = self._cr.fetchone()[0]
        if user.readonly_user and mode != 'read' and model != 'res.users.log':
            r = 0
        if not r and raise_exception:
            groups = '\n'.join('\t- %s' % g for g in self.group_names_with_access(model, mode))
            msg_heads = {
                # Messages are declared in extenso so they are properly exported in translation terms
                'read': _("Sorry, you are not allowed to access documents of type '%(document_kind)s' (%(document_model)s)."),
                'write':  _("Sorry, you are not allowed to modify documents of type '%(document_kind)s' (%(document_model)s)."),
                'create': _("Sorry, you are not allowed to create documents of type '%(document_kind)s' (%(document_model)s)."),
                'unlink': _("Sorry, you are not allowed to delete documents of type '%(document_kind)s' (%(document_model)s)."),
            }
            msg_params = {
                'document_kind': self.env['ir.model']._get(model).name or model,
                'document_model': model,
            }
            if groups:
                msg_tail = _("This operation is allowed for the groups:\n%(groups_list)s")
                msg_params['groups_list'] = groups
            else:
                msg_tail = _("No group currently allows this operation.")
            msg_tail += u' - ({} {}, {} {})'.format(_('Operation:'), mode, _('User:'), self._uid)
            _logger.info('Access Denied by ACLs for operation: %s, uid: %s, model: %s', mode, self._uid, model)
            msg = '%s %s' % (msg_heads[mode], msg_tail)
            if user.readonly_user and mode != 'read':
                raise AccessError(_('You Have Just Readonly Access, You Can not Do Any Transaction.'))
            raise AccessError(msg % msg_params)
        return bool(r)
