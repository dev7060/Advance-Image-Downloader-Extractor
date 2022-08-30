import argparse
from datetime import datetime
import schedule
import time
import pyshorteners
from filestack import Client
from filestack import Security
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os, shutil
import requests
import urllib.request
from bs4 import BeautifulSoup
import logging

logging.basicConfig(filename="newfile.log", format='%(asctime)s %(message)s', filemode='w')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.info("Main started")

def images_directory_create():
    logger.info("Creating the images directory")    
    current_directory = os.getcwd()
    final_directory = os.path.join(current_directory, r'images')
    if not os.path.exists(final_directory):
        os.makedirs(final_directory)
    logger.info("Durectory created")    

def images_folder_clearer():
    logger.info("Clearing the images folder")    
    folder = './images'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    logger.info("Images folder cleared")    

def link_emailer(link, email, name):
    logger.info("Preparing data to email")  
    mail_content = "Download Link: " + link
    sender_address = ''
    sender_pass = ''
    receiver_address = email
    message = MIMEMultipart()
    message['From'] = sender_address
    message['To'] = receiver_address
    message['Subject'] = 'Download ' + name + " images"
    message.attach(MIMEText(mail_content, 'plain'))
    session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
    session.starttls() #enable security
    session.login(sender_address, sender_pass)
    text = message.as_string()
    session.sendmail(sender_address, receiver_address, text)
    session.quit()
    logger.info("Mail sent")  
    print('mail sent')

def zip_file_upload():
    logger.info("Uploaing the zip file")  
    policy = {'expiry': ''} #int value rhs
    security = Security(policy, '')
    client = Client('', security=security)
    new_filelink = client.upload(filepath='./images.zip')
    #print(new_filelink.url)
    file_url = new_filelink.url + '?signature=&policy='
    logger.info("Zip upload done. Long URL generated")  
    return file_url 

def my_link_shortener(link):
    logger.info("Generating shortlink")       
    s = pyshorteners.Shortener(api_key='')
    logger.info("Shortlink generated")
    return s.bitly.short(link)

def getdata(url): 
    r = requests.get(url) 
    return r.text

def images_download_to_folder(images):
    logger.info("Downloading images to folder")
    i = 0
    for link in images:
        i = i+1
        f = open('images/'+str(i) + '.jpg','wb')
        f.write(requests.get(link).content)
        f.close()
    logger.info("Images has been downloaded to the folder")

def make_zip():
    logger.info("Started to make images folder archive")
    shutil.make_archive('images' , 'zip', 'images')
    logger.info("Archive made")

def job(name, email):
    logger.info("Job started")
    my_client_id = ""
    pixabay_key = ""
    max_images = 50
    query = name
    images = []     
    #yandex scraping
    htmldata = getdata("https://yandex.com/images/search?text=" + query) 
    soup = BeautifulSoup(htmldata, 'html.parser') 
    for item in soup.find_all('img'):
        if len(images) >= max_images:
	        break
        mystr = "https:"
        mystr = mystr + item['src']
        images.append(mystr)
    images = images[1:-1]
    #unsplash scraping
    htmldata = getdata("https://unsplash.com/s/photos/" + query) 
    soup = BeautifulSoup(htmldata, 'html.parser') 
    for item in soup.find_all('img'):
        if len(images) >= max_images:
	        break
        images.append(item['src'])
    #using unsplash api
    URL = "https://api.unsplash.com/search/photos"
    PARAMS = {'page':1, "query":query, "client_id": my_client_id}
    r = requests.get(url = URL, params = PARAMS)
    data = r.json()
    for i in range (0, data['total_pages']):
        if len(images) >= max_images:
            break
        PAGE_PARAMS = {'page':i+1, "query":query, "client_id":""}
        page_r = requests.get(url = URL, params = PAGE_PARAMS)
        page_data = page_r.json()
        for j in range(0, 10):
            if len(images) >= max_images:
                break
            images.append(page_data['results'][j]['urls']['small_s3'])
    #pixabay api
    URL = "https://pixabay.com/api/"
    PARAMS = {"page": 1, "q":query, "key": pixabay_key, "image_type":"photo"}
    r = requests.get(url = URL, params = PARAMS)
    data = r.json()
    for i in range (0, data['total']):
        if len(images) >= max_images:
            break
        PAGE_PARAMS = {'page':i+1, "q":query, "key": pixabay_key, "image_type":"photo"}
        page_r = requests.get(url = URL, params = PAGE_PARAMS)
        page_data = page_r.json()
        for j in range(0, 20):
            if len(images) >= max_images:
                break
            images.append(page_data['hits'][j]['webformatURL'])
    logger.info("Images links array done")    
    images_directory_create()
    images_download_to_folder(images)
    make_zip()
    images_folder_clearer()
    long_link = zip_file_upload()
    short_link = my_link_shortener(long_link)
    link_emailer(short_link, email, name)
    print('job done')
    logger.info("Job completed")
    return schedule.CancelJob

def job_scheduler(name, date_time_str, email):
    logger.info("Job scheduler called")    
    date_time_obj = datetime.strptime(date_time_str + ':00', '%Y-%m-%d %H:%M:%S')
    current_time = datetime.now()
    current_formatted_date_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    current_formatted_date_time = datetime.strptime(current_formatted_date_time, '%Y-%m-%d %H:%M:%S')
    #print((date_time_obj-current_formatted_date_time).total_seconds())
    schedule.every((date_time_obj-current_formatted_date_time).total_seconds()).seconds.do(job, name, email)
    while True:
        schedule.run_pending()
        time.sleep(1)

def args_pass():
    logger.info("args_pass begin")
    parser = argparse.ArgumentParser(description="Input Name, Date, Time and Email")
    parser.add_argument("name", type=str)
    parser.add_argument("date", type=str)
    parser.add_argument("time", type=str)
    parser.add_argument("email", type=str)
    args = parser.parse_args()
    logger.info("Name: " + args.name + " Date: " + args.date + " Time: " + args.time + " Email: " + args.email)
    logger.info("Scheduling the job")
    job_scheduler(args.name, args.date + ' ' + args.time, args.email)

args_pass()
