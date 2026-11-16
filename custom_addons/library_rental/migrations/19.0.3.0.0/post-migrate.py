from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    loans = env['library.loan'].search([])
    for field_name in ('due_date', 'fine_amount'):
        env.add_to_compute(loans._fields[field_name], loans)
        loans.flush_recordset([field_name])
