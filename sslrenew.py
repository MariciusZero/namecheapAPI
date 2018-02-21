#!/bin/python3
#Author: Maricius


import subprocess
import sys
import requests
import os
import xml.etree.ElementTree as ET

target = str(sys.argv[1])

conf_file = 'ssl.conf'
lines = [line.strip().split('=') for line in open('ssl.conf')]
config = {}
for line in lines:
    config[line[0]] = line[1]

key  = config['apikey']
user = config['user']
ip   = config['clientip']
cmd = ''
base_url = 'https://api.sandbox.namecheap.com/xml.response?ApiUser='+user+'&ApiKey='+key+'&UserName='+user+'&Command='+cmd+''

def get_info(domain):

    y = open("domaininfo.tmp", "w")
    command = 'grep -Ril  "^dom='+domain+'"  /etc/webmin/virtual-server/domains/ | xargs  cat'
    subprocess.run(['ssh', target, command], stdout=y)
    y.close()

    lines = [line.rstrip('\n').split('=') for line in open('domaininfo.tmp')]
    data = {}

    for line in lines:
        data[line[0]] = line[1]
    os.remove("domaininfo.tmp")

    return data


def make_dir(info):

    home_path = info['home']+'/public_html'
    user_id = info['uid']
    group_id = info['ugid']

    command1 = 'mkdir -p ' + home_path+'/.well-known/pki-validation/'
    command2 = 'chown -R ' + user_id+':'+group_id + ' ' + home_path+'/.well-known/'

    subprocess.run(['ssh', target, command1 + ' && ' + command2])


def upload_file(domain):
    subprocess.run(['scp -P 4975', target, ''])


def renew_ssl(signing_request):
    print(signing_request)


def create_ssl(*type):
    if type:
        ssl_type=type[0]
    else:
        ssl_type = "PositiveSSL"

    r = requests.post('https://api.sandbox.namecheap.com/xml.response?ApiUser='+user+'&ApiKey='+key+'&UserName='+user+'&Command=namecheap.ssl.create&ClientIp='+ip+'&Years=1&Type='+ssl_type)
    r.raw.decode_content = True

    root = ET.fromstring(r.content)

    for child in root:
        for kid in child:
            for baby in kid:
                cert_id = baby.get('CertificateID')
    return(cert_id)


    #print(r)
    #print(tree)
def activate_ssl(id,csr):
    cmd = ''
    r = requests.post('''https://api.sandbox.namecheap.com/xml.response?ApiUser='+user+'&ApiKey='+key+'&UserName='+user+'
    &Command=namecheap.ssl.activate&ClientIp='+ip+'&CertificateID='+id+'&HTTPDCValidation=TRUE&csr='+csr+'&WebServerType=apache2
    &AdminFirstName=Red&AdminLastName=Web&AdminAddress1=Blangstedgårdsvej 1''')

def get_cert_status(id):
    cmd = 'namecheap.ssl.getinfo'
    params =
    r = requests.get(base_url+'&certificateID='+id+'&ClientIp='+ip+'&returncertificate=true&returntype=individual')
    r.raw.decode_content = True
    #print(r.content)
    print(r.text)


def generate_csr(domain):
    domain = domain
    country = input('Country?')
    org = domain
    email = input('email?')
    state = input('state')
    home_path = domain_info['home']+'/'
    subprocess.run(['ssh', target, 'virtualmin generate-cert --domain ' +domain+ ' --ou IT --c '+country+ ' --l odense --o ' +org+ '  --email '+email+ ' --st '+state+ ' --size 2048 --sha2 --csr'])
    subprocess.run(['scp', target+':'+home_path+'ssl.csr', 'ssl.csr'])
    with open('ssl.csr', 'r') as csr_file:
        csr=csr_file.read()
    os.remove('ssl.csr')
    return csr


#get_cert_status('951671')

#create_ssl('PositiveSSl')
#domain_info = get_info(target)
#csr = generate_csr(target)
#make_dir(domain_info)

create_ssl()

