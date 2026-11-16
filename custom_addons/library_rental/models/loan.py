import logging
from contextlib import contextmanager
from datetime import timedelta

from psycopg2.errors import UniqueViolation

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)
LOAN_TERM_DAYS = 14
DAILY_FINE_UAH = 5.0
ACTIVE_COPY_CONFLICT = 'Цей примірник уже має активну видачу.'


class LibraryLoan(models.Model):
    _name = 'library.loan'
    _description = 'Видача примірника'
    _rec_name = 'copy_id'
    _order = 'loan_date desc, id desc'

    copy_id = fields.Many2one('library.copy', string='Примірник', required=True, ondelete='restrict')
    member_id = fields.Many2one('library.member', string='Читач', required=True, ondelete='restrict')
    reader_user_id = fields.Many2one(
        'res.users', string='Обліковий запис читача', related='member_id.user_id',
        store=True, ondelete='set null',
    )
    loan_date = fields.Date(string='Дата видачі', required=True, default=fields.Date.context_today)
    due_date = fields.Date(
        string='Повернути до', compute='_compute_due_date',
        store=True, precompute=True, required=True,
    )
    return_date = fields.Date(string='Фактичне повернення')
    fine_amount = fields.Float(
        string='Штраф, грн', compute='_compute_fine_amount', store=True, digits=(16, 2),
    )
    is_overdue = fields.Boolean(string='Прострочено', compute='_compute_is_overdue')
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

    _active_copy_unique = models.UniqueIndex(
        "(copy_id) WHERE state = 'active'", ACTIVE_COPY_CONFLICT,
    )

    @api.depends('loan_date')
    def _compute_due_date(self):
        for loan in self:
            loan.due_date = loan.loan_date and loan.loan_date + timedelta(days=LOAN_TERM_DAYS)

    @api.depends('due_date', 'return_date')
    def _compute_fine_amount(self):
        for loan in self:
            if loan.return_date and loan.due_date:
                late_days = (loan.return_date - loan.due_date).days
                loan.fine_amount = max(late_days, 0) * DAILY_FINE_UAH
            else:
                loan.fine_amount = 0.0

    @api.depends('state', 'due_date')
    @api.depends_context('tz', 'uid')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for loan in self:
            loan.is_overdue = bool(loan.state == 'active' and loan.due_date and loan.due_date < today)

    @api.model
    def _cron_check_overdue_loans(self):
        overdue_loans = self.search([
            ('state', '=', 'active'),
            ('due_date', '<', fields.Date.context_today(self)),
        ])
        failed = 0
        for loan in overdue_loans:
            try:
                with self.env.cr.savepoint():
                    loan._log_overdue_loan()
            except Exception:
                failed += 1
                _logger.exception('Не вдалося обробити прострочену видачу ID=%s.', loan.id)

        _logger.info(
            'Перевірка прострочення: знайдено %s, оброблено %s, помилок %s.',
            len(overdue_loans), len(overdue_loans) - failed, failed,
        )

    def _log_overdue_loan(self):
        self.ensure_one()
        inventory_number = self.copy_id.inventory_number
        if not inventory_number:
            raise ValueError('У видачі відсутній інвентарний номер примірника.')
        _logger.info(
            'Прострочена видача ID=%s, примірник %s, повернути до %s.',
            self.id, inventory_number, self.due_date,
        )

    def _find_other_active_loan(self, copy, excluded_id):
        return self.sudo().search([
            ('copy_id', '=', copy.id),
            ('state', '=', 'active'),
            ('id', '!=', excluded_id),
        ], limit=1)

    @api.onchange('copy_id')
    def _onchange_copy_id(self):
        if self.copy_id and self._find_other_active_loan(self.copy_id, self._origin.id):
            return {
                'warning': {
                    'title': _('Примірник зайнятий'),
                    'message': _(ACTIVE_COPY_CONFLICT),
                },
            }

    @api.constrains('copy_id', 'state')
    def _check_one_active_loan_per_copy(self):
        for loan in self.filtered(lambda loan: loan.state == 'active'):
            if loan._find_other_active_loan(loan.copy_id, loan.id):
                raise ValidationError(_(ACTIVE_COPY_CONFLICT))

    @api.constrains('loan_date', 'due_date')
    def _check_due_date(self):
        for loan in self:
            if not loan.due_date or loan.due_date <= loan.loan_date:
                raise ValidationError(_('Планова дата повернення має бути пізнішою за дату видачі.'))

    @api.constrains('loan_date', 'return_date')
    def _check_return_date(self):
        for loan in self:
            if loan.return_date and loan.return_date < loan.loan_date:
                raise ValidationError(_('Фактична дата повернення не може бути ранішою за дату видачі.'))

    @contextmanager
    def _validate_active_copy_index(self):
        try:
            with self.env.cr.savepoint():
                yield
        except UniqueViolation as error:
            if error.diag.constraint_name != self._active_copy_unique.full_name(self):
                raise
            raise ValidationError(_(ACTIVE_COPY_CONFLICT)) from error

    @api.model_create_multi
    def create(self, vals_list):
        with self._validate_active_copy_index():
            return super().create(vals_list)

    def write(self, vals):
        if {'copy_id', 'state'}.intersection(vals):
            with self._validate_active_copy_index():
                return super().write(vals)
        return super().write(vals)
