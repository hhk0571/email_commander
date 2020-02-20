# coding: utf-8
import os
import sys
import time
import smtplib
import poplib
from PIL import ImageGrab
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart, MIMEBase
from email.parser import Parser
from email.header import decode_header
from email.utils import parseaddr
import json
from config import Config

WIDTH = 50
SCREENSHOT_FILE = 'screenshot.jpg'

class SmtpPop3Base(object):
    def __init__(self):
        self.closed = True

    def login(self):
        self._login_impl()
        self.closed = False

    def assert_server_is_login(self, msg=None):
        if self.closed:
            msg = msg or '%s is not login' % self.__class__.__name__
            raise AssertionError(msg)

    def quit(self):
        if not self.closed:
            self._quit_impl()
            self.closed = True

    def _login_impl(self):
        raise NotImplementedError # virual function

    def _quit_impl(self):
        raise NotImplementedError # virual function


class SmtpServer(SmtpPop3Base):
    def __init__(self):
        super().__init__()
        self.from_addr = Config.USERNAME

    def _login_impl(self):
        if not Config.ENABLE_SSL:
            self.server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
            self.server.set_debuglevel(Config.DEBUG_LEVEL)
        else:
            try:
                self.server = smtplib.SMTP_SSL(Config.SMTP_SERVER, Config.SMTP_PORT)
            except:
                self.server = smtplib.SMTP_SSL(Config.SMTP_SERVER)
            self.server.set_debuglevel(Config.DEBUG_LEVEL)
            self.server.ehlo(Config.SMTP_SERVER)

        self.server.login(Config.USERNAME, Config.PASSWORD)


    def _quit_impl(self):
        self.server.quit()

    def send_msg(self, to_addr, subject='', content=None, filename=None):
        self.assert_server_is_login()
        if not content:
            content = subject or '<EMPTY>'

        msg = MIMEText(content, 'plain', 'utf-8')

        if filename:
            multi_msg = MIMEMultipart()
            multi_msg.attach(msg)
            msg = multi_msg

            with open(filename, 'rb') as f:
                short_name = os.path.basename(filename)
                mime = MIMEBase('attachment', short_name.split('.')[-1], filename=short_name)
                mime.add_header('Content-Disposition', 'attachment', filename=filename)
                mime.add_header('Content-ID', '<0>')
                mime.add_header('X-Attachment-Id', '0')
                mime.set_payload(f.read())
                encoders.encode_base64(mime)
                msg.attach(mime)

        msg['From'] = self.from_addr
        msg['To'] = to_addr
        msg['Subject'] = subject

        try:
            self.server.sendmail(self.from_addr, [to_addr], msg.as_string())
            print('Email sending to %s ... OK' % to_addr)
            return True
        except smtplib.SMTPException as e:
            print('Email sending to %s ... failed: <%s>.' % (to_addr,e))
            return False


class PopServer(SmtpPop3Base):
    def __init__(self):
        super().__init__()
        self.parser = Parser()
        self.login()

    def _login_impl(self):
        self.server = poplib.POP3(Config.POP_SERVER)
        self.server.set_debuglevel(Config.DEBUG_LEVEL)
        self.server.user(Config.USERNAME)
        self.server.pass_(Config.PASSWORD)

    def _quit_impl(self):
        self.server.quit()

    @property
    def msg_num(self):
        self.assert_server_is_login()
        return self.server.stat()[0]

    def get_msg(self, index):
        self.assert_server_is_login()
        __, lines, __ = self.server.retr(index)
        msg = b'\n'.join(lines).decode()
        msg = self.parser.parsestr(msg)
        return msg


class EmailMonitor(object):
    def __init__(self):
        self.smtp_server = SmtpServer()
        self.pop_server = PopServer()
        self.cmd_executor = CmdExecutor()
        self.white_list = Config.WHITE_LIST
        self.msg_num = self.pop_server.msg_num
        print('Initial Messages: %s' % self.msg_num)


    def _decode_str(self, s):
        value, charset = decode_header(s)[0]
        if charset:
            value = value.decode(charset)
        return value


    def _decode_addr(self, addr):
        name, mailbox = parseaddr(addr)
        name = self._decode_str(name)
        return name, mailbox


    def handle_new_msgs(self, msg_num):
        for index in range(self.msg_num + 1, msg_num + 1):
            msg = self.pop_server.get_msg(index)
            from_name, from_addr = self._decode_addr(msg.get('From'))
            subject = self._decode_str(msg.get('Subject', '')).strip()
            print(('Message: %d' % index).center(WIDTH, '-'))
            print('From:', '%s <%s>' % (from_name, from_addr))
            print('Subject:', subject)
            if from_addr in self.white_list and self.cmd_executor.is_cmd_supported(subject):
                print('Execute command: %s' % subject)
                __, output, attach_file = self.cmd_executor.execute(subject)
                self.send_result(from_addr, subject=output, filename=attach_file)


    def send_result(self, to_addr, subject='', content=None, filename=None):
        self.smtp_server.login()
        self.smtp_server.send_msg(to_addr, subject, content, filename)
        self.smtp_server.quit()


    def run(self):
        while True:
            msg_num = self.pop_server.msg_num
            if msg_num > self.msg_num:
                self.handle_new_msgs(msg_num)
                self.msg_num = msg_num
            self.pop_server.quit()
            time.sleep(Config.POP_INTERVAL * 60)
            self.pop_server.login()


class CmdExecutor(object):
    def __init__(self):
        with open('commands.json', encoding='utf-8') as f:
            self._commands = json.load(f)

    def is_cmd_supported(self, cmd_name):
        return cmd_name in self._commands


    def execute(self, cmd_name):
        if not self.is_cmd_supported(cmd_name):
            output = '[Error]: Command <%s> is not supported.' % cmd_name
            print(output)
            return False, output

        cmd = self._commands.get(cmd_name)
        print('Command line: "%s"' % cmd)
        print('Result: ', end='')
        result = False
        attach_file = None
        try:
            self._exe_cmd(cmd)
        except SystemExit:
            print('Exit')
            sys.exit(0)
        except Exception as e:
            output = 'Failed: %s' % e
        else:
            output ='OK'
            result = True

        print(output)

        if cmd == 'screenshot' and result:
            attach_file = SCREENSHOT_FILE

        return result, 'Command <%s>: %s' % (cmd_name, output), attach_file


    def _exe_cmd(self, cmd):
        if cmd == 'screenshot':
            img = ImageGrab.grab()
            img.save(SCREENSHOT_FILE)
        elif cmd == 'exit monitor':
            raise SystemExit
        elif cmd == 'NotImplemented':
            raise NotImplementedError('Command is not implemented.')
        else:
            os.system(cmd)


if __name__ == "__main__":
    email_monitor = EmailMonitor()
    email_monitor.run()
