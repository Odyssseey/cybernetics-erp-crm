from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestLibraryLoan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loans = cls.env['library.loan']
        cls.today = fields.Date.context_today(cls.loans)
        book = cls.env['library.book'].create({'name': 'Тестова книга', 'author': 'Тестовий автор'})
        cls.copies = cls.env['library.copy'].create([
            {'book_id': book.id, 'inventory_number': 'TEST-001'},
            {'book_id': book.id, 'inventory_number': 'TEST-002'},
        ])
        cls.member = cls.env['library.member'].create({
            'name': 'Тестовий читач', 'membership_number': 'TEST-MEMBER',
        })

    def _create_loan(self, copy, **values):
        return self.loans.create({
            'copy_id': copy.id,
            'member_id': self.member.id,
            'loan_date': self.today,
            **values,
        })

    def test_dates_and_fine_recompute_and_are_searchable(self):
        loan = self._create_loan(self.copies[0])
        self.assertEqual(loan.due_date, self.today + timedelta(days=14))
        self.assertEqual(loan.fine_amount, 0.0)
        loan.write({'return_date': self.today + timedelta(days=14), 'state': 'returned'})
        self.assertEqual(loan.fine_amount, 0.0)
        loan.return_date = self.today + timedelta(days=16)
        self.assertEqual(loan.fine_amount, 10.0)
        loan.loan_date = self.today - timedelta(days=2)
        self.assertEqual(loan.due_date, self.today + timedelta(days=12))
        self.assertEqual(loan.fine_amount, 20.0)
        self.assertEqual(self.loans.search_count([
            ('id', '=', loan.id), ('fine_amount', '=', 20.0), ('due_date', '=', loan.due_date),
        ]), 1)
        loan.return_date = False
        self.assertEqual(loan.fine_amount, 0.0)

    def test_is_overdue_applies_to_active_loans_only(self):
        loan = self._create_loan(self.copies[0], loan_date=self.today - timedelta(days=15))
        self.assertFalse(loan._fields['is_overdue'].store)
        self.assertTrue(loan.is_overdue)
        loan.loan_date = self.today - timedelta(days=14)
        self.assertFalse(loan.is_overdue, 'Loans due today are not overdue.')
        loan.write({'loan_date': self.today - timedelta(days=15), 'state': 'returned'})
        self.assertFalse(loan.is_overdue)

    def test_onchange_and_duplicate_guard(self):
        copy, other_copy = self.copies
        loan = self._create_loan(copy)
        loan.write({'copy_id': copy.id})
        own_draft = self.loans.new({'copy_id': copy.id}, origin=loan)
        self.assertIsNone(own_draft._onchange_copy_id())
        draft = self.loans.new({'copy_id': copy.id})
        self.assertIn('warning', draft._onchange_copy_id())

        with self.assertRaisesRegex(ValidationError, 'уже має активну видачу'):
            self._create_loan(copy)
        other_loan = self._create_loan(other_copy)
        with self.assertRaisesRegex(ValidationError, 'уже має активну видачу'):
            other_loan.copy_id = copy
        self.assertEqual(other_loan.copy_id, other_copy)

        loan.write({'state': 'returned', 'return_date': self.today})
        self.assertTrue(self._create_loan(copy))

    def test_invalid_dates_raise_validation_error(self):
        loan = self._create_loan(self.copies[0])
        with self.assertRaisesRegex(ValidationError, 'Планова дата'), self.env.cr.savepoint():
            loan.due_date = loan.loan_date
        with self.assertRaisesRegex(ValidationError, 'Фактична дата'), self.env.cr.savepoint():
            loan.return_date = loan.loan_date - timedelta(days=1)
        loan.return_date = loan.loan_date
        self.assertEqual(loan.return_date, loan.loan_date)
