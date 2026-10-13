import os

from config import load_env_file


def test_env_file_parsing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# comment\n\nT_PLAIN=a\nT_QUOTED="b c"\nT_KEEP=from_file\nnot a setting\n')
    monkeypatch.delenv("T_PLAIN", raising=False)
    monkeypatch.delenv("T_QUOTED", raising=False)
    monkeypatch.setenv("T_KEEP", "from_env")
    load_env_file(env)
    assert os.environ["T_PLAIN"] == "a"
    assert os.environ["T_QUOTED"] == "b c"
    assert os.environ["T_KEEP"] == "from_env"
    for key in ("T_PLAIN", "T_QUOTED"):
        monkeypatch.delenv(key)
