import sys
import email


def main():
    open('/home/mailuser/test.eml', 'rb').write(sys.stdin.read())

if __name__ == '__main__':
    main()
