from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase


class TestLibraryReturnAndReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.librarian, cls.reader = cls.env['res.users'].create([
            {'name': 'Test Librarian', 'login': 'test.library.return.librarian',
             'group_ids': [Command.set(cls.env.ref('library_rental.group_library_librarian').ids)]},
            {'name': 'Test Reader', 'login': 'test.library.return.reader',
             'group_ids': [Command.set(cls.env.ref('library_rental.group_library_reader').ids)]},
        ])
        cls.member = cls.env['library.member'].create({
            'name': 'Читач для звіту', 'membership_number': 'TEST-RETURN', 'user_id': cls.reader.id,
        })
        books = cls.env['library.book'].create([
            {'name': 'Тестова перша книга', 'author': 'Автор'},
            {'name': 'Тестова друга книга', 'author': 'Автор'},
        ])
        cls.copies = cls.env['library.copy'].create([
            {'book_id': book.id, 'inventory_number': f'RET-{index}'}
            for index, book in enumerate(books, start=1)
        ])
        cls.loans = cls.env['library.loan'].create([
            {'copy_id': copy.id, 'member_id': cls.member.id, 'loan_date': cls.today - timedelta(days=21)}
            for copy in cls.copies
        ])
        cls.wizards = cls.env['library.return.wizard'].with_user(cls.librarian)

    def test_wizard_defaults_only_for_loan_context(self):
        requested_fields = ['loan_id', 'condition_on_return']
        loan = self.loans[0]
        defaults = self.wizards.with_context(
            active_model='library.loan', active_id=loan.id,
        ).default_get(requested_fields)
        self.assertEqual(defaults, {'loan_id': loan.id, 'condition_on_return': 'good'})
        other_defaults = self.wizards.with_context(
            active_model='library.member', active_id=self.member.id,
        ).default_get(requested_fields)
        self.assertNotIn('loan_id', other_defaults)

    def test_return_recomputes_fine_and_blocks_repeat(self):
        loan = self.loans[0]
        wizard = self.wizards.create({'loan_id': loan.id, 'condition_on_return': 'damaged'})
        self.assertEqual(wizard.action_confirm(), {'type': 'ir.actions.act_window_close'})
        self.assertEqual((loan.state, loan.return_date, loan.fine_amount), ('returned', self.today, 35.0))
        self.assertEqual(loan.copy_id.condition, 'damaged')
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_confirmation_requires_one_wizard_and_librarian(self):
        wizard_records = self.wizards.create([
            {'loan_id': loan.id, 'condition_on_return': 'good'} for loan in self.loans
        ])
        with self.assertRaisesRegex(ValueError, 'Expected singleton'):
            wizard_records.action_confirm()
        self.assertEqual(self.loans.mapped('state'), ['active', 'active'])
        with self.assertRaises(AccessError):
            self.wizards.with_user(self.reader).create({
                'loan_id': self.loans[0].id, 'condition_on_return': 'good',
            })

    def test_history_report_matches_member_and_is_restricted(self):
        report = self.env.ref('library_rental.action_report_member_loan_history')
        self.assertEqual(report.model, 'library.member')
        self.assertEqual(report.binding_model_id.model, report.model)
        html, kind = report.with_user(self.librarian)._render_qweb_html(
            report.report_name, self.member.ids,
        )
        self.assertEqual(kind, 'html')
        content = str(html, 'utf-8')
        for text in (self.member.name, *self.copies.mapped('book_id.name')):
            self.assertIn(text, content)
        with self.assertRaises(AccessError):
            report.with_user(self.reader)._render_qweb_html(report.report_name, self.member.ids)
