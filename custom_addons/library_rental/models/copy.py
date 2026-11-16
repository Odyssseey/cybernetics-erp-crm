from odoo import fields, models


class LibraryCopy(models.Model):
    _name = 'library.copy'
    _description = 'Примірник книги'
    _rec_name = 'inventory_number'
    _order = 'inventory_number, id'

    book_id = fields.Many2one('library.book', string='Книга', required=True, ondelete='restrict')
    inventory_number = fields.Char(string='Інвентарний номер', required=True)
    condition = fields.Selection(
        [('new', 'Новий'), ('good', 'Добрий'), ('damaged', 'Пошкоджений')],
        string='Стан примірника',
        required=True,
        default='good',
    )
    loan_ids = fields.One2many('library.loan', 'copy_id', string='Історія видач')

    _unique_inventory_number = models.Constraint(
        'UNIQUE(inventory_number)', 'Інвентарний номер має бути унікальним.',
    )
