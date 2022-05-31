from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
import requests
from bs4 import BeautifulSoup
import os
from openpyxl import Workbook
import re

paper_names = {}


def spider_baidu(url, exam_path, work_sheet, year, exam_id):
    try:
        driver = webdriver.Chrome()
        driver.get(url)
        sleep(1)
        if url != driver.current_url:
            if driver.current_url == 'https://tiku.baidu.com/tikucommon/404':
                print('Got 404: %s' % url)
                sleep(1)
                return False
            print('Error when get url: %s' % url)
            print('Current url is %s' % driver.current_url)
            exit()
        title = driver.find_element(By.CLASS_NAME, 'title').text
        subject = ''
        if '语文' in title:
            subject = 'chinese'
        elif '数学' in title:
            subject = 'math'
        elif '英语' in title:
            subject = 'english'
        elif '物理' in title:
            subject = 'physics'
        elif '化学' in title:
            subject = 'chemistry'
        elif '生物' in title:
            subject = 'biology'
        elif '政治' in title:
            subject = 'politics'
        elif '历史' in title:
            subject = 'history'
        elif '地理' in title:
            subject = 'geo'
        elif '文综' in title:
            subject = 'geo'
        elif '理综' in title:
            subject = 'chemistry'
        else:
            print('Cannot tell the subject of exam %s' % title)
            return False
        questions = driver.find_elements(By.CLASS_NAME, 'question-box')
        for i in range(len(questions)):
            if os.path.exists('%s%d.html' % (exam_path, i)) and os.path.exists('%s%d_answer.html' % (exam_path, i)):
                continue
            question = questions[i]
            question.click()
            sleep(1)

            with open('%s%s_%d.html' % (exam_path, exam_id, i), 'w') as f:
                f.write(question.get_attribute('outerHTML'))

            try:
                answers = driver.find_elements(By.CLASS_NAME, 'queanalyse-wrap')
            except Exception as e:
                print('Cannot find answers in exam %s, question %d' % (title, i))
                continue
            with open('%s%s_%d_answer.html' % (exam_path, exam_id, i), 'w') as f:
                for answer in answers:
                    f.write(answer.get_attribute('outerHTML'))

        work_sheet.append([title, url, year, subject, '12', '%d_%d' % (year, exam_id)])
        paper_names[title] = True
        return True
    except Exception as e:
        #print(e)
        return None


if __name__ == '__main__':
    root_path = os.environ['HOME'] + '/GaoKao_origin/'
    if not os.path.exists(root_path):
        os.mkdir(root_path)
    exam_path = '%ssource_html/' % root_path
    if not os.path.exists(exam_path):
        os.mkdir(exam_path)
    excel_path = '%sexcel/' % root_path
    if not os.path.exists(excel_path):
        os.mkdir(excel_path)
    for year in range(2021, 2012, -1):
        exam_id = 0
        work_book = Workbook()
        work_sheet = work_book.active
        table_title = ['Name', 'Url', 'Year', 'Subject', 'Grade', 'rid']
        for col in range(len(table_title)):
            work_sheet.cell(row=1, column=col+1, value=table_title[col])
        year_path = '%s%dGaoKao' % (exam_path, year)
        if not os.path.exists(year_path):
            os.mkdir(year_path)
        for i in range(1, 50):
            url = 'https://tiku.baidu.com/tikupc/paperlist/1bfd700abb68a98271fefa04-0-1-%d-0-%d-download' % (year, i)
            content = requests.get(url)
            content.encoding = 'utf-8'
            soup = BeautifulSoup(content.text, 'lxml')
            page_sum = soup.select('.page-sum')[0].text
            total_page = re.search(r'共(\d+)页', page_sum).group(1)
            if i > int(total_page):
                break
            exams = soup.select('.paper-a')
            for exam in exams:
                if exam.text in paper_names.keys():
                    continue
                path = '%s/%d_%d/' % (year_path, year, exam_id)
                if not os.path.exists(path):
                    os.mkdir(path)
                result = spider_baidu('https://tiku.baidu.com%s' % exam.get('href'), path, work_sheet, year, exam_id)
                if result is None:
                    print('Error in spidering ,sleep 30s and retry')
                    sleep(30)
                    result = spider_baidu('https://tiku.baidu.com%s' % exam.get('href'), path, work_sheet, year,
                                          exam_id)
                if result:
                    exam_id += 1
                    with open('%s%s.txt' % (path, exam.text), 'w') as f:
                        f.write(exam.text)
        work_book.save(filename='%s%dGaoKao.xlsx' % (excel_path, year))
