{
    'name': 'Library Rental',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Бібліотека та прокат книг — базовий каркас модуля (Трек A)',
    'description': """
Library Rental (Бібліотека / Прокат)
====================================
Базовий каркас кастомного модуля для Odoo 19 Community (Трек A курсу «ERP-CRM системи»).
У наступних практичних заняттях (2–6) модуль розширюється моделями:
- Book (Книга)
- Copy (Примірник)
- Member (Читач / Абонент)
- Loan (Видача / Прокат)
    """,
    'author': 'Maxim Drobov (Odyssey)',
    'website': 'https://github.com/Oddysey1326/cybernetics_ERP_CRM',
    'license': 'LGPL-3',
    'depends': [
        'base',
    ],
    'data': [
        # Порожній список для Практичного заняття 1.
        # Файли security/ir.model.access.csv та views/*.xml будуть підключені у Практичному 2.
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
