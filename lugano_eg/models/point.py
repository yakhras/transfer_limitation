# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta


class LuganoPoint(models.Model):
    _name = 'lugano.survey'
    _description = "Lugano Survey"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    

    # READONLYSTATES = {'done': [('readonly', True)], 'cancel': [('readonly', True)]}

    name = fields.Char(string='Point Title')
    number = fields.Char(string='Number', required=True, readonly=True, default="/")
    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('done', 'Done'),
    #     ('cancel', 'Cancelled'),
    # ], string='Status', copy=False, default='draft', states=READONLYSTATES, tracking=1)
    beans = fields.Boolean(string='Beans')
    beans_consume = fields.Char(string='Beans Monthly Consumption:')
    pod = fields.Boolean(string='Pod')
    pod_consume = fields.Char(string='Pod Monthly Consumption:')
    capsules = fields.Boolean(string='Capsules')
    capsules_consume = fields.Char(string='Capsules Monthly Consumption:')
    used_price = fields.Char(string='Used Coffee Price')
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
    used_brand_ids = fields.Many2many('coffee.brand', string="Used Coffee Brand")
    strength_ids = fields.Many2many('strength.point', string="Strength Points")
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
        tracking=40,
    )
    location = fields.Selection(
        [("main", "Main Street"),
         ("secondary", "Secondary Street"),
         ("mall", "Shopping Mall"),],
        default="main",
        required=True,
        string="Location",
        tracking=50,
    )
    space = fields.Selection(
        [("open", "Open"),
         ("close", "Close"),],
        default="open",
        required=True,
        string="Space",
        tracking=60,
    )
    hours = fields.Selection(
        [("half", "12 Hours"),
         ("full", "24 Hours"),],
        default="half",
        required=True,
        string="Working Hours",
        tracking=70,
    )
    start_date = fields.Datetime("Start Date", default=fields.Datetime.now)
    end_date = fields.Datetime("End Date", required=True,  default=fields.Datetime.now)
    note = fields.Text('Internal Notes')
    # project_id = fields.Many2one('project.project', 'Project', ondelete='restrict', states=READONLYSTATES)
    # sale_id = fields.Many2one('sale.order', string='Sale Order', states=READONLYSTATES, ondelete="set null")
    # task_id = fields.Many2one('project.task', string='Task', states=READONLYSTATES, ondelete="set null")
    # product_id = fields.Many2one('product.product', string='Product', states=READONLYSTATES, ondelete="set null")
    partner_id = fields.Many2one('res.partner', string='Customer', ondelete="cascade", required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id, readonly=True)

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
        return super(LuganoPoint, self).create(values)

    # def action_done(self):
    #     self.state = 'done'
    #     self.name = self.user_id.crm_team_member_ids.crm_team_id
        # self.name = self.env.user.crm_team_member_ids.crm_team_id

    # def action_draft(self):
    #     self.state = 'draft'

    # def action_cancel(self):
    #     self.state = 'cancel'

    # @api.onchange('beans')
    # def onchange_task_id(self):
    #     if self.beans:
    #         self.name


    def _visit_count(self):
        for rec in self: 
            rec.visit_count = self.env['lugano.visit'].search_count([('partner_id', '=', rec.id)])

    visit_count = fields.Integer(compute="_visit_count", readonly=True, string="Visits")

    def lugano_visit_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("lugano_eg.lugano_survey_track")
        action['domain'] = [('partner_id','=', self.id)]
        action['context'] = {
            'default_partner_id': self.id,
        }
        return action