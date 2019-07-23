import logging
import os.path

from mimetypes import guess_type
from datetime import datetime
from requests import HTTPError
from requests_html import HTMLSession
from requests.compat import urljoin

import config


class Bloxs():
    def __init__(self):
        self.API_BASE = config.get('BLOXS_API_BASE')
        self.USER = config.get('BLOXS_USER')
        self.PASS = config.get('BLOXS_PASS')
        self.session = HTMLSession()
        self.perform_login(self.USER, self.PASS)

    @classmethod
    def debug_on():
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
            data={"Username": user, "Password": passwd})
        response.raise_for_status()
        return True

    def upload_file(self, attachment):
        """upload a file into bloxs, returning the resulting file ID"""
        response = self.session.post(
            urljoin(self.API_BASE, 'File/UpdateFile'),
            data={"fileId": 'null', "path": "$$Upload"},
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
            data={"searchTerm": period, "maxItems": "4"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'] == period:
                return result['ID']

    def find_payment_term_zero_id(self):
        """Query bloxs for the payment terms, return the 0 days"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/PaymentTermWithOtherReferenceItem'),
            data={"sort": "Days", "maxItems": "99"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Days'] == 0:
                return result['ID']

    def find_owner_id(self, owner):
        """Query bloxs for the owner ID"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/OwnerReferenceItem'),
            data={"searchTerm": owner, "maxItems": "10"})
        response.raise_for_status()
        results = response.json()
        for result in results:
            if result['Name'] == owner:
                return result['ID']

    def find_owner_accounts_id(self, owner_id):
        """Query bloxs for the owner's bank accounts ID"""
        response = self.session.post(
            urljoin(
                self.API_BASE,
                'data/reference/OwnerBankAccountReferenceItem'),
            data={
                'filters[0][column]': 'OwnerID',
                'filters[0][operator]': 'eq',
                'filters[0][value]': str(owner_id),
                'maxItems': '1'})
        response.raise_for_status()
        results = response.json()
        return results[0]['Name']

    def create_draft_purchase_invoice(self, attachment):
        """create a purchase invoice"""
        file_id = self.upload_file(attachment)
        time_now = datetime.now().replace(microsecond=0)
        iso_timestamp = time_now.isoformat()
        period_id = self.find_period_id(time_now)
        payment_term_zero_id = self.find_payment_term_zero_id()
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
            data=invoice_data)
        response.raise_for_status()


def main():
    bloxs = Bloxs()
    # debug_on()
    bloxs.create_draft_purchase_invoice(
        '/home/tech/Documents/GrayHatPython_Cruz3N_Ganteng_Banget.pdf')

if __name__ == '__main__':
    main()
