from datetime import datetime
import decimal

import click
from pyexcel_odsr import get_data as ods_get_data

from bloxs import Bloxs, InvoiceCreateError


def get_owners_from_file(fname):
    """read the ODS file and extract the owner information"""
    sheets = ods_get_data(fname)

    # expecting a workbook with a single sheet
    if len(sheets) != 1:
        raise AssertionError("Expecting a single sheet")

    sheet_name = next(iter(sheets))
    sheet = sheets[sheet_name]

    # expecting rows to be (owner, property, sum)
    return [
        (row[0], row[1], decimal.Decimal(row[2].split()[0]))
        for row in sheet[1:] if len(row) == 3
    ]


@click.command()
@click.option('--eigfile',
              help="The CSV file containing the owners")
@click.option('--year',
              default=datetime.now().year,
              help="The year of the period")
@click.option('--month',
              default=datetime.now().month,
              help="The month of the period")
def main(eigfile, year, month):
    """
        Read the configuration file and create invoices for the owners
    """
    owners = get_owners_from_file(eigfile)
    bloxs = Bloxs()
    period_date = datetime(year, month, 1)

    for name, address, amount in owners:
        try:
            inv_num = bloxs.create_owner_purchase_invoice(
                name, address, period_date, str(amount))
            print("Created invoice number {} for owner {}".format(
                                                            inv_num, name))
        except InvoiceCreateError:
            print("Failed to create an invoice for owner {}".format(name))

if (__name__ == '__main__'):
    decimal.getcontext().prec = 2
    main()
