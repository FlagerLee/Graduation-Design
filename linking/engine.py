from elasticsearch import Elasticsearch as ES
import json
from utils import json_paths


class Engine():
    def __init__(self) -> None:
        engine = ES()
        mappings = {
            'mappings': {
                'properties': {
                    'label': {
                        'type': 'text'
                    },
                    'uri': {
                        'type': 'text'
                    },
                    'alias': {
                        'type': 'text'
                    }
                }
            }
        }
        if engine.indices.exists("entity"):
            engine.indices.delete("entity")
        if engine.indices.exists("chinese") and \
            engine.indices.exists("math") and \
            engine.indices.exists("chemistry") and \
            engine.indices.exists("physics") and \
            engine.indices.exists("biology") and \
            engine.indices.exists("geo") and \
            engine.indices.exists("history") and \
            engine.indices.exists("politics"):
            return
            engine.indices.delete("chinese")
            engine.indices.delete("math")
            engine.indices.delete("chemistry")
            engine.indices.delete("physics")
            engine.indices.delete("biology")
            engine.indices.delete("geo")
            engine.indices.delete("history")
            engine.indices.delete("politics")
        res = engine.indices.create(index='chinese', body=mappings, ignore=400)
        res = engine.indices.create(index='math', body=mappings, ignore=400)
        res = engine.indices.create(index='chemistry', body=mappings, ignore=400)
        res = engine.indices.create(index='physics', body=mappings, ignore=400)
        res = engine.indices.create(index='biology', body=mappings, ignore=400)
        res = engine.indices.create(index='geo', body=mappings, ignore=400)
        res = engine.indices.create(index='history', body=mappings, ignore=400)
        res = engine.indices.create(index='politics', body=mappings, ignore=400)
        print(res)
        '''
        iid = 0
        for json_path in json_paths.values():
            print(json_path)
            with open(json_path, 'r') as f:
                contents = json.load(f)
                for content in contents:
                    iid += 1
                    engine.index(index='entity', id=iid, body=content)
            engine.indices.refresh(index='entity')
        '''
        for subject in json_paths.keys():
            print(subject)
            iid = 0
            with open(json_paths[subject], 'r') as f:
                contents = json.load(f)
                for content in contents:
                    iid += 1
                    engine.index(index=subject, id=iid, body=content)
            engine.indices.refresh(index=subject)

    def search(self, key, target, subject, size=30):
        search_body = {
            'query': {
                'match': {
                    key: target
                }
            }
        }
        engine = ES()
        result = engine.search(index=subject, body=search_body, size=size)
        return result
    
    def fuzzSearch(self, key, target, subject, size=30):
        search_body = {
            'query': {
                'match': {
                    key: {
                        'query': target,
                        'fuzziness': 'auto'
                    }
                }
            }
        }
        engine = ES()
        result = engine.search(index=subject, body=search_body, size=size)
        return result
