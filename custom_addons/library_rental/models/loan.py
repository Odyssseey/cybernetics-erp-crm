from odoo import fields, models


class LibraryLoan(models.Model):
    _name = 'library.loan'
    _description = 'Видача примірника'
    _rec_name = 'copy_id'
    _order = 'loan_date desc, id desc'

    copy_id = fields.Many2one('library.copy', string='Примірник', required=True, ondelete='restrict')
    member_id = fields.Many2one('library.member', string='Читач', required=True, ondelete='restrict')
    loan_date = fields.Date(string='Дата видачі', required=True, default=fields.Date.context_today)
    due_date = fields.Date(string='Повернути до', required=True)
    return_date = fields.Date(string='Фактичне повернення')
    state = fields.Selection(
        [('active', 'Активна'), ('returned', 'Повернено')],
        string='Статус',
        required=True,
        default='active',
    )

    book_name = fields.Char(string='Назва книги', related='copy_id.book_id.name')
    book_author = fields.Char(string='Автор книги', related='copy_id.book_id.author')
    book_isbn = fields.Char(string='ISBN', related='copy_id.book_id.isbn')
    membership_number = fields.Char(
        string='Номер читацького квитка', related='member_id.membership_number',
    )
