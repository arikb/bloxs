import logging
import os.path

from mimetypes import guess_type
from datetime import datetime
from requests import HTTPError
from requests_html import HTMLSession
from requests.compat import urljoin
from requests.exceptions import HTTPError

import config


class InvoiceCreateError(Exception):
    pass


class Bloxs():
    def __init__(self):
        self.API_BASE = config.get('BLOXS_API_BASE')
        self.USER = config.get('BLOXS_USER')
        self.PASS = config.get('BLOXS_PASS')
        self.session = HTMLSession()
        self.perform_login(self.USER, self.PASS)

    def debug_on(self):
        """do debug logging"""
        from http.client import HTTPConnection

        HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    def perform_login(self, user, passwd):
        """ Login to Bloxs """
        response = self.session.post(
            urljoin(self.API_BASE, 'Login/PerformLogin'),
            json={"Username": user, "Password": passwd})
        response.raise_for_status()
        return True

    def upload_file(self, attachment):
        """upload a file into bloxs, returning the resulting file ID"""
        response = self.session.post(
            urljoin(self.API_BASE, 'File/UpdateFile'),
            json={"fileId": 'null', "path": "$$Upload"},
            files={'file': (
                os.path.split(attachment)[1],
                open(attachment, 'rb'),
                guess_type(attachment)[0])})
        response.raise_for_status()
        return response.json()['data']

    def find_period_id(self, dt):
        """Query bloxs for the period code"""
        period = dt.strftime('%Y/%-m')
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/PeriodInvoiceReferenceItem'),
            # looking for 4 items to cover the case of
            # 1 matching 10, 11, 12
            json={"searchTerm": period, "maxItems": "4"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'] == period:
                return result['ID']

    def find_payment_term_id(self, days):
        """Query bloxs for the payment terms, return the 0 days"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/PaymentTermWithOtherReferenceItem'),
            json={"sort": "Days", "maxItems": "99"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Days'] == days:
                return result['ID']

    def find_owner_id(self, owner):
        """Query bloxs for the owner ID"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/OwnerReferenceItem'),
            json={"searchTerm": owner, "maxItems": "10"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'] == owner:
                return result['ID']

    def find_party_id(self, party):
        """Query bloxs for a party ID"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/PartyReferenceItem'),
            json={"searchTerm": party, "maxItems": "10"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'] == party:
                return result['ID']

    def find_payment_method_id(self, payment_method):
        """Query bloxs the ID of the payment method"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/PaymentMethodPurchaseInvoiceReferenceItem'),
            json={"maxItems": "999"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'] == payment_method:
                return result['ID']

    def find_ledger_id(self, ledger_code):
        """Query bloxs the ID of the payment method"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/LedgerJournalReferenceItem'),
            json={"searchTerm": ledger_code, "maxItems": "7"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'].startswith(ledger_code):
                return result['ID']

    def find_property_id(self, owner_id, property_name):
        """Query bloxs the ID of the payment method"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/RentableReferenceItem'),
            json={
                "searchTerm": property_name,
                "maxItems": "7",
                "filters": [
                    {
                        "column": "OwnerID",
                        "operator": "neq",
                        "value": owner_id
                    }
                ]
                })
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'].startswith(property_name):
                return result['ID']

    def find_tax_rate_id(self, tax_rate):
        """Query bloxs the ID of the payment method"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/TaxRatePurchaseInvoiceReferenceItem'),
            json={
                "searchTerm": tax_rate,
                "maxItems": "7"
                })
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'] == tax_rate:
                return result['ID']

    def find_owner_account_id(self, owner_id):
        """Query bloxs for the owner's bank accounts ID"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/OwnerBankAccountReferenceItem'),
            json={
                'filters[0][column]': 'OwnerID',
                'filters[0][operator]': 'eq',
                'filters[0][value]': str(owner_id),
                'maxItems': '1'})
        response.raise_for_status()
        results = response.json()
        return results[0]['ID']

    def create_draft_purchase_invoice(self, attachment):
        """create a purchase invoice"""
        file_id = self.upload_file(attachment)
        time_now = datetime.now().replace(microsecond=0)
        iso_timestamp = time_now.isoformat()
        period_id = self.find_period_id(time_now)
        payment_term_zero_id = self.find_payment_term_id(0)
        owner_id = self.find_owner_id('Fictief')
        bank_account_id = self.find_owner_accounts_id(owner_id)

        invoice_data = {
            'OwnerID': owner_id,
            'Date': iso_timestamp,
            'PeriodID': period_id,
            'PaymentTermID': payment_term_zero_id,
            'PaymentDate': iso_timestamp,
            'FileID': file_id,
            'BankAccountID': bank_account_id,
            'IsTransitoric': 'false',
            'Lines[0][Amount]': '0',
            'Lines[0][VAT]': '0',
            'Lines[0][TaxRateID]': '0'
        }

        response = self.session.post(
            urljoin(self.API_BASE, 'ConceptInvoice/Create'),
            json=invoice_data)
        response.raise_for_status()

    def create_owner_purchase_invoice(self, owner, address, period_time,
                                      amount):
        """
        create a purchase invoice for an owner of a huur-door-te-verhuur
        property
        """

        # invoice time will always be the 1st of the month exactly
        invoice_time = period_time.replace(
            day=1, hour=0, minute=0, second=0,
            microsecond=0, tzinfo=None)
        iso_timestamp = invoice_time.isoformat()

        try:
            owner_id = self.find_owner_id('Amstel Vastgoed Beheer')
            bank_account_id = self.find_owner_account_id(owner_id)
            party_id = self.find_party_id(owner)
            payment_method_transfer = self.find_payment_method_id(
                                                        'Overschrijving')
            payment_term_zero_id = self.find_payment_term_id(0)
            period_id = self.find_period_id(invoice_time)
            subject = "Eigenaar saldo voor periode {}-{}".format(
                invoice_time.month, invoice_time.year)

            item_amount = amount
            item_description = "Huur saldo - {}-{}".format(
                invoice_time.month, invoice_time.year)
            item_ledger_id = self.find_ledger_id("8000")
            property_id = self.find_property_id(owner_id, address)
            print(address, property_id)
            tax_rate_none_id = self.find_tax_rate_id("Geen")

            invoice_number = "EIGBTL-{}.{}-{}.{}".format(
                party_id, invoice_time.month, invoice_time.year, property_id)

            invoice_data = {
                'OwnerID': owner_id,
                'BankAccountID': bank_account_id,
                'Date': iso_timestamp,
                'IsTransitoric': False,
                'PartyID': party_id,
                'PaymentDate': iso_timestamp,
                'PaymentMethod': str(payment_method_transfer),
                'PaymentTermID': payment_term_zero_id,
                'PeriodID': period_id,
                'ReferenceCode': invoice_number,
                'Subject': subject,
                'Lines': [
                    {
                        'Amount': item_amount,
                        'Description': item_description,
                        'LedgerID': item_ledger_id,
                        'RentableID': property_id,
                        'TaxRateID': tax_rate_none_id,
                        'VAT': 0
                    }
                ]
            }

            # validate
            response = self.session.post(
                urljoin(self.API_BASE, 'ConceptInvoice/ValidateCreateUpgrade'),
                json=invoice_data)
            response.raise_for_status()

            # create
            response = self.session.post(
                urljoin(self.API_BASE, 'ConceptInvoice/Create'),
                json=invoice_data)
            response.raise_for_status()
            results = response.json()
            invoice_concept_id = results['data']['ID']

            # "upgrade"
            response = self.session.post(
                urljoin(
                    self.API_BASE,
                    'ConceptInvoice/Upgrade/{}'.format(invoice_concept_id)),
                data="")
            response.raise_for_status()
            results = response.json()
            invoice_id = results['data']
            return invoice_id
        except HTTPError:
            raise InvoiceCreateError


def main():
    bloxs = Bloxs()
    # bloxs.debug_on()
    # bloxs.create_draft_purchase_invoice(
    #    '/home/tech/Documents/GrayHatPython_Cruz3N_Ganteng_Banget.pdf')
    print(bloxs.create_owner_purchase_invoice(
        'Mrs. Malka Yulazri',
        'Dijkgraafplein',
        datetime(2019, 9, 1),
        -3000))

if __name__ == '__main__':
    main()
