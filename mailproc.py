import sys
from email import message_from_binary_file
from bloxs import Bloxs


def main():
    bloxs = Bloxs()
    message = message_from_binary_file(sys.stdin.buffer)
    open('/home/mailuser/test.eml', 'wb').write(message.as_bytes())
    for part in message.walk():
        if part.get_content_type() == 'application/pdf':
            open('/home/mailuser/test.pdf', 'wb').write(
                part.get_payload(decode=True))
            bloxs.create_draft_purchase_invoice('/home/mailuser/test.pdf')


if __name__ == '__main__':
    main()
