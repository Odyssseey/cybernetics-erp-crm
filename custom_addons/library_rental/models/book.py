from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Книга'
    _order = 'name, id'

    name = fields.Char(string='Назва', required=True)
    author = fields.Char(string='Автор', required=True)
    isbn = fields.Char(string='ISBN')
    publish_year = fields.Integer(string='Рік видання')
    copy_ids = fields.One2many('library.copy', 'book_id', string='Примірники')

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if not self.env.su and not self.env.user.has_group('library_rental.group_library_librarian'):
            raise AccessError(_('Екрани керування книгами доступні лише бібліотекарю.'))
        return super().get_view(view_id, view_type, **options)
