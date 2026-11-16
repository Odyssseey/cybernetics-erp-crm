from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .copy import COPY_CONDITIONS


class LibraryReturnWizard(models.TransientModel):
    _name = 'library.return.wizard'
    _description = 'Оформлення повернення примірника'

    loan_id = fields.Many2one(
        'library.loan', string='Видача', required=True, ondelete='cascade',
    )
    condition_on_return = fields.Selection(
        COPY_CONDITIONS, string='Стан під час повернення', required=True,
    )
    notes = fields.Text(string='Коментар бібліотекаря')

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        context = self.env.context
        if 'loan_id' in fields_list and not defaults.get('loan_id') and context.get('active_model') == 'library.loan':
            defaults['loan_id'] = context.get('active_id')
        if 'condition_on_return' in fields_list and defaults.get('loan_id') and not defaults.get('condition_on_return'):
            loan = self.env['library.loan'].browse(defaults['loan_id'])
            defaults['condition_on_return'] = loan.copy_id.condition
        return defaults

    def action_confirm(self):
        self.ensure_one()
        self.check_access('write')
        loan = self.loan_id
        loan.check_access('write')
        if not loan.try_lock_for_update(allow_referencing=True):
            raise UserError(_('Цю видачу вже обробляє інший користувач. Спробуйте ще раз.'))
        if loan.state != 'active':
            raise UserError(_('Оформити повернення можна лише для активної видачі.'))

        copy = loan.copy_id
        copy.check_access('write')
        loan.write({'state': 'returned', 'return_date': fields.Date.today()})
        copy.condition = self.condition_on_return
        return {'type': 'ir.actions.act_window_close'}
