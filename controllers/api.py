# -*- coding: utf-8 -*-
import werkzeug
import jwt
from odoo import http
from odoo.http import request, Response
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.exceptions import UserError

from ..validator import validator
from ..jwt_http import jwt_http

import logging
_logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = ['password', 'password_crypt', 'new_password', 'create_uid', 'write_uid']


class JwtController(http.Controller):
    # test route
    @http.route('/api/info', type='http', auth='none', methods=["GET"], csrf=False, cors='*')
    def index(self, **kw):
        return 'Hello, world'

    @http.route('/api/login', type='http', auth='public', csrf=False, cors='*')
    def login(self, email=None, password=None, **kw):
        if not email:
            return jwt_http.errcode(code=422, message='Email address cannot be empty')
        if not password:
            return jwt_http.errcode(code=422, message='Password cannot be empty')

        return jwt_http.do_login(email, password)

    @http.route('/api/me', type='http', auth='public', csrf=False, cors="*")
    def me(self, **kw):
        http_method, body, headers, token = jwt_http.parse_request()
        result = validator.verify_token(token)
        if not result['status']:
            return jwt_http.errcode(code=result['code'], message=result['message'])

        return jwt_http.response(data=request.env.user.to_dict(True))

    @http.route('/api/logout', type='http', auth='public', csrf=False, cors='*')
    def logout(self, **kw):
        http_method, body, headers, token = jwt_http.parse_request()
        result = validator.verify_token(token)
        if not result['status']:
            return jwt_http.errcode(code=result['code'], message=result['message'])

        jwt_http.do_logout(token)
        return jwt_http.response()

    @http.route('/api/register', type='http', auth='public', csrf=False, methods=['POST'], cors='*')
    def register(self, email=None, name=None, password=None, **kw):
        if not email:
            return jwt_http.errcode(code=422, message='Email address cannot be empty')
        if not validator.is_valid_email(email):
            return jwt_http.errcode(code=422, message='Invalid email address')
        if not name:
            return jwt_http.errcode(code=422, message='Name cannot be empty')
        if not password:
            return jwt_http.errcode(code=422, message='Password cannot be empty')

        # sign up
        try:
            self._signup_with_values(login=email, name=name, password=password)
        except AttributeError:
            return jwt_http.errcode(code=501, message='Signup is disabled')
        except (SignupError, AssertionError) as e:
            if request.env["res.users"].sudo().search([("login", "=", email)]):
                return jwt_http.errcode(code=422, message='Email address already existed')
            else:
                return jwt_http.response_500()
        except Exception as e:
            _logger.error(str(e))
            return jwt_http.response_500()
        # log the user in
        return jwt_http.do_login(email, password)

    def _signup_with_values(self, **values):
        request.env['res.users'].sudo().signup(values, None)
        request.env.cr.commit()     # as authenticate will use its own cursor we need to commit the current transaction
        self.signup_email(values)


    def signup_email(self, values):
        user_sudo = request.env['res.users'].sudo().search([('login', '=', values.get('login'))])
        template = request.env.ref('auth_signup.mail_template_user_signup_account_created', raise_if_not_found=False)
        if user_sudo and template:
            template.sudo().with_context(
                lang=user_sudo.lang,
                auth_login=werkzeug.url_encode({'auth_login': user_sudo.email}),
            ).send_mail(user_sudo.id, force_send=True)
