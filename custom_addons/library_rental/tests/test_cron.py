from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import TransactionCase


class TestLibraryOverdueCron(TransactionCase):
    def test_cron_processes_overdue_and_isolates_a_failed_record(self):
        cron = self.env.ref('library_rental.ir_cron_check_overdue_loans')
        self.assertTrue(cron.active)
        self.assertEqual(cron.model_id.model, 'library.loan')
        self.assertEqual((cron.interval_number, cron.interval_type), (1, 'days'))
        self.assertEqual(cron.code, 'model._cron_check_overdue_loans()')
        self.assertEqual((cron.nextcall.hour, cron.nextcall.minute), (2, 0))
        self.assertTrue(cron.user_id.has_group('library_rental.group_library_librarian'))

        loans = self.env['library.loan'].with_user(cron.user_id)
        today = fields.Date.context_today(loans)
        book = self.env['library.book'].create({'name': 'Книга для cron', 'author': 'Автор'})
        member = self.env['library.member'].create({'name': 'Читач для cron', 'membership_number': 'CRON-01'})
        copies = self.env['library.copy'].create([
            {'book_id': book.id, 'inventory_number': f'CRON-{index}'} for index in range(1, 5)
        ])
        bad, good, due_today, returned = self.env['library.loan'].create([
            {'member_id': member.id, 'copy_id': copy.id, 'loan_date': today - timedelta(days=days),
             **values}
            for copy, days, values in zip(copies, (20, 22, 14, 23), (
                {}, {}, {}, {'state': 'returned', 'return_date': today},
            ), strict=True)
        ])

        checked_ids = []
        log_loan = type(loans)._log_overdue_loan

        def log_with_failure(loan):
            checked_ids.append(loan.id)
            if loan.id == bad.id:
                loan.return_date = today
                raise ValueError('Тестова помилка одного запису')
            log_loan(loan)

        with patch.object(type(loans), '_log_overdue_loan', log_with_failure), self.assertLogs(
            'odoo.addons.library_rental.models.loan', level='INFO',
        ) as log:
            loans._cron_check_overdue_loans()

        self.assertLess(checked_ids.index(bad.id), checked_ids.index(good.id))
        self.assertNotIn(due_today.id, checked_ids)
        self.assertNotIn(returned.id, checked_ids)
        self.assertFalse(bad.return_date)
        self.assertIn('помилок 1.', log.output[-1])
        self.assertTrue(any(f'ID={bad.id}' in entry and 'Не вдалося' in entry for entry in log.output))
        self.assertTrue(any(f'ID={good.id}' in entry and 'Прострочена видача' in entry for entry in log.output))
