from PrimaryParser.politics import PoliticsPrimary
from PrimaryParser.chinese import ChinesePrimary
from PrimaryParser.english import EnglishPrimary
from PrimaryParser.physics import PhysicsPrimary
from PrimaryParser.math import MathPrimary
from PrimaryParser.geo import GeoPrimary
from PrimaryParser.biology import BiologyPrimary
from PrimaryParser.history import HistoryPrimary
from PrimaryParser.chemistry import ChemistryPrimary

import asyncio


def main():
    parser = PhysicsPrimary(
        paths={
            'problem_path': '/users/flagerlee/GaoKao/source_html/2018GaoKao/2018_3/3_24.html',
            'answer_path': '/users/flagerlee/GaoKao/source_html/2018GaoKao/2018_3/3_24_Answer.html',
            'output_path': './test.json',
            'error_path': '/Users/flagerlee/generate/error/2018GaoKao/2021_3',
            'image_list_path': '/Users/flagerlee/generate/img/2018GaoKao/image_list.txt',
            'image_path': '/Users/flagerlee/generate/img/2018GaoKao/'
        },
        args={
            'subject': 'geo',
            'grade': '12',
            'source_link': '',
            'year': '',
            'test_name': '',
            'school': '',
        }
    )
    task = [asyncio.ensure_future(parser.parse())]
    result = list(asyncio.get_event_loop().run_until_complete(asyncio.wait(task))[0])[0]
    if result is None:
        print('error')
    print(result)


if __name__=='__main__':
    main()
