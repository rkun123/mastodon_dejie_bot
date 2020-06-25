import os
import re
import time
from mastodon import Mastodon, StreamListener
import requests
from bs4 import BeautifulSoup
from operator import attrgetter
import sys
from dotenv import load_dotenv

def login(mastodon_url, access_token):
    mastodon = Mastodon(
        access_token = access_token,
        api_base_url = mastodon_url
    )
    return mastodon

class Dejie:
    class Notification:
        def __init__(self, title, id, url):
            self.title = title
            self.id = id
            self.url = url

        def __lt__(self, other):
            if self.id < other.id:
                return -1
            elif self.id > other.id:
                return 1
            else:return 0
            
        def __hash__(self):
            return hash((self.id, self.title, self.url))

        def __str__(self):
            return "{0}\n{1}".format(
                self.title,
                self.url
                    )

    def __init__(self, url, latest_id_file_path):
        self.baseURL = url
        self.latest_id_file_path = latest_id_file_path
        self.latest_id = 0
    
    def update(self):
        html = self.fetch()
        parsed_list = self.parse(html)
        unknown_notifications_list = []

        for notification in parsed_list:
            if notification.id > self.latest_id:
                unknown_notifications_list.append(notification)
        #sorted_notifications_list = sorted(unknown_notifications_list, key=attrgetter('id'))
        sorted_notifications_list = unknown_notifications_list
        self.latest_id = parsed_list[0].id
        return sorted_notifications_list

    def fetch(self):
        try:
            res = requests.get(self.baseURL)
            return res.text
        except:
            print("[Error] Fetch error")
            return

    def parse(self, html):
        notification_list = []
        soup = BeautifulSoup(html, 'html.parser')

        try:
            entry_list = soup.find('table', 'dz_recordTable').findAll('tr')
        except:
            print("[Error] Error on parse")
            return None
        
        for entry in entry_list:
            columns = entry.findAll('td')
            if len(columns) > 4 and "record-value" in columns[2]['id']:
                try:
                    id = int(re.search("[0-9]+$", columns[2]['id']).group())
                    title = columns[2].get_text()
                    url = "{0}{1}".format(re.search("^.*/", self.baseURL).group(), columns[0].find('table').find('tr').find('td').find('a')['href'])
                    notification_list.append(self.Notification(title, id, url))
                except:
                    print("Error on parse notification list")
                    print(entry[2])
        return notification_list
    
    def load_state(self):
        try:
            with open(self.latest_id_file_path, mode='tr') as f:
                id = int(f.readline())
                print("[Load] State is {0}", id)
                self.latest_id = id
        except:
            print("[Error] Error while read state file")
    def save_state(self):
        try:
            with open(self.latest_id_file_path, mode='tw') as f:
                f.write(str(self.latest_id))
                print("[Save] State is {0}".format(self.latest_id))
        except:
            print("[Error] Error while save state file")


if __name__ == "__main__":
    is_dry = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "-t":
            is_dry = False

    load_dotenv()
    BASE_URL = os.getenv("BASE_URL", "https://db.jimu.kyutech.ac.jp/cgi-bin/cbdb/db.cgi?page=DBView&did=357")
    MASTODON_URL = os.getenv("MASTODON_URL")
    ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN")
    m = login(MASTODON_URL, ACCESS_TOKEN)

    d = Dejie(BASE_URL, os.path.join(os.getcwd(), "latest_state"))
    d.load_state()
    news = d.update()
    print(len(news))
    for new in news:
        print(new)
        if not is_dry:
            m.toot("[デヂエ・お知らせ]\n{}\n#いきなりステーキ九州通信".format(new))
    d.save_state()
