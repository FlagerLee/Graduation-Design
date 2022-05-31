import os
import csv
import json
from re import sub
from utils import dicts_path, csv_path
from engine import Engine

engine = Engine()


entity_dict = {}
for subject in csv_path.keys():
    entity_list = {}
    csv_file = open(csv_path[subject], 'r', encoding='utf-8-sig')
    csv_iter = csv.reader(csv_file)
    first_row = True
    label_col = -1
    uri_col = -1
    for row in csv_iter:
        if first_row:
            for i in range(len(row)):
                if row[i] == 'label':
                    label_col = i
                elif row[i] == 'uri':
                    uri_col = i
            first_row = False
        else:
            entity_list[row[label_col]] = row[uri_col]
    entity_dict[subject] = entity_list
    csv_file.close()


def csv2dict(csv_path: str, dict_path: str) -> None:
    f_csv = open(csv_path, 'r')
    f_dict = open(dict_path, 'w')
    csv_iter = csv.reader(f_csv)
    first_row = True
    label_col = -1
    for row in csv_iter:
        if first_row:
            for i in range(len(row)):
                if row[i] == 'label':
                    label_col = i
                    break
            first_row = False
            continue
        else:
            f_dict.write('%s 1\n' % row[label_col].strip('\"'))
    f_csv.close()
    f_dict.close()


def gen_dict(prefix):
    csv_prefix = 'processed_3.0'
    for name in os.listdir(csv_prefix):
        if name == '.DS_Store':
            continue
        csv2dict('%s/%s' % (csv_prefix, name), '%s/%s.txt' % (prefix, name.split('_')[0]))


def process(content, subject):
    import jieba
    jieba.load_userdict(dicts_path[subject])
    words = jieba.lcut(content)
    del jieba
    cursor = 0
    label_map = {}
    for word in words:
        hits = engine.fuzzSearch('label', word, subject, 1)['hits']['hits']
        if len(hits) > 0 and hits[0]['_score'] > 12.0:
            target = hits[0]['_source']['label']
            if target in entity_dict[subject].keys():
                if target in label_map.keys():
                    label_map[target]['where'].append([cursor, cursor + len(word)])
                else:
                    label_map[target] = {
                        'uri': entity_dict[subject][target],
                        'where': [[cursor, cursor + len(word)]]
                    }
        cursor += len(word)
    data = []
    for label in label_map.keys():
        data.append({
            'label': label,
            'uri': label_map[label]['uri'],
            'where': label_map[label]['where']
        })
    if data == []:
        return None
    return data

def process_simple(content, subject):
    import jieba
    jieba.load_userdict(dicts_path[subject])
    words = jieba.lcut(content)
    del jieba
    cursor = 0
    label_map = {}
    for word in words:
        if word in entity_dict[subject].keys():
            target = word
            if target in entity_dict[subject].keys():
                if target in label_map.keys():
                    label_map[target]['where'].append([cursor, cursor + len(word)])
                else:
                    label_map[target] = {
                        'uri': entity_dict[subject][target],
                        'where': [[cursor, cursor + len(word)]]
                    }
        cursor += len(word)
    data = []
    for label in label_map.keys():
        data.append({
            'label': label,
            'uri': label_map[label]['uri'],
            'where': label_map[label]['where']
        })
    if data == []:
        return None
    return data


def process_json(json_path):
    json_file = open(json_path, 'r')
    content = json.load(json_file)
    json_file.close()
    subject = content['Subject']
    if subject == 'english':
        return None
    text = ''
    if content['Content'] is not None and content['Content'] != '':
        text = text + '\n' + content['Content']
    for question in content['Questions']:
        if question['Question'] is not None and question['Question'] != '':
            text = text + '\n' + question['Question']
        if question['QuestionType'] == 'choosing' and question['Choices'] is not None:
            for choice in question['Choices']:
                text = text + '\n' + choice['value']
        elif question['QuestionType'] != 'answering-essay':
            assert question['Answer'] is not None
            try:
                text = text + '\n' + question['Answer'][0]
            except Exception as e:
                print(json_path)
                print(e)
                print(question)

    return process_simple(text, subject)


if __name__ == '__main__':
    # gen_dict('dicts')
    # print(process_json('/Users/flagerlee/GaoKao_generate/json/2019GaoKao/2019_39/39_10.json'))

    json_root = '/Users/flagerlee/GaoKao_generate/json'
    path_prefix = 'temp4'
    if not os.path.exists(path_prefix):
        os.mkdir(path_prefix)
    for year_name in os.listdir(json_root):
        if year_name == '.DS_Store':
            continue
        if not os.path.exists('%s/%s' % (path_prefix, year_name)):
            os.mkdir('%s/%s' % (path_prefix, year_name))
        for exam_id in os.listdir('%s/%s' % (json_root, year_name)):
            if exam_id == '.DS_Store':
                continue
            if not os.path.exists('%s/%s/%s' % (path_prefix, year_name, exam_id)):
                os.mkdir('%s/%s/%s' % (path_prefix, year_name, exam_id))
            for problem_json in os.listdir('%s/%s/%s' % (json_root, year_name, exam_id)):
                if problem_json == '.DS_Store':
                    continue
                suffix = '%s/%s/%s' % (year_name, exam_id, problem_json)
                res = process_json('%s/%s' % (json_root, suffix))
                if res is not None:
                    with open('%s/%s/%s/%s' % (path_prefix, year_name, exam_id, problem_json.split('.')[0] + '.txt'), 'w') as f2:
                        json.dump(res, f2, ensure_ascii=False)
                else:
                    with open('%s/%s/%s/%s' % (path_prefix, year_name, exam_id, problem_json.split('.')[0] + '.txt'), 'w') as f2:
                        f2.write('[]')
                        #f2.write(str(res))
