"""
Convert the output of pffexport to .eml files

Usage: `python3 pffexport_to_eml.py export out_folder`

It creates an `export` folder inside `out_folder`. It can convert individual
messages or entire folder hierarchies.
"""

import sys
from pathlib import Path
import re
import email
import email.message
import email.encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from io import BytesIO

def get_file_attachment(p):
    attachment = MIMEBase('application', 'octet-stream')
    with p.open('rb') as f:
        attachment.set_payload(f.read())
    email.encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition',
        'attachment', filename=p.name)
    return attachment

def get_message_attachment(p):
    attachment = MIMEBase('message', 'rfc822')
    f = BytesIO()
    read_email(p, f)
    attachment.set_payload(f.getvalue())
    email.encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition',
        'attachment', filename=p.name)
    return attachment

def read_email(folder, output):
    with (folder / 'InternetHeaders.txt').open('rb') as f:
        raw_headers = f.read()

    message = email.message_from_bytes(raw_headers)
    del message['Content-Type']
    message.set_payload(None)
    message['Content-Type'] = 'multipart/mixed'

    html_file = folder / 'Message.html'
    text_file = folder / 'Message.txt'
    if html_file.exists():
        with html_file.open('rb') as f:
            html_src = f.read()
        utf8 = bool(re.search(br'charset\s*=["\']?utf[-]?8', html_src[:1024]))
        params = {'charset': 'utf-8'} if utf8 else {}
        html = MIMEBase('text', 'html', **params)
        html.set_payload(html_src)
        email.encoders.encode_base64(html)
        message.attach(html)
    elif text_file.exists():
        text = MIMEBase('text', 'plain')
        with text_file.open('rb') as f:
            text.set_payload(f.read())
        email.encoders.encode_base64(text)
        message.attach(text)

    attachments_dir = folder / 'Attachments'
    if attachments_dir.exists():
        for p in attachments_dir.iterdir():
            if p.is_dir():
                for i in p.iterdir():
                    if i.name.startswith('Message'):
                        message.attach(get_message_attachment(i))
                    else:
                        raise RuntimeError('unknown attachment {!r}'.format(i))
            else:
                message.attach(get_file_attachment(p))

    output.write(message.as_bytes())

def convert_message(message, out_folder):
    print(message)
    out_folder.mkdir(parents=True, exist_ok=True)
    out_message = out_folder / (message.name + '.eml')
    if out_message.exists():
        print('exists')
        return
    if not (message / 'InternetHeaders.txt').is_file():
        print('no internet headers')
        return
    out_message_tmp = out_folder / (message.name + '.tmp')
    with out_message_tmp.open('wb') as f:
        read_email(message, f)
    out_message_tmp.rename(out_message)

def convert_item(item, out_folder):
    if item.name.startswith('Message'):
        convert_message(item, out_folder)
    elif item.name.startswith('Meeting'):
        print('skipping meeting', item)
    else:
        convert_folder(item, out_folder / item.name)

def convert_folder(folder, out_folder):
    for item in folder.iterdir():
        convert_item(item, out_folder)

if __name__ == '__main__':
    [item, out_folder] = sys.argv[1:]
    convert_item(Path(item), Path(out_folder))
