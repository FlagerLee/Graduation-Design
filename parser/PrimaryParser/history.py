from . import base_parser
from bs4 import BeautifulSoup
from bs4.element import Tag
import traceback
import httpx
from paddleocr import PaddleOCR
import asyncio
import sys
import os
import json
import re
import logging

try:
    from PIL import Image
except ImportError:
    import Image


class HiddenPrints:
    def __init__(self, activated=True):
        # activated参数表示当前修饰类是否被**
        self.activated = activated
        self.original_stdout = None

    def open(self):
        sys.stdout.close()
        sys.stdout = self.original_stdout

    def close(self):
        self.original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __enter__(self):
        if self.activated:
            self.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.activated:
            self.open()


class HistoryPrimary(base_parser.BaseParser):
    def __init__(self, paths, args):
        super().__init__(paths, args)
        self.__analysis = None
        self.__label_pattern = [
            re.compile(r'\(\s?([1-9][0-9]?)\s?\)\.?'),
            re.compile(r'（\s?([1-9][0-9]?)\s?\)\.?'),
            re.compile(r'\(\s?([1-9][0-9]?)\s?）\.?'),
            re.compile(r'（\s?([1-9][0-9]?)\s?）\.?'),
            re.compile(r'[^0-9(（]\s?([1-9][0-9]?)\s?\)|^([1-9][0-9]?)\s?\)\s?\.?'),
            re.compile(r'[^0-9(（]\s?([1-9][0-9]?)\s?）|^([1-9][0-9]?)\s?）\s?\.?'),
            re.compile(r'[^0-9]\s?([1-9][0-9]?)\s?[.、\uFF0E]\D|^([1-9][0-9]?)\s?[.、\uFF0E]\D')
        ]
        self.img_id = 0
        self.__choice_pattern = re.compile(r'([A-H])[.、．]')
        logging.getLogger('root').setLevel(logging.ERROR)

    async def _download_and_convert_img(self, url, img_name):
        if os.path.exists("%s%s" % (self.paths['image_path'], img_name)):
            return
        client = httpx.AsyncClient()
        try:
            response = await client.get(url, timeout=20)
        except:
            return None
        if response.status_code != 200:
            return None
        img_path = '%s%s' % (self.paths['image_path'], img_name)
        with open(img_path, 'wb') as f:
            f.write(response.content)
        # TODO: add ocr

        # 若存在rgba通道的图片，将透明背景变得不透明
        def remove_transparency(img_pil, bg_color=(255, 255, 255)):
            if img_pil.mode in ('RGBA', 'LA'):
                alpha = img_pil.split()[-1]
                bg = Image.new('RGBA', img_pil.size, bg_color + (255,))
                bg.paste(img_pil, mask=alpha)
                return bg.convert('RGB')
            elif img_pil.mode == 'P':
                return img_pil.convert('RGB')
            else:
                return img_pil

        img = Image.open(img_path)
        img = remove_transparency(img)
        img.save(img_path)
        height, width = img.size
        img.close()
        # 图片过小，不存在有效信息，直接排除
        if height <= 10 and width <= 10:
            os.remove(img_path)
            return None
        '''
        elif height <= 100 and width <= 100:
            # 将图片横向拼接并识别文字
            new_img = Image.new(img.mode, (10 * (img.size[0] + 25), img.size[1] + 100))
            for i in range(10):
                new_img.paste(img, (12 + i * (img.size[0] + 25), 50))
            img.close()
            new_img.save(img_path)
            new_img.close()
            hide_print = HiddenPrints()
            hide_print.close()
            ocr = PaddleOCR(use_angle_cls=True, lang='ch')
            result = ocr.ocr(img_path, cls=True)
            hide_print.open()
            result_str = ''
            for line in result:
                if float(line[1][1]) > 0.8:
                    result_str += line[1][0]
            with open(img_path, 'wb') as f:
                f.write(response.content)
            if len(result_str) % 10 != 0:
                return False
            return result_str[:len(result_str) // 10]
        else:
            img.close()
            hide_print = HiddenPrints()
            hide_print.close()
            ocr = PaddleOCR(use_angle_cls=True, lang='ch')
            result = ocr.ocr(img_path, cls=True)
            hide_print.open()
            result_str = ''
            for line in result:
                if float(line[1][1]) > 0.8:
                    result_str += line[1][0]
            return result_str
        '''
        return True

    async def _preprocess(self, file_path, is_answer, remove_analysis=False):
        try:
            f = open(file_path, 'r')
            soup = BeautifulSoup(f.read(), 'lxml')
            f.close()

            # 找到class为prefix的类，在其内容的末尾添加'.'
            nodes = soup.select('.prefix')
            for node in nodes:
                text = node.get_text().strip(' ')
                if not text.endswith('.'):
                    node.append('. ')

            # 找到class为ext_text-align_left的类，将其开头的数字+'.'去除
            nodes = soup.select('.ext_text-align_left')
            for node in nodes:
                if node.children is not None:
                    for child in node.children:
                        text = child.get_text()
                        result = re.match(r'([1-9][0-9]?[.．])', text)
                        if result is not None and child.string is not None:
                            child.string = text[result.span()[1]:]
                else:
                    text = node.get_text()
                    result = re.match(r'([1-9][0-9]?[.．])', text)
                    if result is not None and child.string is not None:
                        node.string = text[result.span()[1]:]

            # 为空span添加4个'\xa0'
            nodes = soup.find_all('span', text=lambda value: value is None or value == '\n')
            for node in nodes:
                if node.string is None:
                    node.append('\xa0\xa0\xa0\xa0')
                else:
                    node.string.replace_with('\xa0\xa0\xa0\xa0')

            # 将'text-decoration:underline'后的'\xa0'替换成下划线
            nodes = soup.find_all('span', style=lambda value: value and 'text-decoration:underline' in value)
            for node in nodes:
                content = node.find(text=re.compile(r'(\xa0+)'))
                if content is not None:
                    content.replace_with(content.get_text().replace('\xa0', '_'))

            # 将<u>标签下的'\xa0'替换成下划线（为什么还会有人在用h5淘汰了的东西？？？）
            nodes = soup.find_all('u')
            for node in nodes:
                content = node.find(text=re.compile(r'(\xa0+)'))
                if content is not None:
                    content.replaceWith(content.get_text().replace('\xa0', '_'))

            # 为每个<p>标签的末尾添加'\n'，代替换行
            nodes = soup.find_all('p')
            for node in nodes:
                if isinstance(node, Tag):
                    node.append(r'\n')

            # 去除所有<br/>标签，并在其原位置留下换行符
            nodes = soup.find_all('br')
            for node in nodes:
                node.insert_after(r'\n')
                node.decompose()

            # 将\u2474-\u2487区间的所有字符替换为对应的数字（这些字符是括号数字）
            def repl_utf_num(matched):
                return self.replace_dict[matched.group(0)]
            nodes = soup.find_all(text=self.utf_num_pattern)
            for node in nodes:
                new_content = self.utf_num_pattern.sub(repl_utf_num, node.get_text())
                node.replace_with(new_content)

            # 将图像url转换成可加入文本的字符串，并使其带上唯一标签，方便后续替换
            nodes = soup.find_all('img')
            if len(nodes) != 0:
                img_list_file = open(self.paths['image_list_path'], 'a')
                for node in nodes:
                    url = node.get('src')
                    if url is None:
                        url = node.get('data-lazysrc')
                    # 将图像url和id写进文件。
                    # TODO: 开另一个进程，解析到图片之后另一个进程同时下载并尝试识别这张图片

                    # 在当前位置使用异步下载图片
                    img_name = '%s-%s.%s' % (self.file_id, str(self.img_id), url.split('.')[-1])
                    result = await self._download_and_convert_img(url, img_name)

                    if result is not None and result is not False:
                        img_list_file.write(img_name + ': ' + url + '\n')
                        node.insert_after(r'<img>' + self.file_id + '-' + str(self.img_id) + r'</img>')
                    node.decompose()
                    self.img_id += 1
                img_list_file.close()

            # 将table表格转换成文本形式储存在题目字符串中，并删除原table标签
            nodes = soup.find_all('table')
            for node in nodes:
                table_str = node.prettify()
                table_str = table_str.replace('\n', '')
                table_str = table_str.replace(' ', '')
                node.insert_after('<table>' + table_str + '</table>')
                node.decompose()

            # html带标签部分处理完成，转换成字符串继续处理
            raw_text = soup.get_text(strip=True)

            # 去除文字水印
            for mark in self.water_mark:
                raw_text = raw_text.replace(mark, '')

            # 将'第x问'形式的字符串替换为'(x)'形式
            '''
            def repl_question_id(matched):
                span = matched.span()
                if span[1] - span[0] == 3:
                    return '(' + self.replace_dict[matched.group(1)] + ')'
                else:
                    return '(' + self.replace_dict[matched.group(1)[1]] + ')'
            raw_text = self.replace_pattern.sub(repl_question_id, raw_text)
            '''

            # 格式化下划线：将所有的下划线替换成8个
            def format_ul(matched):
                return '________'
            raw_text = self.ul_pattern.sub(format_ul, raw_text)

            # 去除"【答案解析】 【试题ID=xxx】收起 ︽"部分内容（针对答案文件）
            if is_answer:
                sp = raw_text.split('︽')
                if len(sp) > 1:
                    raw_text = sp[1]

            if remove_analysis:
                # 去除不需要的内容（针对答案文件）
                if is_answer:
                    for rubbish in self.useless_text:
                        raw_text = raw_text.split(rubbish)[0]

                # 将解析和答案分开（针对答案文件）
                if is_answer:
                    for analysis in self.analysis_text:
                        texts = raw_text.split(analysis)
                        if len(texts) > 1:
                            raw_text = texts[0]
                            self.__analysis = texts[1]
                            break

            return raw_text
        except Exception as e:
            self._manage_exception(e)
            raise Exception('Error occurred in preprocess')

    def _get_question_type(self, text):
        """
        根据题面信息判断题目类型（选择、填空和问答）
        :param text: 题目内容
        :return: 字符串："choosing"、"filling"、"answering"中的一个
        """
        try:
            choices = self.__choice_pattern.findall(text)
            if len(choices) != 0 and len(choices) < 8:
                choice_dict = {
                    0: 'A',
                    1: 'B',
                    2: 'C',
                    3: 'D',
                    4: 'E',
                    5: 'F',
                    6: 'G',
                    7: 'H'
                }
                is_choice = True
                for i in range(len(choices)):
                    if choices[i] != choice_dict[i]:
                        is_choice = False
                        break
                if is_choice:
                    return 'choosing'
            ul = self.ul_pattern.findall(text)
            if len(ul) != 0:
                return 'filling-text'
            return 'answering-others'
        except Exception as e:
            self._manage_exception(e)
            raise Exception('Error occurred in get question type')

    def _write_json(self, args):
        try:
            stem = args['stem']
            questions = args['questions']
            answers = args['answers']
            problem_ll = args['problem_ll']

            assert len(questions) == len(answers)
            nl = len(questions)  # num labels
            content = {}

            json_path = self.paths['output_path']
            assert json_path is not None

            if stem is None:
                assert len(questions) == 1

                content = {
                    'ID': self.file_id,
                    'Subject': self.subject_name_dict[self.args['subject']],
                    'Grade': self.args['grade'],
                    'School': self.args['school'],
                    'SourceLink': self.args['source_link'],
                    'TestName': self.args['test_name'],
                    'Content': "",
                    'Questions': [
                        {
                            'Q_id': self.pid,
                            'Question': questions[0].strip(r'\n').strip('\n').strip(' '),
                            'QuestionType': self._get_question_type(questions[0]),
                            'Choices': None,
                            'Answer': [answers[0].strip(r'\n').strip('\n').strip(' ')],
                            'Analysis': "",
                            'Keypoint': []
                        }
                    ]
                }
                if content['Questions'][0]['QuestionType'] == 'choosing':
                    choice_iter = self.__choice_pattern.finditer(questions[0])
                    num_choice = 0
                    choice_span = []
                    choice_list = []
                    for it in choice_iter:
                        num_choice += 1
                        choice_span.append(it.span())
                        choice_list.append(it.group(1))
                    choice_dict = {
                        0: 'A',
                        1: 'B',
                        2: 'C',
                        3: 'D',
                        4: 'E',
                        5: 'F',
                        6: 'G',
                        7: 'H'
                    }
                    for j in range(len(choice_list)):
                        if choice_list[j] != choice_dict[j]:
                            is_choice = False
                            break
                    content['Questions'][0]['Question'] = questions[0][:choice_span[0][0]].strip(r'\n').strip('\n').strip(' ')
                    choice_list = []
                    for j in range(num_choice):
                        if j == num_choice - 1:
                            choice_list.append({'label': choice_dict[j], 'value': questions[0][choice_span[j][0]:].strip(r'\n').strip('\n').strip(' ')})
                        else:
                            choice_list.append({'label': choice_dict[j], 'value': questions[0][choice_span[j][0]:choice_span[j + 1][0]].strip(r'\n').strip('\n').strip(' ')})
                    content['Questions'][0]['Choices'] = choice_list
                    try:
                        choice_answer = re.search(r'([A-H]+)', answers[0]).group(0)
                        # 判定是否从大到小，同时限定最多选择4个
                        if len(choice_answer) > 4:
                            # 不是选择题
                            content['Questions'][0]['Choices'] = None
                            content['Questions'][0]['Answer'] = [answers[0].strip(r'\n').strip('\n').strip(' ')]
                        else:
                            is_choice = True
                            for i in range(len(choice_answer) - 1):
                                if choice_answer[i + 1] <= choice_answer[i]:
                                    is_choice = False
                                    break
                            if is_choice:
                                content['Questions'][0]['Answer'] = [choice_answer.strip(r'\n').strip('\n').strip(' ')]
                            else:
                                content['Questions'][0]['Choices'] = None
                                content['Questions'][0]['Answer'] = [answers[0].strip(r'\n').strip('\n').strip(' ')]
                    except AttributeError:
                        # 找不到答案选项，考虑答案是图片的情况
                        content['Questions'][0]['Choices'] = None
                        content['Questions'][0]['Answer'] = [answers[0].strip(r'\n').strip('\n').strip(' ')]
            else:
                content['ID'] = self.file_id
                content['Subject'] = self.subject_name_dict[self.args['subject']]
                content['Grade'] = self.args['grade']
                content['School'] = self.args['school']
                content['SourceLink'] = self.args['source_link']
                content['TestName'] = self.args['test_name']
                content['Content'] = stem.strip(r'\n').strip('\n').strip(' ')

                question_list = []
                for i in range(nl):
                    question_dict = {
                        'Q_id': problem_ll[i][0],
                        'Question': None,
                        'QuestionType': self._get_question_type(questions[i]),
                        'Choices': None,
                        'Answer': [answers[i]],
                        'Analysis': "",
                        'Keypoint': []
                    }
                    choice_iter = self.__choice_pattern.finditer(questions[i])
                    num_choice = 0
                    choice_span = []
                    choice_list = []
                    for it in choice_iter:
                        num_choice += 1
                        choice_span.append(it.span())
                        choice_list.append(it.group(1))
                    if num_choice == 0 or num_choice > 7:
                        # 不是选择题
                        question_dict['Question'] = questions[i].strip(r'\n').strip('\n').strip(' ')
                    else:
                        choice_dict = {
                            0: 'A',
                            1: 'B',
                            2: 'C',
                            3: 'D',
                            4: 'E',
                            5: 'F',
                            6: 'G',
                            7: 'H'
                        }
                        is_choice = True
                        for j in range(len(choice_list)):
                            if choice_list[j] != choice_dict[j]:
                                is_choice = False
                                break
                        if is_choice:
                            question_dict['Question'] = questions[i][:choice_span[0][0]].strip(r'\n').strip('\n').strip(' ')
                            choice_list = []
                            for j in range(num_choice):
                                if j == num_choice - 1:
                                    choice_list.append({'label': choice_dict[j], 'value': questions[i][choice_span[j][0]:].strip(r'\n').strip('\n').strip(' ')})
                                else:
                                    choice_list.append({'label': choice_dict[j], 'value': questions[i][choice_span[j][0]:choice_span[j+1][0]].strip(r'\n').strip('\n').strip(' ')})
                            question_dict['Choices'] = choice_list
                            try:
                                question_dict['Answer'] = [re.search(r'([A-H])', answers[i]).group(0)]
                            except AttributeError:
                                # 找不到答案选项，考虑答案是图片的情况
                                question_dict['Choices'] = None
                                question_dict['Answer'] = [answers[i].strip(r'\n').strip('\n').strip(' ')]
                        else:
                            question_dict['Question'] = questions[i].strip(r'\n').strip('\n').strip(' ')

                    question_list.append(question_dict)
                content['Questions'] = question_list
            with open(json_path, 'w') as f:
                json.dump(content, f, ensure_ascii=False)
        except Exception as e:
            self._manage_exception(e)
            raise Exception('Error occurred in write_json')

    def _collect_label(self, text):
        try:
            label_list = []
            for pattern in self.__label_pattern:
                match_it = pattern.finditer(text)
                for match in match_it:
                    group = match.groups()
                    if group is None:
                        continue
                    span = match.span()
                    duplicated_match = False
                    for label in label_list:
                        # 检测不同匹配规则匹配到同一个label
                        if label[1][0] <= span[0] < label[1][1] or \
                                label[1][0] <= span[1] < label[1][1] or \
                                (label[1][0] >= span[0] and label[1][1] <= span[1]) or \
                                (span[0] >= label[1][0] and span[1] <= label[1][1]):
                            duplicated_match = True
                            break
                    if duplicated_match:
                        continue
                    if len(group) == 1:
                        label_list.append((group[0], span))
                    else:
                        # pattern的最后三个匹配规则有两个小括号，所以匹配到时会有两个group，其中一个为空。将非空的group加入list
                        if group[0] is None:
                            label_list.append((group[1], (span[0], span[1] - 1)))
                        else:
                            label_list.append((group[0], (span[0] + 1, span[1] - 1)))
            label_list.sort(key=lambda obj: obj[1][0])
            return label_list
        except Exception as e:
            self._manage_exception(e)
            raise Exception('Error occurred in collect label')

    def _collect_question(self, text, problem_ll):
        """
        提取问题文本中的问题和题干
        :param text: 问题文本
        :param problem_ll: problem label list
        :return: 返回两个值。第一个值是题干字符串，第二个值是问题列表
        """
        try:
            problem = []
            npl = len(problem_ll)
            if npl == 0:
                problem.append(text)
                stem = None
                return stem, problem
            # 在第一个题号之前的所有文本都是题干
            stem = text[:problem_ll[0][1][0]]
            for i in range(npl):
                if i == npl - 1:
                    # 如果是最后一个标号，则后面所有文本都是题目
                    problem.append(text[problem_ll[i][1][1]:])
                else:
                    # 将两个标号之间的文本提取出来，作为题目
                    problem.append(text[problem_ll[i][1][1]:problem_ll[i+1][1][0]])
            assert len(problem) == npl
            return stem, problem
        except Exception as e:
            self._manage_exception(e)
            raise Exception('Error occurred in collect question')

    def _collect_answer(self, text, answer_ll):
        """
        提取答案文本中的答案
        :param text: 答案文本
        :param answer_ll: answer label list
        :return: 答案列表
        """
        try:
            answer = []
            nal = len(answer_ll)
            if nal == 0:
                answer.append(text)
                return answer
            for i in range(nal):
                if i == nal - 1:
                    # 如果是最后一个标号，则后面所有文本都是答案
                    answer_text = text[answer_ll[i][1][1]:]
                    # 去除不需要的标签
                    for rubbish in self.useless_text:
                        answer_text = answer_text.split(rubbish)[0]
                    # 分离答案和解析
                    for analysis in self.analysis_text:
                        texts = answer_text.split(analysis)
                        if len(texts) > 1:
                            answer_text = texts[0]
                            self.__analysis = texts[1]
                            break
                    answer.append(answer_text)
                else:
                    # 将两个标号之间的文本提取出来，作为答案
                    answer_text = text[answer_ll[i][1][1]:answer_ll[i+1][1][0]]
                    # 去除不需要的标签
                    for rubbish in self.useless_text:
                        answer_text = answer_text.split(rubbish)[0]
                    # 分离答案和解析
                    for analysis in self.analysis_text:
                        texts = answer_text.split(analysis)
                        if len(texts) > 1:
                            answer_text = texts[0]
                            self.__analysis = texts[1]
                            break
                    answer.append(answer_text)
            assert len(answer) == nal
            return answer
        except Exception as e:
            self._manage_exception(e)
            raise Exception('Error occurred in collect answer')

    def _match_ul(self, text, problem_ll, answer):
        """
        匹配题目中的下划线，返回每道题的下划线
        :param text: 待匹配的题目
        :param problem_ll: problem label list
        :param answer: 答案列表
        :return: 如果题目中的下划线能与答案正确匹配，则返回新的答案列表，否则返回None
        """
        try:
            ul_iter = self.ul_pattern.finditer(text)
            ul_span = []
            for it in ul_iter:
                ul_span.append(it.span())
            # 如果下划线数目与答案数目不一样，则不能匹配
            if len(ul_span) != len(answer):
                return None
            mapping = {}
            # npl = num problem label
            npl = len(problem_ll)
            if npl != 0:
                for i in range(npl):
                    num_ul = 0
                    if i == npl - 1:
                        for span in ul_span:
                            if span[0] >= problem_ll[i][1][1]:
                                num_ul += 1
                    else:
                        for span in ul_span:
                            if span[0] >= problem_ll[i][1][1] and span[1] < problem_ll[i + 1][1][0]:
                                num_ul += 1
                    mapping[problem_ll[i]] = num_ul
                    if num_ul == 0:
                        return None
            else:
                mapping['1'] = len(ul_span)

            # 重新组合答案
            answer_id = 0
            new_answer = []
            for num_ul in mapping.values():
                if num_ul == 0:
                    assert False
                if num_ul == 1:
                    new_answer.append(answer[answer_id])
                    answer_id += 1
                else:
                    new_ans_str = ""
                    for i in range(answer_id, answer_id + num_ul):
                        new_ans_str += answer[i]
                    new_answer.append(new_ans_str)
                    answer_id += num_ul

            return new_answer
        except Exception as e:
            self._manage_exception(e)
            raise Exception('Error occurred in match ul')

    def _fold_label(self, label_list):
        try:
            while True:
                found = False
                start, end = 0, 0
                for i in range(1, len(label_list)):
                    if label_list[i][0] == '1' and label_list[i][1][0] - label_list[i-1][1][1] < 300:
                        start = i
                        end = len(label_list)
                        for j in range(i + 1, len(label_list)):
                            if int(label_list[j][0]) != j - i + 1:
                                end = j
                                break
                        break
                if end - start > 0:
                    found = True
                    label_list = label_list[:start] + label_list[end:]

                if not found:
                    break
            return label_list
        except Exception as e:
            self._manage_exception(e)
            raise Exception('Error occurred in fold label')

    async def parse(self):
        problem_text = ''
        answer_text = ''
        try:
            enable_fail_reason = False
            fail_reason = None
            if self.args.__contains__('write_fail_reason') and self.args['write_fail_reason']:
                enable_fail_reason = True
            problem_text = await self._preprocess(self.paths['problem_path'], is_answer=False)
            answer_text = await self._preprocess(self.paths['answer_path'], is_answer=True)

            # problem label list
            problem_ll = self._collect_label(problem_text)
            # answer label list
            answer_ll = self._collect_label(answer_text)

            # 如果题号中出现了非开头的至少"1""2"连号，尝试将该连号匹配到上一个题号
            # 注意：不能在第一道题上应用
            if self.pid != 1:
                problem_ll = self._fold_label(problem_ll)
                answer_ll = self._fold_label(answer_ll)

            # 分类讨论：令npl = num problem label, nal = num answer label，讨论npl < nal, npl == nal, npl > nal
            npl = len(problem_ll)
            nal = len(answer_ll)
            stem, questions = self._collect_question(problem_text, problem_ll)
            answers = self._collect_answer(answer_text, answer_ll)

            success = True

            if npl < nal:
                # 假设出现该问题的原因是题目中出现了下划线，答案中按照下划线个数分配标号，导致题号数量不匹配
                answers = self._match_ul(problem_text, problem_ll, answers)
                if answers is None:
                    fail_reason = "检测到题目数目大于答案数目，且下划线检测未成功。\n" \
                                  "题目编号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                  "\n答案编号列表：" + str([answer_ll[i][0] for i in range(nal)])

                    # 如果没有成功，则考虑答案中是否有分条回答，取前一部分
                    end_idx = 0
                    for i in range(1, nal):
                        if int(answer_ll[i][0]) - int(answer_ll[i - 1][0]) != 1:
                            end_idx = i
                            break
                    answer_ll = answer_ll[:end_idx]
                    nal = len(answer_ll)
                    if nal == 0:
                        success = False
                    else:
                        if npl != nal:
                            success = False
                        else:
                            for i in range(npl):
                                if problem_ll[i][0] != answer_ll[i][0]:
                                    fail_reason = "检测到题目的标号数量小于答案的标号数量，" \
                                                  "但处理后的第%d个题号不匹配\n" \
                                                  "处理后的题目标号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                                  "\n答案标号列表：" + str([answer_ll[i][0] for i in range(nal)])
                                    fail_reason = fail_reason % (i + 1)
                                    success = False
                                    break
                                if i != 0:
                                    if int(answer_ll[i][0]) - int(answer_ll[i - 1][0]) != 1:
                                        fail_reason = "第%d个答案题号与%d个答案题号之间相差不为1。\n" \
                                                      "题目编号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                                      "\n答案编号列表：" + str([answer_ll[i][0] for i in range(nal)])
                                        fail_reason = fail_reason % (i + 1, i + 2)
                                        success = False
                                        break
                    answers = self._collect_answer(answer_text, answer_ll)
                if not success:
                    # 假设题目中有解析，且解析中出现了一堆无关序号
                    answer_text = await self._preprocess(self.paths['answer_path'], is_answer=True, remove_analysis=True)
                    answer_ll = self._collect_label(answer_text)
                    nal = len(answer_ll)
                    if nal == npl:
                        if nal != 0:
                            answers = self._collect_answer(answer_text, answer_ll)
                        else:
                            answers = [answer_text]
                        success = True

            elif npl == nal:
                # 判定题目和题面的题号是否匹配，如果匹配且题号等差数列1，则认定为正确，否则错误
                for i in range(npl):
                    if problem_ll[i][0] != answer_ll[i][0]:
                        fail_reason = "检测到题目数目等于答案数目，但第%d个题号不匹配。\n" \
                                      "题目编号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                      "\n答案编号列表：" + str([answer_ll[i][0] for i in range(nal)])
                        fail_reason = fail_reason % (i + 1)
                        success = False
                        break
                    if i != 0:
                        if int(problem_ll[i][0]) - int(problem_ll[i - 1][0]) != 1:
                            fail_reason = "第%d个题目题号与%d个题目题号之间相差不为1。\n" \
                                          "题目编号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                          "\n答案编号列表：" + str([answer_ll[i][0] for i in range(nal)])
                            fail_reason = fail_reason % (i + 1, i + 2)
                            success = False
                            break
                        if int(answer_ll[i][0]) - int(answer_ll[i - 1][0]) != 1:
                            fail_reason = "第%d个答案题号与%d个答案题号之间相差不为1。\n" \
                                          "题目编号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                          "\n答案编号列表：" + str([answer_ll[i][0] for i in range(nal)])
                            fail_reason = fail_reason % (i + 1, i + 2)
                            success = False
                            break
            elif npl > nal:
                # 题目的标号数量大于答案的标号数量
                # 在这里处理两种情况：某些题目（尤其是阅读题）在题目之前就出现了若干标号；答案为一张图片
                # 第一种情况处理方法为：从列表最后一位开始往前找公差为1的等差数列，将这串等差数列作为题目的标号与答案匹配
                start_idx = 0
                for i in range(npl - 2, -1, -1):
                    if int(problem_ll[i + 1][0]) - int(problem_ll[i][0]) != 1:
                        start_idx = i + 1
                        break
                problem_ll = problem_ll[start_idx:]
                npl = len(problem_ll)
                if npl == 0:
                    # 这里是否可以处理？
                    fail_reason = "检测到题目的标号数量大于答案的标号数量，但处理后出现未知原因错误。" \
                                  "若出现该错误，请联系管理员处理（我也好奇是什么情况会报这个错）"
                    success = False
                else:
                    if npl != nal:
                        fail_reason = "检测到题目的标号数量大于答案的标号数量，" \
                                      "但处理后题目的标号数量仍不等于答案的标号数量\n" \
                                      "处理后的题目标号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                      "\n答案标号列表：" + str([answer_ll[i][0] for i in range(nal)])
                        success = False
                    else:
                        for i in range(npl):
                            if problem_ll[i][0] != answer_ll[i][0]:
                                fail_reason = "检测到题目的标号数量大于答案的标号数量，" \
                                              "但处理后的第%d个题号不匹配\n" \
                                              "处理后的题目标号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                              "\n答案标号列表：" + str([answer_ll[i][0] for i in range(nal)])
                                fail_reason = fail_reason % (i + 1)
                                success = False
                                break
                            if i != 0:
                                if int(answer_ll[i][0]) - int(answer_ll[i - 1][0]) != 1:
                                    fail_reason = "第%d个答案题号与%d个答案题号之间相差不为1。\n" \
                                                  "题目编号列表：" + str([problem_ll[i][0] for i in range(npl)]) + \
                                                  "\n答案编号列表：" + str([answer_ll[i][0] for i in range(nal)])
                                    fail_reason = fail_reason % (i + 1, i + 2)
                                    success = False
                                    break
                if success:
                    stem, questions = self._collect_question(problem_text, problem_ll)
                '''
                else:
                    # 查看答案部分是否存在图片：如果存在，则将其视为一道题目
                    answer_img = self.img_pattern.search(answer_text)
                    if answer_img is not None:
                        problem_ll = [problem_ll[0]]
                        stem, questions = self._collect_question(problem_text, problem_ll)
                        answers = [answer_text]
                        success = True
                '''

            if success and len(questions) != len(answers):
                raise Exception

            if success:
                self._write_json(args={
                        'stem': stem,
                        'questions': questions,
                        'answers': answers,
                        'problem_ll': problem_ll
                    }
                )
            else:
                if enable_fail_reason:
                    assert fail_reason is not None
                    self._write_fail_reason(fail_reason)

            if success:
                return len(problem_ll)
            else:
                self.write_failed_json(args={
                    'problem_text': problem_text,
                    'answer_text': answer_text
                })
                return None
        except Exception as e:
            self._manage_exception(e)
            if 'problem_text' not in vars():
                problem_text = ''
            if 'answer_text' not in vars():
                answer_text = ''
            self.write_failed_json(args={
                'problem_text': problem_text,
                'answer_text': answer_text
            })
            return None

    def _manage_exception(self, e):
        # traceback.print_exc()
        # print(e)
        f = open(self.paths['error_path'], 'w')
        f.close()
        pass
