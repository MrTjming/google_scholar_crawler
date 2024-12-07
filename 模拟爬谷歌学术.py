import re
from time import sleep
from urllib import parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service

from databaseUtil import *
from printUtil import *


def parse_gb7714_citation(citation):
    # 定义正则表达式模式以匹配文章标题、期刊名称和发表年份
    pattern = r'^(.*?)\. (.*?)\[(.*?)\]\. (.*?)\, (\d{4})'

    match = re.match(pattern, citation)
    if match:
        # 提取匹配到的内容
        authors = match.group(1).strip()
        title = match.group(2).strip()
        journal_info = match.group(3).strip()
        journal_name = match.group(4).strip()
        year = match.group(5).strip()

        return {
            'title': title,
            'journal_name': journal_name,
            'year': year
        }
    else:
        return None


class GetBibs():
    def __init__(self, gg_search_url,chrome_driver_path,snapshot_date) -> None:
        # 当前检索的文章标题
        self.title = ''
        # 谷歌学术地址
        self.gg_search_url = gg_search_url
        # 创建 WebDriver 实例
        self.browser = webdriver.Chrome(service=Service(executable_path=chrome_driver_path), options=webdriver.ChromeOptions())
        self.snapshot_date=snapshot_date

    def deal_captcha(self):
        # 判断是是否为验证码页
        while len(self.browser.find_elements(By.ID, 'gs_captcha_ccl')) != 0:
            print_red("检测到验证码，请手动处理完后，再按回车继续")
            input()

    def extract_number(self, text):
        # 使用正则表达式匹配数字
        match = re.search(r'\d+', text)
        if match:
            return int(match.group())  # 返回数字部分并转换为整数
        return None

    # 进入被引用文献链接
    def get_title_to_google_scholar(self, paper_title):
        # 记录本次爬的文章标题
        self.title = paper_title

        # 拼接论文搜索url，并访问
        url = self.gg_search_url + parse.quote(paper_title)
        self.browser.get(url)
        self.deal_captcha()

        # 定位到搜索结果页的底栏
        bottom_list = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_fl gs_flb']")
        # 如果搜索到的论文数量超过1，报错
        if len(bottom_list) > 1:
            print_red(fr"论文标题查到不止一篇结果，请检查 【{paper_title}】")
            save_paper_info_if_absent(self.title, 0,"不唯一",self.snapshot_date)
            return

        links = (self.browser
                 .find_element(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl gs_fmar']")
                 .find_element(By.CSS_SELECTOR, "[class='gs_fl gs_flb']")
                 .find_elements(By.XPATH, "a"))

        cite_button = links[2]
        if not cite_button.accessible_name.startswith("被引用次数"):
            print_red(fr"论文没有被引用次数，请检查 【{paper_title}】")
            save_paper_info_if_absent(self.title, 0, "无引用", self.snapshot_date)
            return

        save_paper_info_if_absent(self.title, self.extract_number(cite_button.accessible_name), "正常", self.snapshot_date)

        # 点击目标论文的 “被引用次数”按钮
        cite_button.click()
        # 处理验证码
        self.deal_captcha()

        # 解析引用的文章
        self.get_data_from_google_scholar()

    def get_data_from_google_scholar(self):
        old_url = self.browser.current_url
        page_count = 0
        while True:
            try:
                # 处理第page_count 的引用文章搜索结果
                has_more_data = self.deal_with_page(page_count,old_url)
                if not has_more_data:
                    # 当前页没有数据了，结束搜索
                    break
                page_count = page_count+1
            except Exception as e:
                print_red("刷新页面，处理机器人验证后按回车")
                input()


    def deal_with_page(self,page_count,old_url):
        # 拼接第page_count页的引用论文的搜索页url
        url = old_url.split('scholar?')[0] + 'scholar?start=' + str(10 * page_count) + '&' + old_url.split('scholar?')[1]

        # 跳转搜索结果页，并处理验证码
        self.browser.get(url)
        self.deal_captcha()

        # 当前页面的10篇文章
        query_cited_result = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl']")
        if len(query_cited_result) == 0:
            # 没有更多数据了
            return False

        for i in range(len(query_cited_result)):
            # 解析当前页的第i个论文
            i_paper = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl']")[i]


            # 等待论文底栏加载完成,定位底栏的 “引用”按钮
            WebDriverWait(self.browser, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "[class='gs_fl gs_flb']"))
            )
            items = []
            while len(items) == 0:
                items = (i_paper
                         .find_element(By.CSS_SELECTOR, "[class='gs_fl gs_flb']")
                         .find_elements(By.XPATH, "a"))
            quote_button = items[1]

            # 等待“引用”按钮可点击之后，点击该按钮
            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(quote_button))
            quote_button.click()
            sleep(1.5)

            # 等待引用页加载完成
            WebDriverWait(self.browser, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "[class='gs_citr']"))
            )

            # 定位到gb774的引用内容
            citrs = []
            while len(citrs) == 0:
                citrs = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_citr']")
            gb774_cit = citrs[0].text

            # 解析引用格式
            result = parse_gb7714_citation(gb774_cit)
            if result:
                save_quote_info_if_absent(self.title, gb774_cit, result['title'], result['journal_name'], result['year'],self.snapshot_date)
            else:
                print_red(f"Failed to parse the citation.{gb774_cit}")
                save_quote_info_if_absent(self.title, gb774_cit, '', '', '',self.snapshot_date)

            # 点击关闭引用的x
            WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, 'gs_cit-x'))
            )
            self.browser.find_element(By.ID, "gs_cit-x").click()

        return True

if __name__ == '__main__':
    # 替换为本机实际 chromedriver 路径
    # chrome_driver_path = "/Users/liuchang/PycharmProjects/LPTHW/chromedriver-mac-arm64/chromedriver"

    # chrome_driver_path = r"C:\Users\刘畅\PycharmProjects\google_scholar_crawler\driver\chromedriver-win64\chromedriver.exe"

    chrome_driver_path = "/Users/bytedance/Downloads/生成式/字帖/chromedriver-mac-arm64/chromedriver"
    gg_search_url = r'https://scholar.google.com/scholar?hl=zh-CN&as_sdt=0%2C5&inst=1597255436240989024&q='
    snapshot_date = '20240909'
    # 创建爬虫对象
    get_bibs = GetBibs(gg_search_url,chrome_driver_path,snapshot_date)

    # 要爬取的文章标题
    paper_titles = [
                    'Multiwavelength high-order optical vortex detection and demultiplexing coding using a metasurface',
                    ]

    for title in paper_titles:
        print_yellow(f"----------start({title})-------------")
        get_bibs.get_title_to_google_scholar(title)
        print_green(f"----------end({title})-------------")
