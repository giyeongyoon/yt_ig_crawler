from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.tools import argparser
import time
import random
import pandas as pd
import os
import ssl
import argparse

ssl._create_default_https_context = ssl._create_unverified_context

parser = argparse.ArgumentParser(description="Youtube crawler")

parser.add_argument("--channel", type=str, help="Channel name")
parser.add_argument("--key", type=str, default="AIzaSyDJnM-CJ3K_jW0ROyKdj0x92uWhvGc1IiU", help="Youtube API KEY")
parser.add_argument("--filename", type=str, default="results.xlsx", help="File name to be saved")
parser.add_argument("--max_results_long", type=int, default=10, help="Max number of long videos to be scrawled")
parser.add_argument("--max_results_shorts", type=int, default=10, help="Max number of shorts to be scrawled")
parser.add_argument("--mode", choices=["long", "shorts", "all"], help="Target video type to be crawled")

group = parser.add_mutually_exclusive_group()
group.add_argument("--login", action="store_true", help="Login")
group.add_argument("--reset", action="store_true", help="Reset")
group.add_argument("--quit", action="store_true", help="Quit crawling")

args = parser.parse_args()


class YoutubeCrawler():
    def __init__(self, API_KEY):
        self.options = Options()
        # 로그인 유지
        self.options.add_argument(f"user-data-dir={os.getcwd()}")
        self.options.add_argument("disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("detach", True)
        self.options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        self.driver = webdriver.Chrome(".\chromedriver\chromedriver.exe", options=self.options)
        self.driver.maximize_window()
        
        self.base_url = "https://www.youtube.com/"
        
        self.sleep_time = 5
        self.interaction_time = 3
        
        self.long_css_selector = "div#contents.style-scope.ytd-rich-grid-renderer > ytd-rich-item-renderer a#thumbnail.yt-simple-endpoint.inline-block.style-scope.ytd-thumbnail"
        self.short_css_selector = "#contents > ytd-rich-item-renderer a.ShortsLockupViewModelHostEndpoint.reel-item-endpoint "
        
        self.channelId = ""
        self.videoId = []
        self.nickname = ""
        self.email = ""
        self.subscribers = 0
        self.likes = []
        self.views = []
        self.comments = []
        # self.df = pd.DataFrame()
        
        
        self.API_KEY = API_KEY # "AIzaSyDJnM-CJ3K_jW0ROyKdj0x92uWhvGc1IiU"
        YOUTUBE_API_SERVICE_NAME = "youtube"
        YOUTUBE_API_SERVICE_VERSION = "v3"

        self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_SERVICE_VERSION, developerKey = self.API_KEY)
        
    # 로그인
    def login(self):
        self.move_to_page(self.base_url)
        # 수동으로 로그인
        
    # 채널 아이디
    def get_channelId(self, channel_name):
        self.channel = self.youtube.search().list(
            q=channel_name,
            part="snippet",
            order="relevance",
            type="channel" 
        ).execute()
        
        self.channelId = self.channel['items'][0]['id']['channelId']
        
        return self.channelId
    
    # 비디오 아이디
    def get_videoId(self, css_selector, max_results=10):
        vids_endpoint = []
        vids = []
        vids_count = 0
        results_start = 0
        
        while vids_count < max_results:
            self.scroll_down()
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            #contents > ytd-rich-item-renderer:nth-child(1)
            vids_results = soup.select(css_selector)
            number_results = len(vids_results)
            
            for vid in vids_results[results_start:number_results]:
                vids.append(vid)
            
            vids_count = len(vids)
            
            if vids_count >= max_results or self.document_height_after == self.document_height_before:
                break
            
        
        if len(vids) >= max_results:
            vids = vids[:max_results]
            
        for v in vids:
            vids_endpoint.append(v.attrs["href"])
            
        if css_selector == self.long_css_selector:
            # /watch?v={videoId}
            self.videoId = [ve.split("?")[-1][2:].split("&")[0] for ve in vids_endpoint]
            
        else:
            # /shorts/{videoId}
            self.videoId = [ve.split("/")[-1].split("&")[0] for ve in vids_endpoint]
            
            
        return self.videoId
    
    # 닉네임(URL endpoint)
    def get_nickname(self):
        self.channel_response = self.youtube.channels().list(
            part="snippet, statistics",
            id=self.channelId
        ).execute()
        
        self.nickname = self.channel_response['items'][0]['snippet']['customUrl']
        
        return self.nickname
    
    # 이메일 주소
    def get_email(self, url):
        self.move_to_page(url)
        
        # 더보기
        self.driver.find_element(By.CSS_SELECTOR, "truncated-text.truncated-text-wiz > button").click()
        time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
        
        # 이메일 주소 보기
        try:
            self.driver.find_element(By.CSS_SELECTOR, "#view-email-button-container > yt-button-view-model > button-view-model > button").click()
            time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
        
            iframe_tag = self.driver.find_element(By.CSS_SELECTOR, "[title='reCAPTCHA']")
            self.driver.switch_to.frame(iframe_tag)
            
            self.driver.find_element(By.CSS_SELECTOR, ".recaptcha-checkbox-border").click()
            time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
            
            self.driver.switch_to.default_content()
            
            self.driver.find_element(By.CSS_SELECTOR, "#submit-btn").click()
            time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
            self.email = self.driver.find_element(By.CSS_SELECTOR, "a#email").text
        except:
            # print("이메일 주소 없음")
            self.email = ""
            
        # 닫기
        self.driver.find_element(By.CSS_SELECTOR, "#visibility-button button[aria-label='닫기']").click()
        time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
            
        return self.email
            
    # 구독자수
    def get_subscribers(self):        
        self.subscribers = int(self.channel_response['items'][0]['statistics']['subscriberCount'])
        
        return self.subscribers
    
    # 조회수/좋아요수/댓글수
    def get_vid_info(self):
        # print("videoId: ", self.videoId)
        for id in self.videoId:
            # print("id: ", id)
            video = self.youtube.videos().list(
                part="snippet, statistics",
                id=id
            ).execute()
            
            self.views.append(int(video['items'][0]['statistics']['viewCount']))
            self.likes.append(int(video['items'][0]['statistics']['likeCount']))
            self.comments.append(int(video['items'][0]['statistics']['commentCount']))
            
        return self.views, self.likes, self.comments
    
    def get_metadata(self, channel_name):
        self.get_channelId(channel_name)
        self.get_nickname()
    
    def scroll_down(self):
        scroll_height = 2000
        self.document_height_before = self.driver.execute_script("return document.documentElement.scrollHeight")
        self.driver.execute_script(f"window.scrollTo(0, {self.document_height_before + scroll_height});")
        time.sleep(random.uniform(self.interaction_time, self.interaction_time+2))
        self.document_height_after = self.driver.execute_script("return document.documentElement.scrollHeight")
        
    def move_to_page(self, url):
        self.driver.get(url)
        time.sleep(random.uniform(self.sleep_time, self.sleep_time+2))
    
    def quit(self):
        self.driver.quit()
        
    def crawl_long(self, channel_name, filename="videos.xlsx", save=True, max_results=10):
        # 채널 아이디 -> 닉네임 -> 이메일 -> 비디오 아이디 -> 구독자수 -> 조회수/좋아요수/댓글수
        self.get_metadata(channel_name)
        url = self.base_url + self.nickname + "/videos"
        self.get_email(url)
        self.get_videoId(self.long_css_selector, max_results=max_results)
        self.get_subscribers()
        self.get_vid_info()
        df = self.merge_data()
        
        if save:
            self.save(df, filename=filename)
            
        self.reset()
        
        return df
        
    
    def crawl_shorts(self, channel_name, filename="shorts.xlsx", save=True, max_results=10):
        self.get_metadata(channel_name)
        url = self.base_url + self.nickname + "/shorts"
        self.get_email(url)
        self.get_videoId(self.short_css_selector, max_results=max_results)
        self.get_subscribers()
        self.get_vid_info()
        df = self.merge_data()
        
        if save:
            self.save(df, filename=filename)
            
        self.reset()
        
        return df
    
    def crawl_all(self, channel_name, filename="all.xlsx", max_results_long=10, max_results_shorts=10):
        long_df = self.crawl_long(channel_name, save=False, max_results=max_results_long)
        short_df = self.crawl_shorts(channel_name, save=False, max_results=max_results_shorts)
        
        long_df["구분"] = ["동영상"] * long_df.shape[0]
        short_df["구분"] = ["쇼츠"] * short_df.shape[0]
        
        df = pd.concat([long_df, short_df], axis=0).reset_index(drop=True)
                    
        self.save(df, filename=filename)
        
        self.reset()
        
        return df
        
    def merge_data(self):
        df = pd.DataFrame({
            "비디오ID": self.videoId,
            "닉네임": self.nickname,
            "이메일": self.email,
            "구독자수": self.subscribers,
            "좋아요수": self.likes,
            "조회수": self.views,
            "댓글수": self.comments
        })
        
        return df
    
    def save(self, df, filename="results.xlsx", path="유튜브크롤링"):
        if not os.path.exists(path):
            os.makedirs(path)
            
        df.to_excel(os.path.join(path, filename))        
    
    def reset(self):
        self.channelId = ""
        self.videoId = []
        self.nickname = ""
        self.email = ""
        self.subscribers = 0
        self.likes = []
        self.views = []
        self.comments = []
        # self.df = pd.DataFrame()


if __name__ == "__main__":
    yt = YoutubeCrawler(args.key)
        
    if args.login:
        yt.login()
        
    if args.mode == "long":
        yt.crawl_long(channel_name=args.channel, filename=args.filename, max_results=args.max_results_long)
    elif args.mode == "shorts":
        yt.crawl_shorts(channel_name=args.channel, filename=args.filename, max_results=args.max_results_shorts)        
    elif args.mode == "all":
        yt.crawl_all(channel_name=args.channel, filename=args.filename, max_results_long=args.max_results_long, max_results_shorts=args.max_results_shorts)
        
    if args.reset:
        yt.reset()
        
    if args.quit:
        yt.quit()