from werkzeug.security import generate_password_hash, check_password_hash
from ..validator import validator
from odoo.http import request
from odoo import http
import datetime
import random
import json
import math
import jwt

import logging

_logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = ['password', 'password_crypt', 'new_password', 'create_uid', 'write_uid']


class JwtController(http.Controller):
    def key(self):
        return '8dxtZrbfRJQJd2NtPujww3OfwAUfKOXf'

    def _prepare_final_email_values(self, partner):
        mail_user = request.env['ir.mail_server'].sudo().search([('smtp_port', '=', 465)])
        user_access = request.env['db.connection'].sudo().search([("state", "=", "confirm")])
        subject = f"Password Changed Successfully"
        mail_obj = request.env['mail.mail']
        email_from = mail_user.smtp_user
        email_to = partner.email
        body_html = f"""
            <html>
            <body>
            <div style="margin:0px;padding: 0px;">
                <p style="padding: 0px; font-size: 13px;">
                    Hello {partner.name} !!,
                    <br/>
                    Your password was successfuly changed.
                    <br/> 
                    We are happy to serve you the best.
                    <br/>
                    .
                <br/>
                </p>

                <p>
                Best Regards
                    <br/>
                {user_access.user_id[0].company_id[0].name}</p>
            <br/>
            </div>
            </body>
            </html>
        """
        mail = mail_obj.sudo().create({
            'body_html': body_html,
            'subject': subject,
            'email_from': email_from,
            'email_to': email_to
        })
        mail.send()
        return mail

    def _prepare_otp_email_values(self, partner):
        mail_user = request.env['ir.mail_server'].sudo().search([('smtp_port', '=', 465)])
        user_access = request.env['db.connection'].sudo().search([("state", "=", "confirm")])
        mail_obj = request.env['mail.mail']
        email_from = mail_user.smtp_user
        subject = f"Forgot My Password"
        email_to = partner.email
        body_html = f"""
            <html>
            <body>
            <div style="margin:0px;padding: 0px;">
                <p style="padding: 0px; font-size: 13px;">
                    Hello {partner.name} !!,
                    <br/>
                    Your request to reset password was successfuly.
                    <br/>
                    user {partner.otp} to reset your Password
                    <br/> 
                    if you did not request for this ignore this message.
                    <br/>
                    .
                <br/>
                </p>

                <p>Best Regards
                    <br/>
                {user_access.user_id[0].company_id[0].name}</p>
            <br/>
            </div>
            </body>
            </html>
        """
        mail = mail_obj.sudo().create({
            'body_html': body_html,
            'subject': subject,
            'email_from': email_from,
            'email_to': email_to
        })
        mail.send()
        return mail

    def _prepare_registration_email_values(self, new_customer):
        mail_user = request.env['ir.mail_server'].sudo().search([('smtp_port', '=', 465)])
        user_access = request.env['db.connection'].sudo().search([("state", "=", "confirm")])
        mail_obj = request.env['mail.mail']
        email_from = mail_user.smtp_user
        subject = f"SuccessFully Registration"
        email_to = new_customer.email
        body_html = f"""
            <html>
            <body>
            <div style="margin:0px;padding: 0px;">
                <p style="padding: 0px; font-size: 13px;">
                    Hello {new_customer.name} !!,
                    <br/>
                    Your Account was successfuly Registered with us.
                    <br/>
                    We hope you will enjoy the best experience as
                    <br/> 
                    you track all your invoices and payments.
                    <br/>
                    .
                <br/>
                </p>

                <p>Best Regards
                    <br/>
                {user_access.user_id[0].company_id[0].name}</p>
            <br/>
            </div>
            </body>
            </html>
        """
        mail = mail_obj.sudo().create({
            'body_html': body_html,
            'subject': subject,
            'email_from': email_from,
            'email_to': email_to
        })
        mail.send()
        return mail

    @http.route('/api/login', type='json', auth='public', cors='*', method=['POST'])
    def login(self, **kw):
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        data = json.loads(request.httprequest.data)
        email = data['email']
        password = data['password']
        if not email:
            response = {
                'code': 400,
                'message': 'Email address cannot be empty'
            }
            return response
        if not password:
            response = {
                'code': 400,
                'message': 'Password cannot be empty'
            }
            return response
        partner = request.env['res.partner'].sudo().search([('email', '=', email)])
        if partner:
            user = check_password_hash(partner['password'], password)
            if user:
                payload = {
                    'exp': exp,
                    'iat': datetime.datetime.utcnow(),
                    'sub': partner['id'],
                    'lgn': partner['email'],
                    'name': partner['name'],
                    'vat': partner['vat'],
                    'phone': partner['phone'],
                }
                token = jwt.encode(payload, self.key(), algorithm='HS256')
                request.env['jwt_provider.access_token'].sudo().create(
                    {'partner_id': partner.id, 'expires': exp, 'token': token})
                return {
                    'phone': partner.phone,
                    'user_name': partner.name,
                    'email': partner.email,
                    'user_id': partner.id,
                    'token_type': 'Bearer',
                    'access_token': token,
                    'code': 200
                }

            else:
                return {
                    'code': 401,
                    'status': 'failed',
                    'message': 'Incorrect username or password'
                }
        else:
            return {
                'code': 401,
                'status': 'failed',
                'message': 'Email address does not'
            }

    @http.route('/api/password', type='json', auth='public', cors='*', method=['POST'])
    def forgot_my_password(self, **kw):
        digits = "0123456789"
        OTP = ""
        data = json.loads(request.httprequest.data)
        email = data['email']
        if not email:
            response = {
                'code': 400,
                'message': 'Email address cannot be empty'
            }
            return response
        partner = request.env['res.partner'].sudo().search([('email', '=', email)])
        if not partner:
            response = {
                'code': 400,
                'message': 'Email address does not exist'
            }
            return response
        if partner:
            for i in range(4):
                OTP += digits[math.floor(random.random() * 10)]
            partner.sudo().write({'otp': OTP})
            self._prepare_otp_email_values(partner)
        return {
            'code': 200,
            'status': 'success',
            'message': 'A code was Sent to your Email'
        }

    @http.route('/api/set/password', type='json', auth='public', cors='*', method=['POST'])
    def set_new_password(self, **kw):
        mail_user = request.env['ir.mail_server'].sudo().search([('smtp_port', '=', 465)])
        digits = "0123456789"
        OTP = ""
        data = json.loads(request.httprequest.data)
        code = data['code']
        password = generate_password_hash(data['password'], method='sha256')
        data['password'] = password
        if not code:
            response = {
                'code': 400,
                'message': 'Email address cannot be empty'
            }
            return response
        if not password:
            response = {
                'code': 400,
                'message': 'Password cannot be empty'
            }
            return response
        partner = request.env['res.partner'].sudo().search([('otp', '=', code)])
        if not partner:
            response = {
                'code': 400,
                'message': 'The Code is Invalid'
            }
            return response
        if partner:
            partner.sudo().write({'password': password})
            partner.sudo().write({'otp': ''})
            self._prepare_final_email_values(partner)
        return {
            'code': 400,
            'status': 'success',
            'message': 'Password Successfully changed'
        }

        # @http.route('/api/me', type='json', auth='public', cors="*", method=['POST'])

    # def me(self, **kw):
    #     http_method, body, headers, token = jwt_http.parse_request()
    #     _logger.error(token)
    #     result = validator.verify_token(token)
    #     _logger.error(result)
    #     if not result['status']:
    #         response = {
    #             'code':result['code'], 
    #             'message':result['message']
    #         }
    #         _logger.error(response)
    #         return response
    #     response = request.env["res.partner"].sudo().search([("id", "=", result['id'])])
    #     partner_details = {
    #         'email': response['email'],
    #         'name': response['name'],
    #         'phone': response['phone'],
    #         'country': response['country_id']['name'],
    #         'token': response['access_token_ids']['token']
    #     }
    #     resp = {
    #         'code':200, 
    #         'details':partner_details
    #     }
    #     return resp

    @http.route('/api/logout', type='json', auth='public', cors='*', method=['POST'])
    def logout(self, **kw):
        data = json.loads(request.httprequest.data)
        token = data['token']
        data.pop('token', None)
        result = validator.verify_token(token)
        if not result['status']:
            response = {
                'code': 400,
                'message': 'Logout Failed'
            }
            return response
        logout = request.env['jwt_provider.access_token'].sudo().search([('token', '=', token)])
        logout.sudo().unlink()
        response = {
            'code': 200,
            'message': 'Logout'
        }
        return response

    @http.route('/api/register', type='json', auth='public', cors='*', method=['POST'])
    def register(self, **kw):
        data = json.loads(request.httprequest.data)
        email = data['email']
        password = generate_password_hash(data['password'], method='sha256')
        data['password'] = password
        name = data['name']
        vat = data['vat']
        phone = data['phone']
        if not email:
            response = {
                'code': 422,
                'message': 'Email address cannot be empty'
            }
            return response
        if not vat:
            response = {
                'code': 422,
                'message': 'Tax Id cannot be empty'
            }
            return response
        if not name:
            response = {
                'code': 422,
                'message': 'Name cannot be empty'
            }
            _logger.error(response)
            return response
        if not password:
            response = {
                'code': 422,
                'message': 'Password cannot be empty'
            }
            return response
        if not phone:
            response = {
                'code': 422,
                'message': 'Phone cannot be empty'
            }
            return response
        if request.env["res.partner"].sudo().search([("email", "=", email)]):
            response = {
                'code': 422,
                'message': 'Email address already existed'
            }
            return response
        if request.env["res.partner"].sudo().search([("phone", "=", phone)]):
            response = {
                'code': 422,
                'message': 'Phone Number already existed'
            }
        if request.env["res.partner"].sudo().search([("vat", "=", vat)]):
            response = {
                'code': 422,
                'message': 'Tax Id already existed'
            }
        new_customer = request.env['res.partner'].sudo().create(data)
        if new_customer:
            self._prepare_registration_email_values(new_customer)
            response = {
                'code': 200,
                'message': {
                    'name': new_customer.name,
                    'number': new_customer.vat,
                    'email': new_customer.email,
                    'phone': new_customer.phone
                }
            }
        return response
