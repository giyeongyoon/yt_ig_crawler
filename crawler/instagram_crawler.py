from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
import re
import pandas as pd
import os
import argparse

parser = argparse.ArgumentParser(description="Instagram crawler")

parser.add_argument("--account", type=str, help="Account name")
parser.add_argument("--filename", type=str, default="results.xlsx", help="File name to be saved")
parser.add_argument("--max_results_feeds", type=int, default=10, help="Max number of feeds to be scrawled")
parser.add_argument("--max_results_reels", type=int, default=10, help="Max number of reels to be scrawled")
parser.add_argument("--mode", choices=["feeds", "reels", "all"])

group = parser.add_mutually_exclusive_group()
group.add_argument("--login", action="store_true", help="Login")
group.add_argument("--reset", action="store_true", help="Reset")
group.add_argument("--quit", action="store_true", help="Quit crawling")

args = parser.parse_args()


def load_credentials(file_path):
    credentials = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split('=', 1)
            credentials[key.strip()] = value.strip()
    return credentials

cred = load_credentials("secret.txt")
id = cred["username"]
pw = cred["password"]

class InstaCrawler():
    def __init__(self):
        self.options = Options()
        # 로그인 유지
        self.options.add_argument(f"user-data-dir={os.getcwd()}")
        self.options.add_argument("disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("detach", True)
        self.options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        self.driver = webdriver.Chrome(".\chromedriver\chromedriver.exe", options=self.options)
        self.driver.maximize_window()
        
        self.base_url = "https://www.instagram.com/"
        self.id = id
        self.pw = pw
        
        self.sleep_time = 5
        self.interaction_time = 3
        
        self.nickname = ""
        self.email = ""
        self.followers = 0
        self.likes = []
        self.views = []
        self.comments = []
        self.path_feeds = []
        self.path_reels = []
        # self.df = pd.DataFrame()
    
    def login(self):
        self.move_to_page(self.base_url)
        
        username = self.driver.find_element(By.CSS_SELECTOR, "input[name='username']")
        username.send_keys(self.id)
        
        password = self.driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        password.send_keys(self.pw)
        
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        time.sleep(random.uniform(self.interaction_time, self.sleep_time+2))
    
    def move_to_page(self, url):
        self.driver.get(url)
        time.sleep(random.uniform(self.sleep_time, self.sleep_time+2))
    
    def get_nickname(self):
        self.nickname = self.driver.find_element(By.CSS_SELECTOR, "span.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.x1ji0vk5.x18bv5gf.x193iq5w.xeuugli.x1fj9vlw.x13faqbe.x1vvkbs.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x1i0vuye.xvs91rp.x1s688f.x5n08af.x10wh9bi.x1wdrske.x8viiok.x18hxmgj").text
        
        return self.nickname
    
    def get_followers(self):
        self.followers = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/followers/']").text.replace('팔로워', '').strip()
        
        return self.followers
    
    def get_email(self):
        text = self.driver.find_element(By.CSS_SELECTOR, "span._ap3a._aaco._aacu._aacx._aad7._aade").text

        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_address = re.search(email_pattern, text)

        if email_address:
            self.email = email_address.group()
        else:
            self.email = ""
            print("이메일을 찾을 수 없습니다.")
            
        return self.email
    
    def get_likes_count(self):
        likes_count = self.driver.find_element(By.CSS_SELECTOR, "a[href*='liked_by'] > span > span").text
        
        return likes_count
    
    def get_comments_count(self):
        # 더보기 클릭
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        more_btn = soup.select_one("button:has([aria-label='댓글 더 읽어들이기'])")

        while more_btn is not None:
            self.driver.find_element(By.CSS_SELECTOR, "button:has([aria-label='댓글 더 읽어들이기'])").click()
            time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            more_btn = soup.select_one("button:has([aria-label='댓글 더 읽어들이기'])")
            
        # 답글수
        reply_btns = soup.find_all("span", string=re.compile("^답글 보기"))
        reply_count = [int(reply.text[6:-2]) for reply in reply_btns]
        replys = sum(reply_count)

        # 댓글수
        try:
            comments_tags = self.driver.find_elements(By.CSS_SELECTOR, "div.x78zum5.xdt5ytf.x1iyjqo2.xs83m0k.x2lwn1j.x1odjw0f.x1n2onr6.x9ek82g.x6ikm8r.xdj266r.x11i5rnm.x4ii5y1.x1mh8g0r.xexx8yu.x1pi30zi.x18d9i69.x1swvt13 > ul > div:nth-child(3) > div > div > div img")
            comments = len(comments_tags)
        except:
            comments = 0
        
        # 답글수+댓글수
        comments_count = replys + comments
        
        return comments_count     
    
    def get_feeds_info(self, max_results=10):
        # 첫번째 피드 클릭 -> 좋아요수 -> 댓글수 -> url -> 다음 클릭
        feeds_count = 0
        self.driver.find_element(By.CSS_SELECTOR, "div._ac7v > div:nth-of-type(1)").click()
        time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
        while feeds_count < max_results:
            self.likes.append(self.get_likes_count())
            self.comments.append(self.get_comments_count())
            self.path_feeds.append(self.driver.current_url.split("/")[4])
            
            feeds_count += 1
            
            try:
                self.driver.find_element(By.CSS_SELECTOR, "div._aaqg._aaqh > button").click()
                time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
            except:
                break
        
    def get_reels_info(self, max_results=10):
        # 스크롤 -> 조회수 & url
        reels = []
        reels_count = 0
        results_start = 0
        
        while reels_count < max_results:
            self.scroll_down()
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            reels_results = soup.select("div._ac7v > div")
            number_results = len(reels_results)
            
            for reel in reels_results[results_start:number_results]:
                reels.append(reel)
                
            reels_count = len(reels)
                
            if reels_count >= max_results or self.document_height_after == self.document_height_before:
                break
            
        if len(reels) > max_results:
            reels = reels[:max_results]
            
        for r in reels:
            self.views.append(r.select_one("._aajy > div > span > span").text) 
            self.path_reels.append(r.select_one("a").attrs["href"].split("/")[3])
        
        # 첫번째 피드 클릭 -> 좋아요수 -> 댓글수 -> 다음 클릭
        reels_count = 0
        first_tag = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div._ac7v > div:nth-of-type(1)")))
        first_tag.click()
        # self.driver.find_element(By.CSS_SELECTOR, "div._ac7v > div:nth-of-type(1)").click()
        time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
        while reels_count < max_results:
            self.likes.append(self.get_likes_count())
            self.comments.append(self.get_comments_count())
            
            reels_count += 1
            
            try:
                self.driver.find_element(By.CSS_SELECTOR, "div._aaqg._aaqh > button").click()
                time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
            except:
                break
        
    def scroll_down(self):
        scroll_height = 2000
        self.document_height_before = self.driver.execute_script("return document.documentElement.scrollHeight")
        self.driver.execute_script(f"window.scrollTo(0, {self.document_height_before + scroll_height});")
        time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
        self.document_height_after = self.driver.execute_script("return document.documentElement.scrollHeight")
        
    def crawl_feeds(self, account_name, filename="feeds.xlsx", max_results=10, save=True):
        self.move_to_page(self.base_url + account_name)
        self.get_nickname()
        self.get_email()
        self.get_followers()
        self.get_feeds_info(max_results=max_results)
        
        df_feeds = pd.DataFrame({
            "닉네임": self.nickname,
            "이메일": self.email,
            "팔로워수": self.followers,
            "좋아요수": self.likes,
            "댓글수": self.comments,
            "Path": self.path_feeds
        })
        
        if save:
            self.save(df_feeds, filename=filename)
            
        self.reset()
        
        return df_feeds
        
    
    def crawl_reels(self, account_name, filename="reels.xlsx", max_results=10, save=True):
        self.move_to_page(self.base_url + account_name + "/reels/")
        self.get_nickname()
        self.get_email()
        self.get_followers()
        self.get_reels_info(max_results=max_results)
        
        df_reels = pd.DataFrame({
            "닉네임": self.nickname,
            "이메일": self.email,
            "팔로워수": self.followers,
            "좋아요수": self.likes,
            "조회수": self.views,
            "댓글수": self.comments,
            "Path": self.path_reels
        })
        
        if save:
            self.save(df_reels, filename=filename)
            
        self.reset()
        
        return df_reels
        
    def quit(self):
        self.driver.quit()
        
    def reset(self):
        self.nickname = ""
        self.email = ""
        self.followers = 0
        self.likes = []
        self.views = []
        self.comments = []
        self.path_feeds = []
        self.path_reels = []
        # self.df = pd.DataFrame()
    
    def crawl_all(self, account_name, filename="all.xlsx", max_results_feeds=10, max_results_reels=10):
        df_feeds = self.crawl_feeds(account_name, save=False, max_results=max_results_feeds)
        df_reels = self.crawl_reels(account_name, save=False, max_results=max_results_reels)
        
        df = pd.merge(df_feeds, df_reels, on=["닉네임", "이메일", "팔로워수", "좋아요수", "댓글수", "Path"], how="outer")
        
        df = df.fillna(0)
        
        self.save(df, filename=filename)
        
        self.reset()
        
        return df
    
    def save(self, df, filename="insta_results.xlsx", path="인스타크롤링"):
        if not os.path.exists(path):
            os.makedirs(path)
            
        df.to_excel(os.path.join(path, filename))    
        
        
if __name__ == "__main__":
    ig = InstaCrawler()
        
    if args.login:
        ig.login()
        
    if args.mode == "feeds":
        ig.crawl_feeds(account_name=args.account, filename=args.filename, max_results=args.max_results_feeds)
    elif args.mode == "reels":
        ig.crawl_reels(account_name=args.account, filename=args.filename, max_results=args.max_results_reels)
    elif args.mode == "all":
        ig.crawl_all(account_name=args.account, filename=args.filename, max_results_feeds=args.max_results_feeds, max_results_reels=args.max_results_reels)
        
    if args.reset:
        ig.reset()
        
    if args.quit:
        ig.quit()