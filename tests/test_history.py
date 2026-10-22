import sys,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
import rolo_common as c
import analyze_music_dna as a
import update_rolo_db as u
from rolo_check_age import check_age
NOW=int(time.time())
def play(ago,artist='Legião Urbana',track='Tempo Perdido'):
    return {'listened_at': NOW-ago,'track_metadata':{'artist_name':artist,'track_name':track}}
class HistoryTests(unittest.TestCase):
    def test_identity_and_legitimate_repeats(self):
        items=[play(1),play(1,'LEGIAO URBANA'),play(2)]
        self.assertEqual(len(c.clean_listens(items,NOW)),2)
        dna=a.build_summary({'listens':items},NOW)
        self.assertEqual(len(dna['top_dna_weighted']),1)
        self.assertEqual(dna['top_dna_weighted'][0]['raw_count'],2)
    def test_calendar_windows_and_filter(self):
        dna=a.build_summary({'listens':[play(181*86400,'Old'),play(29*86400,'Recent'),play(31*86400,'Not recent'),play(1,'Music Library Uploads'),play(1,'Release')]},NOW)
        self.assertEqual(dna['current_mood_artists'],['Recent'])
        self.assertEqual(dna['forgotten_gems_artists'],['Old'])
        self.assertEqual(dna['recent_listens_count'],1)
        self.assertEqual(len(dna['top_dna_weighted']),3)
    def test_future_rejected(self):
        with self.assertRaises(ValueError): c.clean_listens([play(-3600)],NOW)
    def test_interrupted_sync_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'db.json'; original={'last_update':'2026-10-07','count':1,'listens':[play(10)]}; c.atomic_json(path,original)
            before=path.read_bytes()
            def failure(params): raise RuntimeError('offline')
            with self.assertRaises(RuntimeError): u.sync(path,failure)
            self.assertEqual(path.read_bytes(),before)
            self.assertFalse(Path(str(path)+'.bak').exists())
    def test_watermark_merge_preserves_old_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'db.json'; old=[play(10),play(999999)]; c.atomic_json(path,{'count':2,'listens':old})
            calls=[]
            def page(params): calls.append(params); return [play(1),play(10),play(11)]
            result=u.sync(path,page)
            self.assertEqual(result['count'],4);self.assertEqual(len(calls),1)
            self.assertTrue(result['sync']['watermark_crossed'])
            self.assertEqual(json.loads(Path(str(path)+'.bak').read_text())['count'],2)
    def test_no_overlap_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'db.json';c.atomic_json(path,{'count':1,'listens':[play(10)]});before=path.read_bytes()
            with self.assertRaises(RuntimeError):u.sync(path,lambda params:[play(1),play(11)])
            self.assertEqual(path.read_bytes(),before)
    def test_atomic_failure_preserves_consumed_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'db.json';c.atomic_json(path,{'original':True});before=path.read_bytes()
            with patch.object(c.os,'replace',side_effect=OSError('simulated crash')):
                with self.assertRaises(OSError): c.atomic_json(path,{'new':True})
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(list(Path(tmp).glob('.db.json.*')),[])
    def test_initial_window_honest(self):
        with patch.object(u,'TARGET_COUNT',3):
            listens,proof=u.fetch_all_listens(fetch_page=lambda params:[play(1),play(2),play(3)])
        self.assertEqual(len(listens),3); self.assertFalse(proof['reached_end'])
    def test_pagination_boundary(self):
        calls=[]
        def page(params):
            calls.append(params)
            return [play(1),play(2)] if len(calls)==1 else [play(10),play(11)]
        listens,proof=u.fetch_all_listens([play(10)],page)
        self.assertEqual(calls[1]['max_ts'],NOW-2); self.assertEqual(proof['pages'],2)
    def test_fresh_requires_intact_current_dna(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbpath=Path(tmp)/'db.json';dna_path=Path(tmp)/'dna.json'
            from datetime import datetime
            from zoneinfo import ZoneInfo
            db={'count':1,'last_update':datetime.now(ZoneInfo('UTC')).isoformat(),'listens':[play(10)]}
            c.atomic_json(dbpath,db);c.atomic_json(dna_path,a.build_summary(db))
            self.assertEqual(check_age(dbpath,dna_path)[1],0)
            dna=json.loads(dna_path.read_text());dna['source_last_update']='outdated';c.atomic_json(dna_path,dna)
            self.assertEqual(check_age(dbpath,dna_path)[1],10)
if __name__=='__main__':unittest.main()
