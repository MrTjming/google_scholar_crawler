import re
from unittest import result

import databaseUtil
from databaseUtil import QuoteInfo



def parse_gb7714(reference):
    # 定义正则表达式匹配 GB/T 7714 各部分信息
    pattern = re.compile(r"""
        ^(?P<authors>[\u4e00-\u9fa5,\. ]+)  # 匹配作者，中文字符，逗号分隔
        \.\s+                               # 匹配作者与文献名之间的符号
        (?P<title>.+?)                      # 匹配文献标题
        \.\s+                               # 匹配文献名后的符号
        (?P<pub_info>.*)$                   # 匹配出版信息 (可能是期刊或出版社等)
    """, re.VERBOSE)

    # 尝试匹配参考文献
    match = pattern.match(reference)

    if match:
        result = match.groupdict()

        # 解析出版信息，区分期刊还是书籍
        pub_info = result['pub_info']
        journal_pattern = re.compile(r'(?P<journal>.+),\s+(?P<year>\d{4}),\s+(?P<volume>\d+)\((?P<issue>\d+)\):\s+(?P<pages>\d+-\d+)')
        book_pattern = re.compile(r'(?P<location>.+):\s+(?P<publisher>.+),\s+(?P<year>\d{4}):\s+(?P<pages>\d+-\d+)')

        journal_match = journal_pattern.match(pub_info)
        book_match = book_pattern.match(pub_info)

        if journal_match:
            journal_info = journal_match.groupdict()
            return {
                'title': result['title'],
                'journal_name': journal_info['journal'],
                'year': journal_info['year']
            }
        elif book_match:
            # 如果是书籍，返回年份，且 journal_name 设为 None
            book_info = book_match.groupdict()
            return {
                'title': result['title'],
                'journal_name': None,  # 对于书籍，没有期刊名称
                'year': book_info['year']
            }
    return None



def parse_journal():
    quotes = QuoteInfo.select().where((QuoteInfo.journal == '') )
    for quote in quotes:
        res = parse_gb7714(quote.citationGBT)
        if res:
            quote.journal = result['journal_name']
            quote.year_month = result['year']
            quote.save()

## 下面是根据 解析出来的期刊名 精确匹配 进行修改
# UPDATE quoteInfo20240908
# SET journal_type = (
#     SELECT indexed_by
#     FROM journalTypeConfig
#     WHERE journalTypeConfig.title = quoteInfo20240908.journal COLLATE NOCASE
# )
# WHERE EXISTS (
#     SELECT 1
#     FROM journalTypeConfig
#     WHERE journalTypeConfig.title = quoteInfo20240908.journal COLLATE NOCASE
# );


## 下面的是根据 原始的citationGBT 模糊匹配 进行修改
# UPDATE quoteInfo20240908
# SET journal_type = (
#     SELECT indexed_by
#     FROM journalTypeConfig
#     WHERE LOWER(quoteInfo20240908.citationGBT) like LOWER('%' ||journalTypeConfig.title ||'%') COLLATE NOCASE
# )
# WHERE
#     journal_type is null
#     and EXISTS (
#     SELECT 1
#     FROM journalTypeConfig
#     WHERE LOWER(quoteInfo20240908.citationGBT) like LOWER('%' ||journalTypeConfig.title ||'%') COLLATE NOCASE
# );


def test_parse_gb7714():
    str = "Han F, Mu T, Li H, et al. Deep image prior plus sparsity prior: toward single-shot full-Stokes spectropolarimetric imaging with a multiple-order retarder[J]. Advanced Photonics Nexus, 2023, 2(3): 036009-036009."
    res = parse_gb7714(str)
    print(res)


if __name__ == '__main__':
    # parse_journal()
    test_parse_gb7714()