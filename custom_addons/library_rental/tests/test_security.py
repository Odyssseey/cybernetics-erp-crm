from psycopg2.errors import UniqueViolation

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase
from odoo.tools.safe_eval import safe_eval


class TestLibrarySecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reader_group = cls.env.ref('library_rental.group_library_reader')
        cls.librarian_group = cls.env.ref('library_rental.group_library_librarian')
        cls.reader, cls.librarian, cls.internal = cls.env['res.users'].create([
            {'name': 'Читач для тесту', 'login': 'test.library.reader',
             'group_ids': [Command.set(cls.reader_group.ids)]},
            {'name': 'Бібліотекар для тесту', 'login': 'test.library.librarian',
             'group_ids': [Command.set(cls.librarian_group.ids)]},
            {'name': 'Працівник без ролі', 'login': 'test.library.internal',
             'group_ids': [Command.set(cls.env.ref('base.group_user').ids)]},
        ])
        cls.book = cls.env['library.book'].create({'name': 'Тестова книга доступу', 'author': 'Автор'})
        cls.copy, other_copy = cls.env['library.copy'].create([
            {'book_id': cls.book.id, 'inventory_number': 'SEC-001'},
            {'book_id': cls.book.id, 'inventory_number': 'SEC-002'},
        ])
        cls.member, cls.other_member = cls.env['library.member'].create([
            {'name': 'Читач для тесту', 'membership_number': 'SEC-01', 'user_id': cls.reader.id},
            {'name': 'Інший читач', 'membership_number': 'SEC-02'},
        ])
        cls.own_loan, cls.other_loan = cls.env['library.loan'].create([
            {'copy_id': cls.copy.id, 'member_id': cls.member.id},
            {'copy_id': other_copy.id, 'member_id': cls.other_member.id},
        ])

    def test_model_permissions(self):
        for model in ('library.book', 'library.copy', 'library.member', 'library.loan'):
            for operation in ('read', 'write', 'create', 'unlink'):
                self.assertTrue(self.env[model].with_user(self.librarian).has_access(operation))
                self.assertFalse(self.env[model].with_user(self.internal).has_access(operation))
                reader = self.env[model].with_user(self.reader)
                self.assertEqual(reader.has_access(operation), operation == 'read' and model != 'library.member')

        self.assertEqual(self.book.with_user(self.reader).read(['name'])[0]['name'], self.book.name)
        self.assertEqual(self.copy.with_user(self.reader).read(['condition'])[0]['condition'], 'good')
        for record in (self.book, self.copy, self.other_member):
            with self.assertRaises(AccessError):
                record.with_user(self.reader).get_view()

    def test_loan_rule_is_scoped_to_reader(self):
        rule = self.env.ref('library_rental.rule_library_loan_reader')
        self.assertEqual(rule.groups, self.reader_group)
        loans = self.own_loan | self.other_loan
        domain = [('id', 'in', loans.ids)]
        self.assertEqual(loans.with_user(self.reader).search(domain).ids, self.own_loan.ids)
        action = self.env.ref('library_rental.action_library_my_loans')
        my_loans_domain = safe_eval(action.domain, {'uid': self.reader.id})
        self.assertEqual(loans.with_user(self.reader).search(domain + my_loans_domain).ids, self.own_loan.ids)
        with self.assertRaises(AccessError):
            self.other_loan.with_user(self.reader).read(['state'])
        with self.assertRaises(AccessError):
            self.own_loan.with_user(self.reader).write({'state': 'returned'})

        for user in (self.librarian, self.env.ref('base.user_admin')):
            self.assertEqual(set(loans.with_user(user).search(domain).ids), set(loans.ids))
        self.librarian.group_ids = [Command.link(self.reader_group.id)]
        self.assertEqual(set(loans.with_user(self.librarian).search(domain).ids), set(loans.ids))

    def test_library_menus_match_roles(self):
        menu_model = self.env['ir.ui.menu']
        root = self.env.ref('library_rental.menu_library_root')
        my_loans = self.env.ref('library_rental.menu_library_my_loans')
        management = [
            self.env.ref('library_rental.menu_library_' + name).id
            for name in ('book', 'copy', 'member', 'loan')
        ]
        reader_menus = menu_model.with_user(self.reader)._visible_menu_ids()
        librarian_menus = menu_model.with_user(self.librarian)._visible_menu_ids()
        internal_menus = menu_model.with_user(self.internal)._visible_menu_ids()
        self.assertIn(root.id, reader_menus)
        self.assertIn(my_loans.id, reader_menus)
        self.assertTrue(reader_menus.isdisjoint(management))
        self.assertTrue(set(management).issubset(librarian_menus))
        self.assertNotIn(my_loans.id, librarian_menus)
        self.assertNotIn(root.id, internal_menus)

    def test_user_can_only_be_linked_to_one_member(self):
        self.assertFalse(self.other_member.user_id)
        with self.assertRaises(UniqueViolation), self.env.cr.savepoint():
            self.other_member.user_id = self.reader
