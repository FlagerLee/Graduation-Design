from abc import ABCMeta, abstractmethod
import json
import re


class BaseParser:
    __metaclass__ = ABCMeta

    # 文字中的水印，需要去除
    water_mark = [
        'www.ks5u.com',
        'w.w.w.k.s.5.u.c.o.m',
        'www.k@s@5@u.com',
        'ks5u',
        '高考资源网',
        '高#考#资#源#网',
        '中学历史教学园地'
    ]
    # 代表分析开始的文本，认定其后都是分析的内容
    # 若列表中文本A包含文本B，则A需要放在B前以免漏判
    analysis_text = [
        '【1题详解】',
        '【2题详解】',
        '【3题详解】',
        '【4题详解】',
        '【5题详解】',
        '【6题详解】',
        '【7题详解】',
        '【8题详解】',
        '【9题详解】',
        '【10题详解】',
        '【11题详解】',
        '【12题详解】',
        '【13题详解】',
        '【14题详解】',
        '【15题详解】',
        '【16题详解】',
        '【17题详解】',
        '【18题详解】',
        '【19题详解】',
        '【20题详解】',
        '【分析】',
        '【详解】',
        '详解',
        '【解析】',
        '[解析]',
        '解析',
        '【解答】',
        '【简评】',
        '【试题分析】',
        '试题分析',
        '【试题解析】',
        '试题解析',
        '解析试题',
        '【解题思路】',
        '整体分析',
    ]
    # 其它无用的标签，可以直接去除之后的文字
    useless_text = [
        '【参考译文】',
        '参考译文',
        '【诗歌翻译】',
        '诗歌翻译',
        '【赏析】',
        '赏析',
        '【诗歌简赏】',
        '诗歌简赏',
        '【背景解读】',
        '背景解读',
        '附：',
        '【文言文参考译文】',
        '【点评】',
        '点评',
        '参考',
        '【指示拓展】',
        '【拓展】',
        '【名师点睛】',
        '【点睛】',
        '点睛',
        '【思路点拨】',
        '思路点拨',
        '【方法总结】',
        '【诗歌鉴赏】',
        '【诗词赏析】'
    ]
    # 替换文本
    utf_num_pattern = re.compile(r'[\u2474-\u2487\uFF21-\uFF3A\u2160-\u216B]')
    replace_pattern = re.compile(r'第([(（]\d[)）]|[\u4E00-\u4E09])[题问]')
    replace_dict = {
        '一': '1',
        '二': '2',
        '三': '3',
        '四': '4',
        '五': '5',
        '六': '6',
        '七': '7',
        '八': '8',
        '九': '9',
        '\u2474': '(1)',
        '\u2475': '(2)',
        '\u2476': '(3)',
        '\u2477': '(4)',
        '\u2478': '(5)',
        '\u2479': '(6)',
        '\u247A': '(7)',
        '\u247B': '(8)',
        '\u247C': '(9)',
        '\u247D': '(10)',
        '\u247E': '(11)',
        '\u247F': '(12)',
        '\u2480': '(13)',
        '\u2481': '(14)',
        '\u2482': '(15)',
        '\u2483': '(16)',
        '\u2484': '(17)',
        '\u2485': '(18)',
        '\u2486': '(19)',
        '\u2487': '(20)',
        '\u2160': '1',
        '\u2161': '2',
        '\u2162': '3',
        '\u2163': '4',
        '\u2164': '5',
        '\u2165': '6',
        '\u2166': '7',
        '\u2167': '8',
        '\u2168': '9',
        '\u2169': '10',
        '\u216A': '11',
        '\u216B': '12',
        '\uFF21': 'A',
        '\uFF22': 'B',
        '\uFF23': 'C',
        '\uFF24': 'D',
        '\uFF25': 'E',
        '\uFF26': 'F',
        '\uFF27': 'G',
        '\uFF28': 'H',
        '\uFF29': 'I',
        '\uFF2A': 'J',
        '\uFF2B': 'K',
        '\uFF2C': 'L',
        '\uFF2D': 'M',
        '\uFF2E': 'N',
        '\uFF2F': 'O',
        '\uFF30': 'P',
        '\uFF31': 'Q',
        '\uFF32': 'R',
        '\uFF33': 'S',
        '\uFF34': 'T',
        '\uFF35': 'U',
        '\uFF36': 'V',
        '\uFF37': 'W',
        '\uFF38': 'X',
        '\uFF39': 'Y',
        '\uFF3A': 'Z'
    }
    # 科目名称替换
    subject_name_dict = {
        '语文': 'chinese',
        'chinese': 'chinese',
        '数学': 'math',
        'math': 'math',
        '英语': 'english',
        'english': 'english',
        '物理': 'physics',
        'physics': 'physics',
        '化学': 'chemistry',
        'chemistry': 'chemistry',
        '生物': 'biology',
        'biology': 'biology',
        '政治': 'politics',
        'politics': 'politics',
        '历史': 'history',
        'history': 'history',
        '地理': 'geo',
        'geo': 'geo'
    }
    # 图片查找
    img_pattern = re.compile(r'<img>(.+)</img>')
    # 下划线正则(英语需要重新定义)
    ul_pattern = re.compile(r'(_+)')

    def __init__(self, paths, args):
        assert isinstance(paths, dict)
        assert isinstance(args, dict)
        # 题目html路径
        assert paths.__contains__('problem_path')
        # 答案html路径
        assert paths.__contains__('answer_path')
        # 输出json路径
        assert paths.__contains__('output_path')
        # 图像对应表路径
        assert paths.__contains__('image_list_path')
        # 学科
        assert args.__contains__('subject')
        # 年级
        assert args.__contains__('grade')
        # 题目原链接，以url的形式给出
        assert args.__contains__('source_link')
        # 题目年份
        assert args.__contains__('year')
        # 试卷名字
        assert args.__contains__('test_name')
        # 学校
        assert args.__contains__('school')
        self.paths = paths
        self.args = args
        # 将文件名中的数字作为文件名的唯一标识符
        self.file_id = self.paths['problem_path'].split('/')[-1].split('.')[0].replace('_', '-')
        self.pid = self.file_id.split('-')[-1]

    @abstractmethod
    async def _preprocess(self, file_path, is_answer):
        """
        预处理，主要是提取文字内容和替换一些文本，方便后续解析
        :param file_path: 待处理文件路径
        :param is_answer: boolean，是否是答案文件
        :return: 纯文本形式的字符串
        """
        pass

    @abstractmethod
    def _write_json(self, args):
        """
        将解析结果写入json
        :param args: 一个dict，具体格式由各衍生解析器决定
        :return: None
        """

    def write_failed_json(self, args):
        """
        将解析错误的结果写入json
        :param args: 一个dict，其中包含problem_text、answer_text
        :return: None
        """
        assert args.__contains__('problem_text')
        assert args.__contains__('answer_text')
        assert args['problem_text'] is not None
        assert args['answer_text'] is not None
        content = {
            'ID': self.file_id,
            'Subject': self.subject_name_dict[self.args['subject']],
            'Grade': self.args['grade'],
            'School': self.args['school'],
            'SourceLink': self.args['source_link'],
            'TestName': self.args['test_name'],
            'Content': None,
            'Questions': [
                {
                    'Q_id': None,
                    'Question': None,
                    'QuestionType': 'choosing/filling-number/filling-text/answering-essay/answering-others',
                    'Choices': None,
                    'Answer': None,
                    'Analysis': ""
                }
            ]
        }
        with open(self.paths['error_path'], 'w') as f:
            json.dump(content, f, ensure_ascii=False)

    @abstractmethod
    def _collect_label(self, text):
        """
        识别text中的标号并将其提取出来
        :param text: 待识别的文本
        :return: 一个标号列表。列表中的每个元素是一个tuple，第0项是标号数字，第1项是标号span
        """
        pass

    @abstractmethod
    async def parse(self):
        """
        解析接口
        :return: bool，指示成功与否
        """
        pass

    @abstractmethod
    def _manage_exception(self, e):
        """
        异常处理
        :param e: 异常Exception
        :return: None
        """
        print(e)

    def _write_fail_reason(self, reason):
        """
        args参数令'write_fail_reason' = True时调用
        将解析失败的文件及其失败原因写进文件保存
        文件路径在paths参数'fail_file_path'中指定，默认为'./'
        :param reason: 原因字符串
        :return: None
        """
        if not self.args.__contains__('write_fail_reason'):
            return
        if not self.args['write_fail_reason']:
            return
        if not self.paths.__contains__('fail_reason_path'):
            print("No fail-reason file path provided")
            assert False
        with open(self.paths['fail_reason_path'], 'a') as f:
            f.write(self.paths['problem_path'] + ':\n' + reason + '\n\n')
