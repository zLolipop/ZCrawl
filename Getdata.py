# coding: utf-8
__author__ = 'zzg'
'''
Build in: 2015-10-14
这只是测试的代码
'''
import requests
import MySQLdb
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
pd.set_option('display.width', 500)

class CrawlInformation:
    def __init__(self,):
        self.login_header = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Ubuntu Chromium/44.0.2403.89 '
                           'Chrome/44.0.2403.89 '
                           'Safari/537.36'}
        self.loginPage = None

    def login(self,ID,psw,url="222.201.132.114"):
        '''模拟登录正方管理系统'''
        if url.startswith("http://") != True:
            url = 'http://' + url

        self.url = url
        # 获取第一页的源代码
        firstPage = requests.post(self.url,headers=self.login_header)
        soup = BeautifulSoup(firstPage.text)
        # 获取首页的隐藏参数
        hidden_tag = soup.find('input',attrs={"name":"__VIEWSTATE"})
        # post参数列表
        paraload = {
                    hidden_tag['name']:hidden_tag['value'],
                    "txtUserName":ID,
                    "TextBox2":psw,
                    "RadioButtonList1":u'学生'.encode('gbk'),
                    "Button1":'',
                    "lbLanguage":'',
                    "hidPdrs":'',
                    "hidsc":''}

        self.loginPage = requests.post(firstPage.url,data=paraload,headers=self.login_header)
        self.__postfixUrl() # 处理得到url的后缀用于访问子页面

    def __postfixUrl(self):
        soup = BeautifulSoup(self.loginPage.text)
        ul = soup.find('ul',attrs={"class":"nav"}).find_all('a',attrs={'target':'zhuti'})
        self.postDict = {}
        for item in ul:
            self.postDict[item.get_text()] = item['href']

    def getTable(self,ID,psw,url="222.201.132.114"):
        if self.loginPage is None:
            self.login(ID,psw,url)

        def sift(tag):
            '筛选掉text是空的tag'
            return not tag.get_text().isspace()

        def processTable(tag):
            '把课程的各项信息分离为列表'
            return BeautifulSoup(str(tag).replace('<br/>','\n')).get_text().split('\n')

        def regexProcess(course):
            course_dict = {'courseName':course[0]}
            course_day = re.findall(u'周[一二三四五六日]',course[1]) # 课程是星期几的
            course_time = re.findall(u'第(.*)节',course[1])        # 课程是第几节
            course_date = re.findall()


        tablePageUrl = self.loginPage.url[:-28] + self.postDict[u'学生个人课表']

        connection_header = {'Connection':'keep-alive','Referer':self.loginPage.url}
        table_r = requests.get(tablePageUrl,headers=connection_header)

        tablesoup = BeautifulSoup(table_r.text)
        table= filter(sift,tablesoup.find('span',attrs={'class':'formbox'}).find_all('td',attrs={'align':'Center'}))

        test = map(processTable,table)[7:]

        for i in test:
            print i[0]

            reg = u'\{第(\d*)-(\d*)周.*\}'
            r = re.compile(reg,re.S)
            # f = re.findall(reg,i[1],re.S)
            f = r.findall(i[1])
            print f


    def getGrade(self,ID,psw,url="222.201.132.114"):
        if self.loginPage is None:
            self.login(ID,psw,url)

        def visitGetGradePage():
            gradePageUrl = self.loginPage.url[:-28] + self.postDict[u'成绩查询']
            connection_header = {'Connection':'keep-alive','Referer':self.loginPage.url}
            grade_r1 = requests.get(gradePageUrl,headers=connection_header)
            return grade_r1

        def getGrade(year, semester, hidden, gradeurl):  # year:string semester:string hidden:string
            para = {'ddlXN':year,'ddlXQ':semester,'btn_xq':u'学期成绩'.encode('gbk'),'__VIEWSTATE':hidden}
            connection_header = {'Connection':'keep-alive','Referer':self.loginPage.url}
            r = requests.post(gradeurl, data=para, headers=connection_header)
            gradeSoup = BeautifulSoup(r.text).find('table',attrs={"class":"datelist"}).find_all('tr')[1:]
            test_Df = pd.DataFrame(columns=['ID', 'year', 'semester', 'name', 'property', 'credit', 'GPA', 'grade', 'college', 'rank'])
            for item in gradeSoup:
                tds = item.find_all('td')
                course = []
                for i in tds:
                    course.append([i.get_text()])
                course = [[ID], course[0], course[1], course[3], course[4], course[6], course[7], course[8], course[12], course[15] ]
                course = np.array(course).T
                # print course
                tmp_df = pd.DataFrame(course,columns=['ID','year', 'semester', 'name', 'property', 'credit', 'GPA', 'grade', 'college', 'rank'])
                test_Df = test_Df.append(tmp_df,ignore_index=True)
            return test_Df

        def writeToDB(year,semester,df):
            conn = MySQLdb.connect(host='localhost',user='root', passwd='', charset='utf8', db='crawlTest')
            df.to_sql(year[:4]+'to'+year[-4:]+'semester'+semester, conn, flavor='mysql',index=False,if_exists='append')



        grade_r1 = visitGetGradePage()
        html = grade_r1.text
        gradeSoup = BeautifulSoup(html)
        select = gradeSoup.find_all('select')
        option_year = [i.get_text() for i in select[0].find_all('option')[1:]]  # 可供选择的年度
        option_semester = [i.get_text() for i in select[1].find_all('option')[1:]]  # 可供选择的月份

        hidden = gradeSoup.find('input',attrs={'type':'hidden', 'name':'__VIEWSTATE'})['value']  # 找到隐藏的标签
        print "请选择年份："
        year_dic, semester_dic= {}, {}
        for year in option_year:
            print option_year.index(year), year
            year_dic[option_year.index(year)] = year
        print year_dic
        year = input()
        year = year_dic[year]

        print "请输入学期："
        semester = raw_input()


        # grade_df = getGrade(option_year[0], option_semester[1], hidden, grade_r1.url)
        grade_df = getGrade(year, semester, hidden, grade_r1.url)

        writeToDB(year,semester,grade_df)

if __name__ == '__main__':
    test = CrawlInformation()
    test.getGrade('201430552330', '3.1415926', '110.65.10.232')
    # test.getGrade('201430550251', 'DEMMONCEO2014.')
    # test.getGrade('201430550473', 'ljk23085420XP')