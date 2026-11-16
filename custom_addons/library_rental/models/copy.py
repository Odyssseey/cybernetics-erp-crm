from odoo import _, api, fields, models
from odoo.exceptions import AccessError


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

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if not self.env.su and not self.env.user.has_group('library_rental.group_library_librarian'):
            raise AccessError(_('Екрани керування примірниками доступні лише бібліотекарю.'))
        return super().get_view(view_id, view_type, **options)
