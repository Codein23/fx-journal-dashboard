import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import fetch_data as F

trades = [
 {'date':'2026-01-08','pl':-100,'win':False,'be':False,'dow':'Thu','pair':'EURUSD','direction':'SHORT','session':'London','entry_window':'1-2am','model':'Model 2','followed':False,'pos_tags':[],'neg_tags':['impulsive']},
 {'date':'2026-01-13','pl':400,'win':True,'be':False,'dow':'Tue','pair':'GBPUSD','direction':'LONG','session':'NY','entry_window':'8-9am','model':'Model 1','followed':True,'pos_tags':['well-managed'],'neg_tags':[]},
 {'date':'2026-01-14','pl':500,'win':True,'be':False,'dow':'Wed','pair':'EURUSD','direction':'LONG','session':'NY','entry_window':'8-9am','model':'Model 1','followed':True,'pos_tags':['perfect-entry'],'neg_tags':[]},
 {'date':'2026-01-15','pl':500,'win':True,'be':False,'dow':'Thu','pair':'GBPUSD','direction':'LONG','session':'London','entry_window':'2-3am','model':'Model 1','followed':True,'pos_tags':['well-managed'],'neg_tags':['early-exit']},
 {'date':'2026-01-16','pl':600,'win':True,'be':False,'dow':'Fri','pair':'EURUSD','direction':'LONG','session':'NY','entry_window':'8-9am','model':'Model 2','followed':True,'pos_tags':['perfect-entry'],'neg_tags':[]},
 {'date':'2026-01-19','pl':-100,'win':False,'be':False,'dow':'Mon','pair':'GBPUSD','direction':'SHORT','session':'London','entry_window':'1-2am','model':'Model 2','followed':False,'pos_tags':[],'neg_tags':['revenge-trading']},
]
out = os.path.join(os.path.dirname(__file__), '..', 'data.demo.json')
json.dump(F.compute(trades), open(out, 'w'), indent=2)
print('demo written', out)
