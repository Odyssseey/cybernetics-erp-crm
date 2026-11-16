from odoo import fields, models


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Читач'
    _order = 'name, id'

    name = fields.Char(string='Ім’я читача', required=True)
    membership_number = fields.Char(string='Номер читацького квитка', required=True)
    loan_ids = fields.One2many('library.loan', 'member_id', string='Історія видач')

    _unique_membership_number = models.Constraint(
        'UNIQUE(membership_number)', 'Номер читацького квитка має бути унікальним.',
    )
