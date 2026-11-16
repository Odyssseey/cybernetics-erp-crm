{
    'name': 'Library Rental',
    'version': '19.0.4.0.0',
    'category': 'Services/Library',
    'summary': 'Каталог бібліотеки, фізичні примірники, читачі та видачі (Трек A)',
    'description': """
Library Rental (Бібліотека / Прокат)
====================================
Навчальний модуль для Odoo 19 Community (Трек A курсу «ERP-CRM системи»).
Містить каталог книг, облік примірників і читачів та історію видач.
    """,
    'author': 'Maxim Drobov (Odyssey)',
    'license': 'LGPL-3',
    'depends': [
        'base',
    ],
    'data': [
        'security/library_security.xml',
        'security/ir.model.access.csv',
        'views/book_views.xml',
        'views/copy_views.xml',
        'views/member_views.xml',
        'views/loan_views.xml',
        'views/library_menus.xml',
    ],
    'demo': ['demo/library_demo.xml', 'demo/library_users_demo.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
