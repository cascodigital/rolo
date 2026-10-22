import copy, importlib.util, json, os, pathlib, sys, tempfile, time, unittest
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
import rolo_curate as r
class CurateTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.old=r.ROOT; r.ROOT=pathlib.Path(self.tmp.name); self.now=int(time.time())
  self.oldplay={'listened_at':self.now-200*r.DAY,'track_metadata':{'artist_name':'Legião Urbana','track_name':'Tempo perdido'}}
  self.newplay={'listened_at':self.now-2*r.DAY,'track_metadata':{'artist_name':'Queen','track_name':'Radio Ga Ga'}}
  (r.ROOT/'history_db.json').write_text(json.dumps({'last_update':'2026-10-20','count':2,'listens':[self.oldplay,self.newplay]}))
  self.pulse={'fetched_at':self.now,'complete_30d':True,'listens':[]}; self.state={'version':1,'feedback':[],'delivered':[]}
 def tearDown(self): r.ROOT=self.old; self.tmp.cleanup()
 def track(self,cat='nostalgia'):
  return {'videoId':'12345678901','title':'Tempo perdido','artists':['Legiao Urbana'],'category':cat}
 def plan(self,t=None): return {'count':1,'mode':'custom','reason':'explicit nostalgia request','tracks':[t or self.track()]}
 def check(self,m=None,p=None,s=None,**kw): return r.validate(m or self.plan(),p or self.pulse,s or self.state,**kw)
 def test_alias_nostalgia(self): self.assertTrue(self.check()['ok'])
 def test_current_date(self):
  t=self.track('current'); self.assertFalse(self.check(self.plan(t))['ok']); t.update(title='Radio Ga Ga',artists=['Queen']); self.assertTrue(self.check(self.plan(t))['ok'])
 def test_discovery_known(self): self.assertFalse(self.check(self.plan(self.track('discovery')))['ok'])
 def test_artist_block_and_reverse(self):
  f={'at':self.now,'artist_key':'legiao urbana','title_key':'','verdict':'dislike'}; self.state['feedback']=[f]; self.assertFalse(self.check()['ok']); self.state['feedback'].append({**f,'verdict':'like'}); self.assertTrue(self.check()['ok'])
 def test_track_skip_expires(self):
  f={'at':self.now,'artist_key':'legiao urbana','title_key':'tempo perdido','verdict':'skip'}; self.state['feedback']=[f]; self.assertFalse(self.check()['ok']); f['at']-=31*r.DAY; self.assertTrue(self.check()['ok'])
 def test_repetition(self):
  self.state['delivered']=[{'at':self.now,'playlist_id':'TEST','tracks':[self.track()]}]; self.assertFalse(self.check()['ok']); self.assertTrue(self.check(allow_repeat=True)['ok'])
 def test_duplicate(self):
  m=self.plan(); m['tracks'].append(copy.deepcopy(m['tracks'][0])); m['count']=2; self.assertFalse(self.check(m)['ok'])
 def test_readback(self):
  m=self.plan(); m['playlist_id']='TEST'; rb={'id':'TEST','trackCount':1,'tracks':[self.track()]}; self.assertTrue(self.check(m,readback=rb)['ok']); rb['tracks'][0]['videoId']='01234567890'; self.assertFalse(self.check(m,readback=rb)['ok'])
 def test_stale_incomplete_pulse(self):
  p=copy.deepcopy(self.pulse); p['complete_30d']=False; self.assertFalse(self.check(p=p)['ok']); p['complete_30d']=True;p['fetched_at']-=3601;self.assertFalse(self.check(p=p)['ok'])
 def test_quotas(self): self.assertEqual(r.quotas(15),{'nostalgia':6,'discovery':6,'current':3});self.assertEqual(sum(r.quotas(16).values()),16)
 def test_mix_wrong_ratios(self):
  m=self.plan();m['mode']='mix';self.assertFalse(self.check(m)['ok'])
 def test_feedback_cli_no_apply_and_persistence(self):
  import subprocess
  base=[sys.executable,r.__file__,'feedback','--artist','Queen','--verdict','dislike']; env={**os.environ,'ROLO_DATA_DIR':str(r.ROOT)}
  self.assertEqual(subprocess.run(base,env=env,capture_output=True).returncode,0);self.assertFalse((r.ROOT/'feedback.json').exists())
  self.assertEqual(subprocess.run(base+['--apply'],env=env,capture_output=True).returncode,0);self.assertEqual(r.state()['feedback'][0]['verdict'],'dislike')
 def test_record_cli_readback_gate_and_idempotence(self):
  import subprocess
  m=self.plan();m['playlist_id']='TEST'; rb={'id':'TEST','trackCount':1,'tracks':[self.track()]}
  for name,doc in [('plan',m),('pulse',self.pulse),('rb',rb)]: (r.ROOT/(name+'.json')).write_text(json.dumps(doc))
  base=[sys.executable,r.__file__,'record','--manifest',str(r.ROOT/'plan.json'),'--pulse-json',str(r.ROOT/'pulse.json'),'--apply']; env={**os.environ,'ROLO_DATA_DIR':str(r.ROOT)}
  self.assertNotEqual(subprocess.run(base,env=env,capture_output=True).returncode,0)
  for _ in range(2): self.assertEqual(subprocess.run(base+['--readback',str(r.ROOT/'rb.json')],env=env,capture_output=True).returncode,0)
  self.assertEqual(len(r.state()['delivered']),1)
 def test_secondary_artist_rejected(self):
  t=self.track();t['artists'].append('Queen');self.state['feedback']=[{'at':self.now,'artist_key':'queen','title_key':'','verdict':'dislike'}];self.assertFalse(self.check(self.plan(t))['ok'])
 def test_delivery_requires_current_job_record(self):
  import subprocess
  env={**os.environ,'ROLO_DATA_DIR':str(r.ROOT)};base=[sys.executable,r.__file__,'delivery','--playlist-id','TEST','--since',str(self.now)]
  self.assertNotEqual(subprocess.run(base,env=env,capture_output=True).returncode,0)
  data={'version':1,'feedback':[],'delivered':[{'at':self.now-20,'playlist_id':'TEST','tracks':[self.track()],'counts':{'nostalgia':1}}]};(r.ROOT/'feedback.json').write_text(json.dumps(data))
  self.assertNotEqual(subprocess.run(base,env=env,capture_output=True).returncode,0)
  data['delivered'][0]['at']=self.now;(r.ROOT/'feedback.json').write_text(json.dumps(data));self.assertEqual(subprocess.run(base,env=env,capture_output=True).returncode,0)
if __name__=='__main__': unittest.main()
