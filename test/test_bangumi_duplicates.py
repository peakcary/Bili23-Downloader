from copy import deepcopy
from util.parse.episode.bangumi import BangumiEpisodeParser


def test_same_episode_deduplicated_across_sections_without_mutating_response():
    first = {'ep_id': 1, 'bvid': 'BVone', 'cid': 11, 'badge': ''}
    alternate = {'ep_id': 2, 'bvid': 'BVtwo', 'cid': 22, 'badge': ''}
    payload = {'result': {'episodes': [first, dict(first)], 'section': [
        {'title': '合集', 'episodes': [dict(first), alternate]}]}}
    original = deepcopy(payload)
    parser = BangumiEpisodeParser(deepcopy(payload), 'DOCUMENTARY')
    sections = parser.info_data['sections']
    assert [len(x['episodes']) for x in sections] == [1, 1]
    assert parser.episode_number_map == {11: 1}
    assert payload == original


def test_missing_episode_id_uses_video_and_cid():
    item = {'bvid': 'BVone', 'cid': 11, 'badge': ''}
    other = {**item, 'cid': 12}
    parser = BangumiEpisodeParser({'result': {'episodes': [item, dict(item), other]}}, 'DOCUMENTARY')
    assert len(parser.info_data['sections'][0]['episodes']) == 2


def test_running_parse_is_not_started_twice(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from gui.interface.parse import ParseInterface, AsyncTask
    interface = SimpleNamespace(_parse_in_progress=False, parse_btn=Mock(),
                                on_parse_success=Mock(), on_parse_error=Mock(), on_parse_finished=Mock())
    worker = Mock(url='https://www.bilibili.com/bangumi/play/ss33585', pn=1)
    launch = Mock()
    monkeypatch.setattr(AsyncTask, 'run', launch)
    ParseInterface.start_parse(interface, worker)
    ParseInterface.start_parse(interface, worker)
    assert launch.call_count == 1
    ParseInterface.on_parse_finished(interface)
    ParseInterface.start_parse(interface, worker)
    assert launch.call_count == 2
