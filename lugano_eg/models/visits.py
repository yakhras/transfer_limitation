# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta


class LuganoSurvey(models.Model):
    _name = 'lugano.survey'
    _description = "Lugano Survey"
    

    READONLYSTATES = {'done': [('readonly', True)], 'cancel': [('readonly', True)]}

    name = fields.Char(string='Visit Title', states=READONLYSTATES)
    number = fields.Char(string='Number', required=True, readonly=True, default="/")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, default='draft', states=READONLYSTATES, tracking=1)
    beans = fields.Boolean(string='Beans')
    pod = fields.Boolean(string='Pod')
    capsule = fields.Boolean(string='Capsules')
    machine_station = fields.Selection(
        [("no_need", "No Need"),
         ("repair", "Need Repair"),
         ("free", "Need Machines for Free"),
         ("grinder", "Need Machines & Grinder"),],
        default="no_need",
        required=True,
        string="Machine Stations",
        tracking=20,
    )
    location_type = fields.Selection(
        [("shop", "Coffee Shop"),
         ("restaurant", "Restaurant"),
         ("bar", "Bar"),
         ("work", "Working Space"),
         ("kiosk", "Kiosk"),
         ("beauty", "Beauty Center"),
         ("hotel", "Hotel"),
         ("ship", "Ship (Safina)"),
         ("company", "Company"),
         ("barber", "Barber"),
         ("gold", "Gold Dealers"),],
        default="shop",
        required=True,
        string="Location Type",
        tracking=30,
    )
    # start_date = fields.Datetime("Start Date", states=READONLYSTATES, default=fields.Datetime.now)
    # end_date = fields.Datetime("End Date", required=True, states=READONLYSTATES, default=fields.Datetime.now)
    # note = fields.Text('Internal Notes', states=READONLYSTATES)
    # project_id = fields.Many2one('project.project', 'Project', ondelete='restrict', states=READONLYSTATES)
    # sale_id = fields.Many2one('sale.order', string='Sale Order', states=READONLYSTATES, ondelete="set null")
    # task_id = fields.Many2one('project.task', string='Task', states=READONLYSTATES, ondelete="set null")
    # product_id = fields.Many2one('product.product', string='Product', states=READONLYSTATES, ondelete="set null")
    partner_id = fields.Many2one('res.partner', string='Customer', states=READONLYSTATES, ondelete="cascade", required=True)
    # user_id = fields.Many2one('res.users', string='User', states=READONLYSTATES, default=lambda self: self.env.user.id)

    # _sql_constraints = [
    #     ('date_check2', "CHECK (start_date <= end_date)", "The start date must be anterior to the end date."),
    # ]

    # def unlink(self):
    #     for rec in self:
    #         if rec.state not in ('draft', 'cancel'):
    #             raise UserError(_('You cannot delete an record which is not draft or cancelled.'))
    #     return super(Visit, self).unlink()

    @api.model
    def create(self, values):
        values['number'] = self.env['ir.sequence'].next_by_code('lugano.survey') or '/'
        return super(LuganoSurvey, self).create(values)

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    # @api.onchange('task_id')
    # def onchange_task_id(self):
    #     if self.task_id:
    #         self.product_id = self.task_id.sale_line_id and self.task_id.sale_line_id.product_id.id or False