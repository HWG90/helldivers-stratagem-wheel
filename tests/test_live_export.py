from types import SimpleNamespace

from stratagems.app import App
from stratagems.loadout_log import STATE_LOG_NAME, read_live_loadout


def frame(names):
    return 'EquippedStratagems snapshot 1\ncount=' + str(len(names)) + '\n' + ''.join(n+'\n' for n in names) + 'END\n'


def test_live_file_is_authoritative_and_recovers(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    logs = tmp_path / 'CowboyBingus/Helldivers2/Logs'
    logs.mkdir(parents=True)
    path = logs / STATE_LOG_NAME
    assert read_live_loadout() is None
    (logs/'StratagemSlots.log').write_text('Resupply\n')
    (logs/'EquippedStratagems.log').write_text('Reinforce\n')
    app = App.__new__(App)
    app.config = SimpleNamespace(manual_override=False)
    app._live_log = []
    path.write_text(frame(['Eagle 500kg Bomb']))
    assert [x.name for x in app._immediate_state()[0]] == ['Eagle 500kg Bomb']
    path.write_text('EquippedStratagems snapshot 1\ncount=0\n')
    assert read_live_loadout().entries is None
    assert [x.name for x in app._immediate_state()[0]] == ['Eagle 500kg Bomb']
    path.write_text(frame([]))
    assert app._immediate_state()[0] == []
    path.write_text(frame(['Resupply']))
    assert [x.name for x in app._immediate_state()[0]] == ['Resupply']
    path.write_text(frame(['not a catalog name']))
    assert read_live_loadout().entries is None
    path.write_text(frame(['Resupply']).replace('count=1','count=2'))
    assert read_live_loadout().entries is None


def test_visible_wheel_updates_and_clears_old_selection(monkeypatch):
    app = App.__new__(App)
    app.config = SimpleNamespace(manual_override=False,radial_bind='mouse3')
    events = []
    app.root = SimpleNamespace(after=lambda *args: events.append(args))
    overlay = SimpleNamespace(visible=True,entries=['old'],notice='old',highlight=0)
    overlay.set_state = lambda entries, notice, bind: events.append(('state',entries,notice))
    overlay.apply_offset = lambda x,y: events.append(('offset',x,y))
    app.overlay = overlay
    app._immediate_state = lambda: ([], 'NO STRATAGEMS IN LIVE EXPORT')
    app._watch_live_loadout()
    assert events[0] == ('state',[], 'NO STRATAGEMS IN LIVE EXPORT')
    assert overlay.highlight is None
    assert events[-1][0] == 250
    app.config.manual_override=True;events.clear();app._watch_live_loadout()
    assert len(events)==1
