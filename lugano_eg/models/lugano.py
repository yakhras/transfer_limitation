# -*- coding: utf-8 -*-

from odoo import models, fields
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class Survey(models.Model):
    _name = 'lugano.survey'   # Name the model
    _description = 'Lugano Survey'
    
    