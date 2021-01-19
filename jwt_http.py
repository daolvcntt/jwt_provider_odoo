import simplejson as json
from odoo import http
from odoo.http import request, Response
from .validator import validator
from odoo.exceptions import AccessError, AccessDenied

return_fields = ['id', 'login', 'name', 'company_id']

class JwtHttp:

    def get_state(self):
        return {
            'd': request.session.db
        }

    def parse_request(self):
        http_method = request.httprequest.method
        try:
            body = http.request.params
        except Exception:
            body = {}

        headers = dict(list(request.httprequest.headers.items()))
        if 'wsgi.input' in headers:
            del headers['wsgi.input']
        if 'wsgi.errors' in headers:
            del headers['wsgi.errors']
        if 'HTTP_AUTHORIZATION' in headers:
            headers['Authorization'] = headers['HTTP_AUTHORIZATION']

        # extract token
        token = ''
        if 'Authorization' in headers:
            try:
                # Bearer token_string
                token = headers['Authorization'].split(' ')[1]
            except Exception:
                pass

        return http_method, body, headers, token

    def date2str(self, d, f='%Y-%m-%d %H:%M:%S'):
        """
        Convert datetime to string
            :param self: 
            :param d: datetime object
            :param f='%Y-%m-%d%H:%M:%S': string format
        """
        try:
            s = d.strftime(f)
        except:
            s = None
        finally:
            return s

    def response(self, success=True, message=None, data=None, code=200):
        """
        Create a HTTP Response for controller 
            :param success=True indicate this response is successful or not
            :param message=None message string
            :param data=None data to return
            :param code=200 http status code
        """
        payload = json.dumps({
            'success': success,
            'message': message,
            'data': data,
        }, encoding='utf-8')

        return Response(payload, status=code, headers=[
            ('Content-Type', 'application/json'),
        ])
    
    def success(self, success = True, message = None, data = None, code=200):
        return {
            'code': code,
            'success': success,
            'data': data
        }

    def response_500(self, message='Internal Server Error', data=None):
        return self.response(success=False, message=message, data=data, code=500)

    def response_404(self, message='404 Not Found', data=None):
        return self.response(success=False, message=message, data=data, code=404)

    def response_403(self, message='403 Forbidden', data=None):
        return self.response(success=False, message=message, data=data, code=403)

    def errcode(self, code, message=None):
        return self.response(success=False, code=code, message=message)

    def do_login(self, login, password):
        # get current db
        state = self.get_state()
        try:
            uid = request.session.authenticate(state['d'], login, password)

            if uid:
                # login success, generate token
                user = request.env.user.to_dict(True)
                token = validator.create_token(user, password)
                return self.response(data={ 'account': user, 'token_type': 'Bearer', 'access_token': token })
            else:
                return self.errcode(code=422, message='Incorrect Login')
        except AccessError as aee:
            return self.errcode(code=422, message= "Access error" % aee.name)
        except AccessDenied as ade:
            return self.errcode(code=422, message= "Email, password or db invalid")
        except Exception as e:
            return self.errcode(code=422, message= "Wrong database name {}".format((e)))
        

    def do_logout(self, token):
        self.cleanup()
        request.env['jwt_provider.access_token'].sudo().search([
            ('token', '=', token)
        ]).unlink()

    def cleanup(self):
        # Clean up things after success request
        # use logout here to make request as stateless as possible

        request.session.logout()


jwt_http = JwtHttp()