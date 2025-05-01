from odoo import mmodels, fields, api

class CrmLead(models.Model):
  inherit = 'crm.lead'

  @api.model
  def write(self, vals):
    if 'stage_id' in vals:
      old_stages = {lead.id: lead.stage_id for lead in self}
      res = super().write(vals)
      for lead in self:
        if lead.stage_id and lead.id in old_stages and lead.stage_id != old_stages[lead.id]:
          message = "HI"
          self.env['bus.bus']._sendone(
            self.env.user.partner_id.id,
            'notification',
            {'type': 'info',
             'title': 'stage',
             'message': message,
             'sticky': True,
            }
          )
          return res
        return super().write(vals)
          
