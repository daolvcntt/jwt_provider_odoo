import logging
import jwt
import re
import datetime
import traceback
import os
from odoo import http, service, registry, SUPERUSER_ID
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

regex = r"^[a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"


class Validator:
    def is_valid_email(self, email):
        return re.search(regex, email)

    def key(self):
        return os.environ.get('ODOO_JWT_KEY')

    def create_token(self, user, password):
        try:
            exp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            payload = {
                'exp': exp,
                'iat': datetime.datetime.utcnow(),
                'sub': user['id'],
                'lgn': user['email'],
                'password': password,
            }

            token = jwt.encode(
                payload,
                self.key(),
                algorithm='HS256'
            )

            self.save_token(token, user['id'], exp)

            return token.decode('utf-8')
        except Exception as ex:
            _logger.error(ex)
            raise

    def save_token(self, token, uid, exp):
        request.env['jwt_provider.access_token'].sudo().create({
            'user_id': uid,
            'expires': exp.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'token': token,
        })

    def verify(self, token):
        record = request.env['jwt_provider.access_token'].sudo().search([
            ('token', '=', token)
        ])

        if len(record) != 1:
            _logger.info('not found %s' % token)
            return False

        if record.is_expired:
            return False

        return record.user_id

    def verify_token(self, token):
    
        try:
            result = {
                'status': False,
                'message': None,
            }
            payload = jwt.decode(token, self.key(), [])
            if not self.verify(token):
                return self.errorToken()

            uid = request.session.authenticate(request.session.db, payload['lgn'], payload['password'])
            if not uid:
                return self.errorToken()

            result['status'] = True
            return result
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception) as e:
            return self.errorToken()

    def errorToken(self):
        return {
            'message': 'Token invalid or expired',
            'code': 498,
            'status': False
        }

validator = Validator()