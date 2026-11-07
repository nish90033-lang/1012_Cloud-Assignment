import worker


def test_shards_partition_the_pool_without_gaps_or_repeats():
    pool = [{"id": f"C{i:04d}"} for i in range(1, 11)]
    shards = [worker.shard_of(pool, i, 3) for i in range(3)]
    ids = [r["id"] for s in shards for _, r in s]
    assert sorted(ids) == [r["id"] for r in pool]
    assert len(ids) == len(set(ids))
    assert [n for n, _ in shards[1]] == [1, 4, 7]  # line numbers counted from 0, remainder == SHARD_INDEX


def test_prompt_template_keeps_literal_json_braces():
    out = worker.build_prompt('Example {"a": 1}\nCommand: {command}', "hello")
    assert out.endswith("Command: hello") and '{"a": 1}' in out
