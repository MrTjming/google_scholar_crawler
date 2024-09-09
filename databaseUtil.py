from peewee import *

# 连接到 SQLite 数据库
db = SqliteDatabase('论文引用数据库.db')

# 定义模型类
class QuoteInfo(Model):
    #
    title = CharField(max_length=500)
    citationGBT = CharField(max_length=500)
    # 引用的文章名
    cited_by_title = CharField(max_length=500)
    journal= CharField(max_length=500)
    year_month= CharField(max_length=20)
    #期刊类型
    journalType = CharField(max_length=500)
    # 快照日期
    snapshotDate = CharField(max_length=500)

    class Meta:
        database = db  # 使用数据库连接
        table_name = 'quoteInfo' + '20240908'


# 论文信息
class PaperInfo(Model):
    #论文标题
    title = CharField(max_length=500)
    # 引用数量
    quoteNum = IntegerField()
    # 状态
    status = CharField(max_length=500)
    # 快照日期
    snapshotDate = CharField(max_length=500)

    class Meta:
        database = db  # 使用数据库连接
        table_name = 'paperInfo'


# 创建表
db.connect()
db.create_tables([QuoteInfo])
db.create_tables([PaperInfo])

def save_quote_info_if_absent(title, citationGBT, cited_by_title, journal, year_month):
    users = QuoteInfo.select().where((QuoteInfo.title == title) & (QuoteInfo.citationGBT == citationGBT))
    if len(users) == 0:
        QuoteInfo.create(title=title,citationGBT=citationGBT, cited_by_title=cited_by_title,journal=journal, year_month=year_month)



def save_paper_info_if_absent(title, quoteNum,status, snapshotDate):
    papers = PaperInfo.select().where((PaperInfo.title == title) &(PaperInfo.snapshotDate == snapshotDate))
    if len(papers) == 0:
        PaperInfo.create(title=title,quoteNum=quoteNum,status=status, snapshotDate=snapshotDate)

