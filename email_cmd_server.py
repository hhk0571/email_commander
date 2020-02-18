# coding: utf-8
import os
import sys
import time
import smtplib
import poplib
from email.mime.text import MIMEText
from email.parser import Parser
from email.header import decode_header
from email.utils import parseaddr
import json
from config import Config

WIDTH = 50



class SmtpServer(object):
    def __init__(self, configurator):
        self.closed = True
        self.config = configurator
        self.from_addr = self.config.USERNAME

    def login(self):
        self.server = smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT)
        self.server.set_debuglevel(self.config.DEBUG_LEVEL)
        self.server.login(self.config.USERNAME, self.config.PASSWORD)
        self.closed = False

    def quit(self):
        if not self.closed:
            self.server.quit()
            self.closed = True

    def send_msg(self, to_addr, msg_subject='', msg_body=None):
        if self.closed:
            print('SMTP server is not login')
            return False
        if not msg_body:
            msg_body = msg_subject or '<EMPTY>'
        msg = MIMEText(msg_body, 'plain', 'utf-8')
        msg['To'] = to_addr
        msg['Subject'] = msg_subject
        try:
            self.server.sendmail(self.from_addr, [to_addr], msg.as_string())
            print('Email sending to %s ... OK' % to_addr)
            return True
        except smtplib.SMTPException as e:
            print('Email sending to %s ... failed: <%s>.' % (to_addr,e))
            return False


class PopServer(object):
    def __init__(self, configurator):
        self.config = configurator
        self.parser = Parser()
        self.login()

    def login(self):
        self.server = poplib.POP3(self.config.POP_SERVER)
        self.server.set_debuglevel(self.config.DEBUG_LEVEL)
        self.server.user(self.config.USERNAME)
        self.server.pass_(self.config.PASSWORD)

    def quit(self):
        self.server.quit()

    @property
    def msg_num(self):
        return self.server.stat()[0]

    def get_msg(self, index):
        __, lines, __ = self.server.retr(index)
        msg = b'\n'.join(lines).decode()
        msg = self.parser.parsestr(msg)
        return msg


class EmailMonitor(object):
    def __init__(self, configurator):
        self.config = configurator
        self.smtp_server = SmtpServer (configurator)
        self.pop_server = PopServer (configurator)
        self.cmd_executor = CmdExecutor ()
        self.white_list = configurator.WHITE_LIST
        self.msg_num = self.pop_server .msg_num
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
            print(('Message: %d' % index).center(WIDTH, '-'))
            from_name, from_addr = self._decode_addr(msg.get('From'))
            subject = self._decode_str(msg.get('Subject', '')).strip()
            print('From:', '%s <%s>' % (from_name, from_addr))
            print('Subject:', subject)
            if from_addr in self.white_list and self.cmd_executor.is_cmd_supported(subject):
                print('Execute command: %s' % subject)
                __, output = self.cmd_executor.execute(subject)
                self.send_result(from_addr, output)


    def send_result(self, to_addr, result_txt):
        self.smtp_server.login()
        self.smtp_server.send_msg(to_addr, result_txt)
        self.smtp_server.quit()


    def run(self):
        while True:
            msg_num = self.pop_server.msg_num
            if msg_num > self.msg_num:
                self.handle_new_msgs(msg_num)
                self.msg_num = msg_num
            self.pop_server.quit()
            time.sleep(self.config.POP_INTERVAL)
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
        try:
            self._exe_cmd(cmd)
        except SystemExit:
            print('Exit')
            sys.exit(0)
        except NotImplementedError:
            output = 'Not implemented'
        except Exception as e:
            output = 'Failed: %s' % e
        else:
            output ='OK'
            result = True

        print(output)
        return result, 'Command <%s>: %s' % (cmd_name, output)


    def _exe_cmd(self, cmd):
        if cmd == 'screenshot':
            raise NotImplementedError
        elif cmd == 'exit monitor':
            raise SystemExit
        else:
            os.system(cmd)


if __name__ == "__main__":
    configurator = Config()
    email_monitor = EmailMonitor(configurator)
    email_monitor.run()
