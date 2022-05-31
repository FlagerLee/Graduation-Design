import spider
import os


subject_list = [
    'chinese',
    'math',
    'english',
    'physics',
    'chemistry',
    'biology',
    'politics',
    'history',
    'geo',
]

exam_type_list = [
    '高考真题',
    '高中联考',
    '高考模拟',
    '期中试卷',
    '期末试卷',
    '月考试卷',
]

year_list = ['20' + str(i) for i in range(10, 22)]
grade_list = ['11', '12', '13']


def run_spider():
    current_subject = ''
    current_exam_type = ''
    current_year = ''
    current_grade = ''
    if os.path.exists('./statement.txt'):
        f = open('./statement.txt', 'r+')
    else:
        f = open('./statement.txt', 'w')
    try:
        try:
            error = f.readline()
        except IOError:
            error = ''
        start_dict = {}
        start_from_begin = False
        if error == '':
            # no error occurred, start from begin
            start_from_begin = True
        else:
            config = f.readline()
            if config == '':
                start_from_begin = True
            else:
                config_list = config.replace('\n', '').split(' ')
                start_dict['subject'] = config_list[0]
                start_dict['exam_type'] = config_list[1]
                start_dict['year'] = config_list[2]
                start_dict['grade'] = config_list[3]
        root_path = os.environ['HOME'] + '/exams/'
        if not os.path.exists(root_path):
            os.mkdir(root_path)
        if not os.path.exists(root_path + 'excel/'):
            os.mkdir(root_path + 'excel/')
        if not os.path.exists(root_path + 'source_html'):
            os.mkdir(root_path + 'source_html')
        started_exam_type = False
        started_subject = False
        started_year = False
        started_grade = False
        for exam_type in exam_type_list:
            if not started_exam_type:
                if not start_from_begin:
                    if exam_type != start_dict['exam_type']:
                        continue
                    else:
                        started_exam_type = True
                else:
                    started_exam_type = True
            current_exam_type = exam_type
            for subject in subject_list:
                if subject != 'biology':
                    continue
                if not started_subject:
                    if not start_from_begin:
                        if subject != start_dict['subject']:
                            continue
                        else:
                            started_subject = True
                    else:
                        started_subject = True
                current_subject = subject
                excel_path = root_path + 'excel/' + exam_type + '_' + subject + '.xlsx'
                html_path = root_path + 'source_html/' + exam_type + '_' + subject + '/'
                if not os.path.exists(html_path):
                    os.mkdir(html_path)
                for year in year_list:
                    if not started_year:
                        if not start_from_begin:
                            if year != start_dict['year']:
                                continue
                            else:
                                started_year = True
                        else:
                            started_year = True
                    current_year = year
                    for grade in grade_list:
                        if not started_grade:
                            if not start_from_begin:
                                if grade != start_dict['grade']:
                                    continue
                                else:
                                    start_grade = True
                        current_grade = grade
                        spider.run_spider(subject, year, grade, exam_type, excel_path, html_path)
        f.close()
        os.remove('./statement.txt')
    except Exception as e:
        f.write(str(e))
        f.write(current_subject + " " + current_exam_type + " " + current_year + " " + current_grade)
        f.close()


if __name__ == '__main__':
    run_spider()
