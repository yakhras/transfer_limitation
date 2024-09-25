# -*- coding: utf-8 -*-
# from odoo import http


# class LogisticsApp(http.Controller):
#     @http.route('/logistics_app/logistics_app', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/logistics_app/logistics_app/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('logistics_app.listing', {
#             'root': '/logistics_app/logistics_app',
#             'objects': http.request.env['logistics_app.logistics_app'].search([]),
#         })

#     @http.route('/logistics_app/logistics_app/objects/<model("logistics_app.logistics_app"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('logistics_app.object', {
#             'object': obj
#         })
