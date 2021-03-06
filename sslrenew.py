#!/bin/python3
#Author: Maricius

import subprocess
import sys
import requests
import os
import xml.etree.ElementTree as ET
import time

target = str(sys.argv[1])

#base_url = 'https://api.sandbox.namecheap.com/xml.response'
base_url = 'https://api.namecheap.com/xml.response'
conf_file = 'ssl.conf'

lines = [line.strip().split('=') for line in open(conf_file)]
config = {}

ns = {
    "api": "http://api.namecheap.com/xml.response"
}
for line in lines:

    config[line[0]] = line[1]

key  = config['apikey']
user = config['user']
ip   = config['clientip']


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
    print("Successfully retrived domain info")
    return data


def make_dir(info, filename):

    home_path = info['home']+'/public_html'
    user_id = info['uid']
    group_id = info['ugid']

    command1 = 'mkdir -p ' + home_path+'/.well-known/pki-validation/'
    command2 = 'chown -R ' + user_id+':'+group_id + ' ' + home_path+'/.well-known/'

    subprocess.run(['ssh', target, command1 + ' && ' + command2])

    subprocess.run(['scp', filename, target+':'+home_path+'/.well-known/pki-validation/'])
    os.remove(filename)
    return()

def create_ssl(*type):


    if type:
        ssl_type=type[0]
    else:
        ssl_type = "PositiveSSL"
    cmd = 'namecheap.ssl.create'
    params = {'ApiUser': user, 'ApiKey': key, 'UserName': user, 'Command': cmd, 'ClientIP': ip, 'Years': 1, 'Type': ssl_type}
    r = requests.post(base_url, data=params)
    r.raw.decode_content = True

    root = ET.fromstring(r.content)

    for child in root:
        for kid in child:
            for baby in kid:
                cert_id = baby.get('CertificateID')
    print("Successfully created SSL with ID: " + cert_id)
    return(cert_id)


def activate_ssl(id,csr):
    cmd = 'namecheap.ssl.activate'
    params = {'ApiUser': user, 'ApiKey': key, 'UserName': user, 'Command': cmd, 'ClientIP':ip, 'CertificateID':id, 'HTTPDCValidation':'TRUE', 'csr':csr,
              'WebServerType':'apache2', 'AdminFirstName':config['AdminFirstName'], 'AdminLastName':config['AdminLastName'],
              'AdminAddress1':config['AdminAddress1'], 'AdminEmailAddress':config['AdminEmailAddress']}

    r = requests.get(base_url, params=params)
    r.raw.decode_content = True

    root = ET.fromstring(r.content)
    #filename = root.find(".//api:CommandResponse/api:SSLActivateResult/api:HttpDCValidation/api:DNS/api:FileName",ns).text
    #filecontent = root.find(".//api:CommandResponse/api:SSLActivateResult/api:HttpDCValidation/api:DNS/api:FileContent",ns).text
    filename = root.find(".//api:FileName",ns).text
    filecontent = root.find(".//api:FileContent",ns).text

    y = open(filename, "w")
    y.write(filecontent)
    print("Successfully activated SSL certificate, Waiting http validation...")
    return(filename)


def get_cert_status(id):
    cmd = 'namecheap.ssl.getinfo'



    params = {'ApiUser': user, 'ApiKey': key, 'UserName': user, 'Command': cmd, 'ClientIp': ip, 'certificateID': id,
              'returncertificate': 'true', 'returntype': 'individual'}
    r = requests.get(base_url, data = params)
    r.raw.decode_content = True
    root = ET.fromstring(r.content)
    for child in root:
        for kid in child:
            status = kid.get('StatusDescription')
    #status = root.find(".//api:CommandResponse/api:SSLGetInfoResult/api:StatusDescription",ns).text

    #print(r.text)
    #return(status)
    return(status)

def generate_csr(domain):
    domain = domain

    country = input('Country?')
    org = domain
    cn = 'www.'+domain
    email = input('email?')
    state = input('state')
    cmd = 'virtualmin generate-cert --domain ' +domain+ ' --cn '+cn+' --ou IT --c '+country+ ' --l odense --o ' +org+ '  --email '+email+ ' --st '+state+ ' --size 2048 --sha2 --csr'
    home_path = domain_info['home']+'/'
    #print(cmd)
    subprocess.run(['ssh', target, cmd])
    subprocess.run(['scp', target+':'+home_path+'ssl.csr', 'ssl.csr'])
    with open('ssl.csr', 'r') as csr_file:
        csr=csr_file.read()
    os.remove('ssl.csr')
    print("Successfully created CSR")
    return csr

def download_cert(cert_id):
    cmd = 'namecheap.ssl.getinfo'

    params = {'ApiUser': user, 'ApiKey': key, 'UserName': user, 'Command': cmd, 'ClientIp': ip, 'certificateID': cert_id,
              'returncertificate': 'true', 'returntype': 'individual'}
    r = requests.get(base_url, data=params)
    r.raw.decode_content = True

    root = ET.fromstring(r.content)
    certificate = root.find(".//api:Certificates/api:Certificate", ns).text

    CA_certificate = ""

    for CA in root.findall(".//api:Certificate/api:Certificate", ns):
        CA_certificate += CA.text+"\n"
    #print(r.text)

    cert = open("ssl.cert", "w")
    cert.write(certificate)

    CA = open("ssl.ca", "w")
    CA.write(CA_certificate)
    cert.close()
    CA.close()
    return()

def apply_cert(info, target):
    home_path = info['home']+'/'

    subprocess.run(['scp', 'ssl.cert', target + ':' + home_path])
    os.remove("ssl.cert")
    subprocess.run(['scp', 'ssl.ca', target + ':'+home_path])
    os.remove("ssl.ca")
    subprocess.run(['ssh', target, 'virtualmin install-cert --domain ' +target+ ' --cert ' +home_path+'ssl.cert  --ca '+home_path+'ssl.ca --csr '+home_path+'ssl.csr --use-newkey'])
    return()
#get_info -> generate_csr -> Create_ssl -> activate_ssl ->  make_dir



domain_info = get_info(target)

csr = generate_csr(target)
cert_id = create_ssl()
file = activate_ssl(cert_id, csr)
make_dir(domain_info, file)
status = get_cert_status(cert_id)
while status == "Being Processed.":

    time.sleep(5)
    status = get_cert_status(cert_id)
    print("Status: "+status)

print("SSL activation complete final status: "+ status)


download_cert(cert_id)

apply_cert(domain_info, target)
print("SSL certicate successfully applied")
#make_dir(domain_info)

#create_ssl()

