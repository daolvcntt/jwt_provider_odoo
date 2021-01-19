import werkzeug

from odoo.exceptions import AccessDenied
from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)

from ..validator import validator

class Users(models.Model):
    _inherit = "res.users"

    access_token_ids = fields.One2many(
        string='Access Tokens',
        comodel_name='jwt_provider.access_token',
        inverse_name='user_id',
    )

    avatar = fields.Char(compute='_compute_avatar')

    @api.depends()
    def _compute_avatar(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for u in self:
            u.avatar = werkzeug.urls.url_join(base, 'web/avatar/%d' % u.id)

    def to_dict(self, single=False):
        res = []
        for u in self:
            d = u.read(['email', 'name', 'avatar', 'lang', 'tz', 'phone', 'city', 'street', 'state_id', 'partner_id'])[0]
            res.append(d)

        return res[0] if single else res