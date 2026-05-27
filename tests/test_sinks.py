from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

from langgraph_oep.sinks.jsonl import LocalJsonlSink
from langgraph_oep.sinks.stdout import StdoutSink


def test_local_jsonl_sink_writes_valid_json_lines(tmp_path) -> None:  # type: ignore[no-untyped-def]
    sink = LocalJsonlSink(tmp_path / "records.jsonl")
    sink.write({"b": 2, "a": 1})
    sink.write({"c": 3})

    lines = sink.path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [{"a": 1, "b": 2}, {"c": 3}]


def test_local_jsonl_sink_directory_path_uses_oep_jsonl(tmp_path) -> None:  # type: ignore[no-untyped-def]
    sink = LocalJsonlSink(tmp_path / "records")
    sink.write({"ok": True})

    assert sink.path == tmp_path / "records" / "oep.jsonl"
    assert json.loads(sink.path.read_text(encoding="utf-8")) == {"ok": True}


def test_local_jsonl_sink_fsync_option(tmp_path) -> None:  # type: ignore[no-untyped-def]
    sink = LocalJsonlSink(tmp_path / "records.jsonl", fsync=True)
    sink.write({"ok": True})

    assert sink.path.exists()


def test_stdout_sink_writes_to_configured_stream() -> None:
    stream = StringIO()
    sink = StdoutSink(stream=stream)
    sink.write({"b": 2, "a": 1})

    assert stream.getvalue() == '{"a": 1, "b": 2}\n'


def test_local_jsonl_sink_serializes_in_process_concurrent_writes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    sink = LocalJsonlSink(tmp_path / "records.jsonl")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda index: sink.write({"index": index}), range(50)))

    lines = sink.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 50
    assert sorted(json.loads(line)["index"] for line in lines) == list(range(50))
