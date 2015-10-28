# coding: utf-8
__author__ = 'zzg'
'''
rebuild in: 2015-10-24
'''

import requests
import MySQLdb
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
from copy import deepcopy


class Spider:
    def __init__(self, url):
        self.login_header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                                           'Ubuntu Chromium/44.0.2403.89 '
                                           'Chrome/44.0.2403.89 '
                                           'Safari/537.36'}
        self.connectionParament = {'Connection': 'keep-alive', 'Referer': None}
        self.loginPage = None
        self.postDict = {}  # url后缀字典

        if url.startswith("http://") is not True:
            self.url = "http://" + url
        else: self.url = url


    def login(self, stuId, password):
        """
        模拟登陆正方管理系统
        :parameters
        -----------
        stuId : string
            学生的学号
        password : string
            教务管理系统的密码
        """

        homePage = requests.get(self.url, headers = self.login_header)
        homePage_html, homePage_url = homePage.text, homePage.url

        homePage_soup = BeautifulSoup(homePage_html)
        homePage_hiddenTag = homePage_soup.find('input', attrs={"name": "__VIEWSTATE"})

        loginParament = {homePage_hiddenTag['name']: homePage_hiddenTag['value'],
                         "txtUserName": stuId,
                         "TextBox2": password,
                         "RadioButtonList1": u'学生'.encode('gbk'),
                         "Button1": '',
                         "lbLanguage": '',
                         "hidPdrs": '',
                         "hidsc": ''}

        self.loginPage = requests.post(homePage_url, data = loginParament, headers = self.login_header)
        self.__postfixIndex()  # 处理得到url的参数用于访问子页面
        return

    def __postfixIndex(self):
        """解析得到子页面的url参数"""
        soup = BeautifulSoup(self.loginPage.text)
        ul = soup.find('ul',attrs={"class":"nav"}).find_all('a',attrs={'target':'zhuti'})
        self.postDict = {}
        for item in ul:
            self.postDict[item.get_text()] = item['href']
        return

    def getGrade(self, stuId, password):
        """获取学生成绩"""
        def visitGradePage():
            """获得成绩页面的request对象"""
            gradePageUrl = self.loginPage.url[:-28] + self.postDict[u'成绩查询']
            connection_header = deepcopy(self.connectionParament)
            connection_header['Referer'] = self.loginPage.url  # 将Referer 置为登陆页面的url
            gradePage = requests.get(gradePageUrl, headers = connection_header)
            return gradePage

        def findHiddentag(gradePage_soup):
            hiddenTag = gradePage_soup.find('input',attrs={'type':'hidden', 'name':'__VIEWSTATE'})['value']
            return hiddenTag

        def optionYearAndSemester(gradePage_soup):
            """得到可获取的年份和月份"""
            select = gradePage_soup.find_all('select')
            yearList = [i.get_text() for i in select[0].find_all('option')[1:]]
            semesterList = [i.get_text() for i in select[1].find_all('option')[1:]]
            return yearList[:10], semesterList  # 无需查询太早之前的成绩

        def getGrade(year, semester, hiddentag, gradepageurl):
            parament = {'ddlXN':year,'ddlXQ':semester,'btn_xq':u'学期成绩'.encode('gbk'),'__VIEWSTATE':hiddentag}  # post参数
            connection_header = deepcopy(self.connectionParament)
            connection_header['Referer'] = self.loginPage.url
            grade = requests.post(gradepageurl, data = parament, headers = connection_header)
            html = grade.text

            soup = BeautifulSoup(html)
            gradeTag = soup.find('table', attrs={"class":"datelist"}).find_all('tr')[1:]
            gradeDf = pd.DataFrame(columns=['学号', '年度', '学期', '课程名称', '课程性质', '学分', '绩点', '成绩', '排名'])
            for item in gradeTag:
                tds = item.find_all('td')
                course = [[i.get_text()] for i in tds]
                course = np.array([[stuId], course[0], course[1], course[3], course[4], course[6], course[7], course[8], course[15] ]).T
                course = pd.DataFrame(course, columns=['学号', '年度', '学期', '课程名称', '课程性质', '学分', '绩点', '成绩', '排名'])
                gradeDf = gradeDf.append(course, ignore_index=True)
            gradeDf.name = year[:4] + 'to' + year[-4:] + 'Semester' + semester  # 将df命名为firstyear + to + lastyear + Semester + semester
            return gradeDf


        # body
        self.login(stuId, password)

        gradePage = visitGradePage()
        gradePage_soup = BeautifulSoup(gradePage.text)
        hiddenTag = findHiddentag(gradePage_soup)
        # year, semester = optionYearAndSemester(gradePage_soup)
        return getGrade('2014-2015', '2', hiddenTag, gradePage.url)
        # print year
        # print semester

    def getTable(self, stuId, password):
        """获取学生课表"""

        def visitPersonalPage():
            """访问学生个人课表页面"""
            personalPageUrl = self.loginPage.url[:-28] + self.postDict[u'学生个人课表']
            connection_header = deepcopy(self.connectionParament)
            connection_header['Referer'] = self.loginPage.url  # 将Referer 置为登陆页面的url
            tablePage = requests.get(personalPageUrl, headers=connection_header)
            return tablePage

        def visitRecommendPage():
            """访问专业推荐课表"""
            recommendPageUrl = self.loginPage.url[:-28] + self.postDict[u'专业推荐课表查询']
            connection_header = deepcopy(self.connectionParament)
            connection_header['Referer'] = self.loginPage.url  # 将Referer 置为登陆页面的url
            tablePage = requests.get(recommendPageUrl, headers=connection_header)
            return tablePage

        def analyzeTable(html):
            """从html解析出课表以DataFrame返回"""

            def sift(tag):
                return '<br/>' in str(tag) and tag.has_attr('align')

            tableSoup = BeautifulSoup(html)
            bigTable = tableSoup.find('table', attrs={"id": "Table1"})
            for item in bigTable.find_all(sift):
                while 'br' in str(item):
                    item.br.replace_with('\t')
                print item.get_text()


        self.login(stuId, password)
        page = visitPersonalPage()
        html = page.text
        analyzeTable(html)

class DFOperation:
    def __init__(self):
        pass

    @staticmethod
    def writeDB(df):
        conn = MySQLdb.connect(host='localhost', user='root', passwd='', charset='utf8', db='crawlTest')
        df.to_sql(df.name, conn, flavor='mysql', if_exists='append', index=False)

if __name__ == '__main__':
    test = Spider("110.65.10.233")
    # df = test.getGrade('201430552330', '3.1415926')
    # DFOperation.writeDB(df)
    test.getTable('201430552330', '3.1415926')
