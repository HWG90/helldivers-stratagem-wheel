from types import SimpleNamespace

import pytest

from stratagems.app import App
from stratagems.config import Config, Region, _from_dict
from stratagems.loadout_log import recognition_block_reason
from stratagems.settings import SettingsWindow


def log_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    path=tmp_path/'CowboyBingus/Helldivers2/Logs'
    path.mkdir(parents=True)
    return path


def test_default_and_saved_preference():
    assert not Config().ocr_fallback
    assert not _from_dict({}).ocr_fallback
    assert _from_dict(Config(ocr_fallback=True).to_dict()).ocr_fallback
    assert not _from_dict({'ocr_fallback':'true'}).ocr_fallback


@pytest.mark.parametrize('filename,body',[
    ('EquippedStratagems.log','Resupply\n'),
    ('StratagemSlots.log','Reinforce\n'),
    ('EquippedStratagems_state.log','EquippedStratagems snapshot 1\ncount=0\nEND\n'),
    ('EquippedStratagems_state.log','EquippedStratagems snapshot 1\n'),
])
def test_logs_block_every_recognition_entry(tmp_path,monkeypatch,filename,body):
    logs=log_dir(tmp_path,monkeypatch);(logs/filename).write_text(body)
    app=App.__new__(App)
    app.config=Config(ocr_fallback=True,region=Region(0,0,10,10))
    app.settings=SimpleNamespace(set_status=lambda text: None)
    app._scan_gen=1
    def forbidden(*args,**kwargs):
        pytest.fail('Recognition or worker must not run with a log')
    monkeypatch.setattr('stratagems.app.threading.Thread',forbidden)
    monkeypatch.setattr('stratagems.app.cluster_glyphs',forbidden)
    app.rescan();app.scan();app.learn()
    app._open_learn(object(),None,False,None)
    app._apply_scan(1,object(),None,object())
    panel=SettingsWindow.__new__(SettingsWindow);panel.config=app.config
    panel._show_preview_message=lambda text:None
    monkeypatch.setattr('stratagems.settings.arrow_preview',forbidden)
    panel._refresh_preview()


def test_fallback_is_opt_in_and_starts_only_without_logs(tmp_path,monkeypatch):
    logs=log_dir(tmp_path,monkeypatch)
    assert recognition_block_reason(False)
    assert recognition_block_reason(True) is None
    app=App.__new__(App);app.config=Config(region=Region(0,0,10,10))
    app.settings=SimpleNamespace(set_status=lambda text:None)
    app._scan_gen=0;app._live_log=[];app._cache=['old'];app._cache_notice='old'
    calls=[]
    monkeypatch.setattr('stratagems.app.threading.Thread',lambda **kw: SimpleNamespace(start=lambda:calls.append('start')))
    app.scan();app.learn();assert calls==[]
    assert app._immediate_state()[0]==[]
    app.config.ocr_fallback=True;app.scan();app.learn();assert calls==['start','start']
    # A newly arriving log suppresses the result of an earlier scan.
    (logs/'EquippedStratagems.log').write_text('Resupply\n')
    app._apply_scan(app._scan_gen,object(),None,object())
    assert app._cache==['old']
