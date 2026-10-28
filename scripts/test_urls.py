import urllib.request
import ssl
import sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = {
    'AICTE Approved Dashboard': 'https://facilities.aicte-india.org/dashboard/pages/angulardashboard.php#!/approved',
    'AISHE Directory': 'https://dashboard.aishe.gov.in/hedirectory/',
    'PSG College of Technology': 'https://www.psgtech.edu',
    'COEP Tech University': 'https://www.coeptech.ac.in',
    'COEP (alt)': 'https://www.coep.org.in',
    'Delhi Technological University': 'https://www.dtu.ac.in',
    'VJTI Mumbai': 'https://vjti.ac.in',
    'Jadavpur University': 'http://www.jaduniv.edu.in',
    'Jadavpur University (alt)': 'https://jadavpuruniversity.in',
    'BMS College of Engineering': 'https://bmsce.ac.in',
    'The National Institute of Engineering (NIE)': 'https://nie.ac.in',
    'Harcourt Butler Technical University (HBTU)': 'https://hbtu.ac.in',
    'Thapar Institute': 'https://www.thapar.edu',
    'College of Engineering Guindy': 'https://ceg.annauniv.edu',
    'Anna University': 'https://www.annauniv.edu'
}

for name, u in urls.items():
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            print(f'{name}: OK ({resp.status}) -> {resp.url}', flush=True)
    except Exception as e:
        print(f'{name}: FAILED -> {e}', flush=True)
