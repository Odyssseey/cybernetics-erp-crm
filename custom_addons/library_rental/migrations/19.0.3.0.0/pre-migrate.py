from odoo.exceptions import ValidationError


def migrate(cr, version):
    if not version:
        return

    # The practice 1 skeleton has no loan table yet.
    cr.execute("SELECT to_regclass('library_loan')")
    if not cr.fetchone()[0]:
        return

    cr.execute("""
        SELECT copy_id
          FROM library_loan
         WHERE state = 'active'
         GROUP BY copy_id
        HAVING COUNT(*) > 1
         ORDER BY copy_id
         LIMIT 1
    """)
    duplicate = cr.fetchone()
    if duplicate:
        raise ValidationError(
            f'Перед оновленням закрийте дублікати активних видач '
            f'для примірника з ID {duplicate[0]}.'
        )

    cr.execute("""
        SELECT id
          FROM library_loan
         WHERE return_date < loan_date
         ORDER BY id
         LIMIT 1
    """)
    invalid_return = cr.fetchone()
    if invalid_return:
        raise ValidationError(
            f'Перед оновленням виправте фактичну дату повернення '
            f'у видачі з ID {invalid_return[0]}.'
        )
